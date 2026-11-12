"""One call's life, and a run's calls at once (plan.md §10.3, §10.4; D51, D53, D105).

A call is reserved in the ledger at its worst case (`budget.reserve`, which refuses one that could pass the total
cap), sent and checked (`client`), then settled at what it used (`budget.settle`) — whatever happens, Stop included,
so the ledger never misses a call. The database is touched only by the thread that runs the job: up to
`AI_READ_PARALLEL` calls stream at once in threads that only talk to Claude, and the job's thread beats between them.
When the beat raises (Stop pressed, the worker stopping, the job reaped), the streams in flight are aborted at their
next event, recorded as stopped, and the beat's exception goes on.
"""

import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass

from . import budget, client
from .models import Call

WAIT_SECONDS = 1.0


class Aborted(client.ClaudeError):
    sentence = 'Stopped.'
    reason = 'stopped'


@dataclass
class Planned:
    params: dict
    key: tuple  # (target, file hash, range label): what the fake client replays
    input_tokens: int  # estimated, for the worst case
    tag: object = None  # the caller's: which file and range


@dataclass
class Done:
    planned: Planned
    data: object = None
    reply: client.Reply = None
    error: client.ClaudeError = None
    cost: object = 0


def send(planned, on_event=None):
    """Network only: the reply's data, or the error with what the call used. Never touches the database."""
    try:
        reply = client.transport().send(planned.params, key=planned.key, on_event=on_event)
        return Done(planned, data=client.check(reply), reply=reply)
    except client.ClaudeError as exc:
        return Done(planned, reply=exc.seen, error=exc)


def reserve(planned, *, job=None, deal_id=None, purpose='read'):
    return budget.reserve(
        model=planned.params['model'],
        input_tokens=planned.input_tokens,
        max_tokens=planned.params['max_tokens'],
        purpose=purpose,
        job=job,
        deal_id=deal_id,
    )


def settle(row, done, stopped=False):
    reply = done.reply
    status = Call.STOPPED if stopped or isinstance(done.error, Aborted) else Call.FAILED if done.error else Call.DONE
    done.cost = budget.settle(
        row,
        answered=reply.model if reply else '',
        usage=reply.usage if reply else {},
        status=status,
        stop_reason=reply.stop_reason if reply else '',
    )
    return done


def extract(planned, *, job=None, deal_id=None, purpose='read', on_event=None):
    """One call, start to end, in this thread (the Eval lane, a single read). Returns Done."""
    row = reserve(planned, job=job, deal_id=deal_id, purpose=purpose)
    try:
        done = send(planned, on_event)
    except BaseException as exc:  # Stop, the worker stopping: recorded, then let go
        settle(row, Done(planned, reply=getattr(exc, 'seen', None)), stopped=True)
        raise
    return settle(row, done)


class Runner:
    """Up to `parallel` calls in flight. `submit(planned, row)`, then `wait(beat)` yields (Done, row) as they end."""

    def __init__(self, parallel):
        self.parallel = max(1, int(parallel))
        self._queued = []  # parallel == 1: sent in this thread, at `wait`
        self._futures = {}
        self._abort = threading.Event()
        self._pool = ThreadPoolExecutor(self.parallel, thread_name_prefix='claude') if self.parallel > 1 else None

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self._drop()
        if self._pool is not None:
            self._pool.shutdown(wait=True)

    def _drop(self):
        """End every call still queued or in flight, each recorded as stopped (a call never sent costs nothing)."""
        self._abort.set()
        for planned, row in self._queued:
            settle(row, Done(planned), stopped=True)
        self._queued.clear()
        for future, (_planned, row) in list(self._futures.items()):
            settle(row, future.result(), stopped=True)
        self._futures.clear()

    @property
    def busy(self):
        return bool(self._queued or self._futures)

    @property
    def has_room(self):
        return len(self._queued) + len(self._futures) < self.parallel

    def _check_abort(self):
        if self._abort.is_set():
            raise Aborted

    def submit(self, planned, row):
        if self._pool is None:
            self._queued.append((planned, row))
        else:
            self._futures[self._pool.submit(send, planned, self._check_abort)] = (planned, row)

    def wait(self, beat):
        """The calls that ended; `beat()` runs between waits (and on every stream event when not parallel)."""
        try:
            beat()
        except BaseException:
            self._drop()
            raise
        if self._pool is None:
            planned, row = self._queued.pop(0)
            try:
                done = send(planned, beat)
            except BaseException as exc:
                settle(row, Done(planned, reply=getattr(exc, 'seen', None)), stopped=True)
                raise
            return [(settle(row, done), row)]
        finished, _ = wait(list(self._futures), timeout=WAIT_SECONDS, return_when=FIRST_COMPLETED)
        ended = []
        for future in finished:
            _planned, row = self._futures.pop(future)
            ended.append((settle(row, future.result()), row))
        return ended
