"""The ai payloads (plan.md §7.5; D.6, O.4). Reads only: the state GET writes nothing, not even a DealAi row.

`deal_state` is what `useAiState` polls: the deal's queued and running jobs, the ones that finished in the last
fifteen minutes (so a browser that saw a job run learns how it ended and refetches the areas it landed in), and the
deal's AI settings with their defaults. A fixed number of queries, however many jobs (Q.3 #4).
"""

from datetime import timedelta

from django.conf import settings
from django.db.models import Q, Sum

from accounts.access import can_direct
from deals import clock
from deals.selectors import person

from . import kinds
from .models import DealAi, Job

RECENT = timedelta(minutes=15)
RECENT_KEPT = 10


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
        'resolution': job.resolution,
        'activity_id': job.activity_id,
        'created_by': person(job.created_by),
        'created_at': job.created_at,
        'started_at': job.started_at,
        'finished_at': job.finished_at,
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
    places = _queue_positions(jobs)
    finished = sorted((job for job in jobs if job.status in kinds.FINISHED), key=lambda job: job.finished_at)
    row = DealAi.objects.filter(deal=deal).select_related('locked_by').first()
    spent = Job.objects.filter(deal=deal).aggregate(total=Sum('cost_usd'))['total'] or 0
    return {
        'deal': deal.id,
        'claude': bool(settings.ANTHROPIC_API_KEY),  # Claude's doors show only with a key (D26); the check needs none
        'jobs': [job_light(job, places.get(job.id)) for job in jobs if job.status in kinds.ACTIVE],
        'recent': [job_light(job) for job in reversed(finished[-RECENT_KEPT:])],
        'waiting': [],  # change sets waiting for review (slice 18)
        'news': [],  # what a finished job left to look at (slice 20)
        'lock': {'by': person(row.locked_by), 'at': row.locked_at} if row and row.locked_at else None,
        'spend': {'usd': f'{spent:.2f}', 'budget_usd': f'{row.budget_usd:.2f}' if row and row.budget_usd else None},
        'can': {'direct': can_direct(user), 'budget': bool(getattr(user, 'is_staff', False))},
    }
