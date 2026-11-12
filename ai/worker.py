"""The job worker (plan.md §3.4, §10.2; O.3.3, D105): `manage.py run_worker`, its own Compose service.

- `claim()` takes the oldest queued job whose deal and lane are free. `select_for_update(skip_locked=True)` lets two
  workers pass each other; the partial unique constraint (one running job per deal and lane) settles the race when
  both pick jobs of the same deal and lane: the second one's claim fails and it moves on.
- `reap()` ends the jobs silent for 10 minutes. Its UPDATE re-checks the heartbeat in its own WHERE, so a job that beat
  a moment ago is never taken; the job's next beat then finds itself gone and stops.
- `Worker.loop()` claims, runs, and sleeps a second when there is nothing to do. On SIGTERM it stops at the job's next
  beat and puts the job back in the queue, so `docker compose restart worker` loses nothing. The web process never
  runs a job: `docker compose restart backend` leaves running jobs running.
"""

import logging
import os
import socket
import time
from datetime import timedelta

from django.db import DatabaseError, IntegrityError, close_old_connections, transaction
from django.db.models import Exists, OuterRef

from deals import clock

from . import kinds, running
from .models import Job

logger = logging.getLogger(__name__)

SILENT = timedelta(minutes=10)
REAPED_SENTENCE = 'This stopped answering for 10 minutes, so it was ended. Try again.'
IDLE_SECONDS = 1.0
REAP_EVERY_SECONDS = 30.0


def claim(worker='', job_id=None):
    """The claimed job (now running), or None when no queued job's deal and lane are free."""
    now = clock.now()
    busy = Job.objects.filter(status=kinds.RUNNING, deal_id=OuterRef('deal_id'), lane=OuterRef('lane'))
    with transaction.atomic():
        # The oldest is the first started: its id, never its clock stamp (a clock that steps back, as a VM resyncing
        # its time under load does, would put a later job first).
        queued = (
            Job.objects.select_for_update(skip_locked=True)
            .filter(status=kinds.QUEUED)
            .exclude(Exists(busy))
            .order_by('id')
        )
        if job_id is not None:
            queued = queued.filter(pk=job_id)
        job = queued.first()
        if job is None:
            return None
        try:
            with transaction.atomic():
                Job.objects.filter(pk=job.pk).update(
                    status=kinds.RUNNING, started_at=now, heartbeat_at=now, worker=worker[:100], updated_at=now
                )
        except IntegrityError:
            return None  # another worker started a job of this deal and lane first
    job.refresh_from_db()
    return job


def reap(now=None):
    """End every running job silent for 10 minutes. Returns how many."""
    now = now or clock.now()
    return Job.objects.filter(status=kinds.RUNNING, heartbeat_at__lt=now - SILENT).update(
        status=kinds.FAILED,
        resolution=kinds.REAPED,
        error=REAPED_SENTENCE,
        finished_at=now,
        updated_at=now,
    )


class Worker:
    def __init__(self, name=None, idle=IDLE_SECONDS):
        self.name = name or f'{socket.gethostname()}:{os.getpid()}'
        self.idle = idle
        self.stopping = False

    def stop(self, *_args):
        self.stopping = True

    def work_once(self):
        """Claim and run one job; the job, or None when there was nothing to do."""
        job = claim(self.name)
        if job is not None:
            running.run(job, lambda: self.stopping)
        return job

    def _rest(self, seconds):
        until = time.monotonic() + seconds
        while not self.stopping and time.monotonic() < until:
            time.sleep(min(0.2, seconds))

    def loop(self):
        reaped_at = 0.0
        while not self.stopping:
            close_old_connections()
            try:
                if time.monotonic() - reaped_at >= REAP_EVERY_SECONDS:
                    reaped = reap()
                    reaped_at = time.monotonic()
                    if reaped:
                        logger.warning('Reaped %s silent job(s).', reaped)
                job = self.work_once()
            except DatabaseError as exc:  # the database restarting: wait and try again
                logger.warning('The worker could not reach the database (%s).', exc.__class__.__name__)
                job = None
                self._rest(5)
            if job is None:
                self._rest(self.idle)
