"""Running one claimed job to its end (plan.md §10.2; O.3.3, D105).

`run(job)` calls the kind's runner (registry.job_kinds) with a `Progress`, then writes how it ended, but only while the
job is still running: a job the reaper took is left as the reaper wrote it. A kind's `land` hook runs in that same
transaction (a read that lands by itself, D71): if the job is no longer running, its landing is taken back too. A
failure is logged by the job's id and the exception's class, never its text (a message can carry a file's words, rule
10); the person reads a fixed sentence. `run_inline(job)` claims one job and runs it at once: tests and AI_JOBS_INLINE
(plan §3.5).
"""

import logging

from django.db import transaction

from deals import clock

from . import kinds, registry
from .models import Job
from .progress import Gone, JobFailed, Paused, Progress, Stopped

logger = logging.getLogger(__name__)

FAILED_SENTENCE = 'Something went wrong, so this stopped. Try again; if it fails again, tell an admin.'
STOPPED_STEP = 'Stopped — what was finished is kept.'
PAUSED_STEP = 'Paused while the worker restarted; it starts again in a moment.'


def _finish(job, progress, status, *, result=None, error='', resolution='', land=None):
    now = clock.now()
    steps = progress.steps
    if status == kinds.CANCELLED:
        steps = [*steps, STOPPED_STEP][-kinds.STEPS_KEPT :]
    fields = {
        'status': status,
        'result': result or {},
        'error': error,
        'resolution': resolution,
        'steps': steps,
        'progress': 100 if status == kinds.DONE else progress.progress,
        'activity_id': progress.activity_id,
        'finished_at': now,
        'heartbeat_at': now,
        'updated_at': now,
    }
    with transaction.atomic():
        if land is not None:
            fields.update(land(job, fields['result']) or {})
        written = Job.objects.filter(pk=job.pk, status=kinds.RUNNING).update(**fields)
        if not written:
            transaction.set_rollback(True)  # reaped meanwhile: a landing in this transaction goes back too
    return bool(written)


def _requeue(job, progress):
    """Back to the queue (the worker is stopping); a job whose Stop was pressed ends instead."""
    now = clock.now()
    running = Job.objects.filter(pk=job.pk, status=kinds.RUNNING)
    if running.filter(cancel_requested_at__isnull=False).exists():
        return _finish(job, progress, kinds.CANCELLED, result=progress.result, resolution=kinds.STOPPED)
    steps = [*progress.steps, PAUSED_STEP][-kinds.STEPS_KEPT :]
    return bool(
        running.update(status=kinds.QUEUED, started_at=None, heartbeat_at=None, worker='', steps=steps, updated_at=now)
    )


def run(job, stopping=None):
    """Run a job the caller has claimed (status running). Returns the job's final status, or None when it is no
    longer running here."""
    entry = registry.job_kinds.get(job.kind)
    progress = Progress(job, stopping)
    try:
        if entry is None:
            raise LookupError(f'No runner for {job.kind} jobs')
        result = entry.run(job, progress)
    except Stopped:
        _finish(job, progress, kinds.CANCELLED, result=progress.result, resolution=kinds.STOPPED)
        return kinds.CANCELLED
    except Paused:
        _requeue(job, progress)
        return kinds.QUEUED
    except Gone:
        return None
    except JobFailed as exc:  # the runner's own sentence: it names no file and quotes none
        _finish(job, progress, kinds.FAILED, result=progress.result, error=exc.sentence[:300])
        return kinds.FAILED
    except Exception as exc:  # noqa: BLE001 - any failure ends the job with a sentence, never its text
        logger.warning('Job %s (%s) failed: %s', job.id, job.kind, exc.__class__.__name__)
        _finish(job, progress, kinds.FAILED, result=progress.result, error=FAILED_SENTENCE)
        return kinds.FAILED
    _finish(job, progress, kinds.DONE, result=result, land=entry.land)
    return kinds.DONE


def run_inline(job):
    """Claim this queued job and run it now. A job whose deal and lane are busy stays queued for the worker."""
    from .worker import claim

    claimed = claim('inline', job_id=job.id)
    return run(claimed) if claimed else None
