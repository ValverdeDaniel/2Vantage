"""The ai payloads (plan.md §7.5; D.6, O.4). Reads only: the state GET writes nothing, not even a DealAi row.

`deal_state` is what `useAiState` polls: the deal's queued and running jobs, the ones that finished in the last
fifteen minutes (so a browser that saw a job run learns how it ended and refetches the areas it landed in), and the
deal's AI settings with their defaults. A fixed number of queries, however many jobs (Q.3 #4).
"""

from datetime import timedelta

from django.db.models import Q, Sum

from accounts.access import can_direct
from deals import clock
from deals.selectors import person

from . import budget, client, kinds, pricing, ranges, read_files, registry
from .models import DealAi, Job
from .services.landing import waiting as is_waiting

RECENT = timedelta(minutes=15)
RECENT_KEPT = 10
WAITING_KEPT = 10


def _last_step(job):
    return job.steps[-1] if job.steps else ''


def job_light(job, queue_position=None):
    result = job.result or {}
    return {
        'id': job.id,
        'kind': job.kind,
        'lane': job.lane,
        'target': job.target,
        'status': job.status,
        'progress': job.progress,
        'step': _last_step(job),
        'documents': job.documents,
        'stopping': bool(job.cancel_requested_at) and job.status in kinds.ACTIVE,
        'queue_position': queue_position,
        'counts': result.get('counts'),
        'landed': result.get('landed') or {'areas': [], 'plan_ids': []},
        'error': job.error,
        'land': job.land,  # a read: staged (waits for review) or budget (waits past a cap) (slice 18)
        'wait_reason': job.wait_reason,
        'resolution': job.resolution,
        'activity_id': job.activity_id,
        'created_by': person(job.created_by),
        'created_at': job.created_at,
        'started_at': job.started_at,
        'finished_at': job.finished_at,
    }


def waiting_payload(job):
    """A change set waiting for review, light: what the strip and the card's door need, never its items."""
    result = job.result or {}
    return {
        'job_id': job.id,
        'target': job.target,
        'documents': job.documents,
        'summary': result.get('summary', ''),
        'counts': result.get('counts') or {},
        'partial': bool(result.get('partial')),
        'created_by': person(job.created_by),
        'finished_at': job.finished_at,
    }


def landed_payload(job):
    """A read used in the last minutes, for its "✓ Used …  ↶ Undo this run" strip (D23, D73): never its items."""
    landed = (job.result or {}).get('landed') or {}
    return {
        'type': 'landed',
        'job_id': job.id,
        'target': job.target,
        'documents': job.documents,
        'summary': landed.get('summary', ''),
        'skipped': landed.get('skipped') or [],
        'activity_id': job.activity_id,
        'at': landed.get('at'),
    }


def job_payload(job):
    """One job, whole: its steps and its result (a change set from slice 18; a locate's counts and files)."""
    return {**job_light(job), 'steps': job.steps, 'params': job.params, 'result': job.result}


def _queue_positions(jobs):
    """{job id: place in its lane's queue on the deal, 1 = next}."""
    places, seen = {}, {}
    for job in jobs:
        if job.status == kinds.QUEUED:
            seen[job.lane] = seen.get(job.lane, 0) + 1
            places[job.id] = seen[job.lane]
    return places


def deal_state(deal, user):
    since = clock.now() - RECENT
    jobs = list(
        Job.objects.filter(deal=deal)
        .filter(Q(status__in=kinds.ACTIVE) | Q(finished_at__gte=since))
        .select_related('created_by')
        .order_by('created_at', 'id')
    )
    staged = (
        Job.objects.filter(deal=deal, kind__in=(kinds.READ, kinds.RECHECK), land='staged', result__has_key='items')
        .filter(status__in=(kinds.DONE, kinds.CANCELLED))
        .exclude(resolution__in=('discarded', 'applied', 'undone'))
        .select_related('created_by')
        .order_by('-finished_at', '-id')[:WAITING_KEPT]
    )
    landed = (
        Job.objects.filter(deal=deal, kind=kinds.READ, resolution='applied', updated_at__gte=since)
        .exclude(activity__isnull=True)
        .order_by('-updated_at', '-id')[:WAITING_KEPT]
    )
    places = _queue_positions(jobs)
    finished = sorted((job for job in jobs if job.status in kinds.FINISHED), key=lambda job: job.finished_at)
    row = DealAi.objects.filter(deal=deal).select_related('locked_by').first()
    spent = Job.objects.filter(deal=deal).aggregate(total=Sum('cost_usd'))['total'] or 0
    return {
        'deal': deal.id,
        'claude': client.available(),  # Claude's doors show only with a key (D26); the check needs none
        'jobs': [job_light(job, places.get(job.id)) for job in jobs if job.status in kinds.ACTIVE],
        'recent': [job_light(job) for job in reversed(finished[-RECENT_KEPT:])],
        'waiting': [waiting_payload(job) for job in staged if is_waiting(job)],  # change sets to review (D28)
        'news': [landed_payload(job) for job in landed],  # reads used lately, with Undo (slice 19; more in 20)
        'lock': {'by': person(row.locked_by), 'at': row.locked_at} if row and row.locked_at else None,
        'spend': {'usd': f'{spent:.2f}', 'budget_usd': f'{row.budget_usd:.2f}' if row and row.budget_usd else None},
        'can': {'direct': can_direct(user), 'budget': bool(getattr(user, 'is_staff', False))},
    }


def meta():
    """`/api/meta/`'s `ai` section, served only when Claude is set up (D.6): the readers and the file kinds each reads,
    the reading models (Opus 5.5 for admins and direct people, D91) in "Try again" order, and the caps."""
    return {
        'targets': [{'key': key, 'kinds': list(reader.kinds)} for key, reader in registry.readers.items()],
        'models': [
            {'key': key, 'label': pricing.LABELS[key], 'admins_only': key == pricing.OPUS}
            for key in pricing.READ_MODELS
        ],
        'ladder': list(pricing.READ_MODELS),
        'read_limit_usd': f'{budget.run_cap():.2f}',
        'failed_words': read_files.FAILED_WORDS,  # why a part of a read failed
        'left_out_words': ranges.LEFT_OUT_WORDS,  # why a page was left out
    }
