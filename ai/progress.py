"""What a running job tells the world, and how it learns to stop (plan.md §10.2; D105, O.3.3).

A job's runner gets a `Progress`. Each call is a beat: it moves `heartbeat_at` (so the reaper leaves the job alone),
writes the progress and the step lines the browser polls, and checks whether Stop was pressed. Beats come from the
work itself (a page read, a file done, a stream event), never from a timer, so a job that hangs falls silent and the
reaper ends it. Writes are at most one a second unless a step is new.

A beat raises, and the runner lets it go: `Stopped` (Stop was pressed: the job ends, keeping its finished parts),
`Paused` (the worker is shutting down: the job goes back to the queue) or `Gone` (the job no longer runs: the reaper
ended it). `result` is what the runner has finished so far, kept when it stops.
"""

import time

from deals import clock

from . import kinds
from .models import Job

BEAT_SECONDS = 1.0


class Stopped(Exception):
    """Stop was pressed."""


class Paused(Exception):
    """The worker is shutting down; the job runs again from the queue."""


class Gone(Exception):
    """The job no longer runs here (the reaper ended it)."""


class JobFailed(Exception):  # noqa: N818
    """The run cannot go on and kept nothing: the job fails with this sentence, which names no file and quotes none."""

    def __init__(self, sentence):
        super().__init__(sentence)
        self.sentence = sentence


def _line(text):
    return ' '.join(str(text).split())[: kinds.STEP_LENGTH]


class Progress:
    def __init__(self, job, stopping=None):
        self.job_id = job.id
        self.steps = list(job.steps or [])
        self.progress = job.progress or 0
        self.result = {}
        self.activity_id = None
        self._stopping = stopping or (lambda: False)
        self._live = False  # the last step is a live line that the next `say` replaces
        self._last_beat = None

    def step(self, text, progress=None):
        """A new line for the progress card: short, never file text or names."""
        self.steps = [*self.steps, _line(text)][-kinds.STEPS_KEPT :]
        self._live = False
        self._set(progress)
        self.beat(force=True)

    def say(self, text, progress=None):
        """A live line ("Reading page 120 of 1,500"), replaced by the next one, written with the next beat."""
        line = _line(text)
        self.steps = [*self.steps[:-1], line] if self._live and self.steps else [*self.steps, line]
        self.steps = self.steps[-kinds.STEPS_KEPT :]
        self._live = True
        self._set(progress)
        self.beat()

    def advance(self, progress):
        self._set(progress)
        self.beat()

    def _set(self, progress):
        if progress is not None:
            self.progress = max(0, min(100, int(progress)))

    def beat(self, force=False):
        """Alive: move the heartbeat, write the progress, and stop if asked to."""
        if self._stopping():
            raise Paused
        now = time.monotonic()
        if not force and self._last_beat is not None and now - self._last_beat < BEAT_SECONDS:
            return
        self._last_beat = now
        stamp = clock.now()
        running = Job.objects.filter(pk=self.job_id, status=kinds.RUNNING)
        if not running.update(heartbeat_at=stamp, updated_at=stamp, progress=self.progress, steps=self.steps):
            raise Gone
        if Job.objects.filter(pk=self.job_id, cancel_requested_at__isnull=False).exists():
            raise Stopped
