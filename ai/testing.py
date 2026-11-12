"""For tests (plan.md §3.5, §12.1, §12.8; Q.6): jobs run inline, never through a worker process, and Claude is the
fake below, so no test reaches a network, even with a key in the container.

`FakeTransport` stands where the SDK stands (`ai.client.install`): it gets the same params a live call would send,
logs them for the request-side checks, and replays a recorded reply keyed by (reader, file hash, range). A key with
no recording fails with "record it"; it never calls out. A recording carries its model, date and schema version, and
can carry a named fault: `truncate` (cut off at max_tokens), `refusal`, `silent` (the stream went quiet: the read
timeout), `account` (the key refused), `bad_json`, or `cancel` (Stop pressed while the stream runs). With a
`manifest` (the corpus's file hashes), recording a file outside it is refused.
"""

import copy
import json
from dataclasses import dataclass, field

from . import client
from .worker import Worker

FAULTS = ('truncate', 'refusal', 'silent', 'account', 'bad_json', 'cancel')
DEFAULT_USAGE = {
    'input_tokens': 1200,
    'output_tokens': 600,
    'cache_creation_input_tokens': 0,
    'cache_read_input_tokens': 0,
}


def run_jobs(limit=20):
    """Claim and run queued jobs in this process until none is free (or `limit`); returns the jobs run."""
    worker, ran = Worker(name='test'), []
    for _ in range(limit):
        job = worker.work_once()
        if job is None:
            break
        ran.append(job)
    return ran


@dataclass
class Recording:
    data: object = None
    model: str = ''  # who answered; '' = the model asked
    usage: dict = field(default_factory=lambda: dict(DEFAULT_USAGE))
    fault: str = ''
    fault_on: str = ''  # the fault happens only when this model is asked ('' = any): a refusal Opus then reads
    during: object = None  # called while the stream runs (the `cancel` fault presses Stop here)
    events: int = 3
    date: str = '2026-11-12'
    schema: int = 1


class FakeTransport:
    def __init__(self, manifest=None):
        self.recordings = {}
        self.log = []  # [{'key', 'params'}] for every request, in order
        self.manifest = set(manifest) if manifest is not None else None

    def record(self, key, data=None, **options):
        """Record the reply for `key` = (reader, file hash, range label); `options` as Recording's fields."""
        if self.manifest is not None and key[1] not in self.manifest:
            raise ValueError('That file is not in the corpus manifest, so its reply is not recorded.')
        fault = options.get('fault', '')
        if fault and fault not in FAULTS:
            raise ValueError(f'Unknown fault: {fault}')
        self.recordings[tuple(key)] = Recording(data=data, **options)
        return self

    def keys(self):
        return [entry['key'] for entry in self.log]

    def send(self, params, *, key=None, on_event=None):
        self.log.append({'key': tuple(key or ()), 'params': copy.deepcopy(params)})
        recording = self.recordings.get(tuple(key or ()))
        if recording is None:
            raise AssertionError(f'No recorded reply for {key}: record it')
        model = recording.model or params['model']
        usage = dict(recording.usage)
        seen = client.Reply(model=model, usage={'input_tokens': usage.get('input_tokens', 0)}, partial=True)
        for number in range(recording.events):
            if number == 1 and recording.during:
                recording.during()
            if on_event:
                try:
                    on_event()
                except Exception as exc:
                    exc.seen = seen
                    raise
        fault = recording.fault if not recording.fault_on or recording.fault_on == params['model'] else ''
        if fault == 'silent':
            raise client.CallFailed('Claude took too long on this part.', seen=seen)
        if fault == 'account':
            raise client.AccountError(seen=seen)
        if fault == 'truncate':
            return client.Reply(model=model, usage=usage, stop_reason='max_tokens', text='{"lines": [')
        if fault == 'refusal':
            return client.Reply(model=model, usage=usage, stop_reason='refusal', text='')
        if fault == 'bad_json':
            return client.Reply(model=model, usage=usage, stop_reason='end_turn', text='{"lines": [}')
        return client.Reply(model=model, usage=usage, stop_reason='end_turn', text=json.dumps(recording.data))
