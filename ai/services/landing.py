"""What becomes of a read's change set (plan.md §10.5; D28, D74, D.6). Slice 18: Discard; slice 19 adds apply and
Undo through the reader's own services.

- `waiting(job)`: a finished read whose change set waits for a person (its `land` is staged, nothing has resolved it).
- `discard(user, job_id)` drops the change set: the job keeps its summary and counts, its `result` loses the items
  (D74), and nothing on the deal changes, so no Activity is recorded. Discarding again changes nothing; a change set
  that was applied cannot be discarded (409).
"""

from django.db import transaction

from deals.activity import Refused

from .. import kinds
from ..models import Job

STAGED = 'staged'
DISCARDED, APPLIED = 'discarded', 'applied'
NOT_WAITING = 'This read is not waiting for review, so there is nothing to discard.'
ALREADY_APPLIED = 'This read was already used, so it cannot be discarded. Undo it instead.'
KEPT = ('v', 'target', 'documents', 'summary', 'counts', 'model', 'cost_usd', 'estimate_usd')


def waiting(job):
    return (
        job.kind in (kinds.READ, kinds.RECHECK)
        and job.status in (kinds.DONE, kinds.CANCELLED)
        and job.land == STAGED
        and not job.resolution.startswith((DISCARDED, APPLIED))
        and bool((job.result or {}).get('items'))
    )


def discard(user, job_id):
    """(job, changed)."""
    with transaction.atomic():
        job = Job.objects.select_for_update().get(pk=job_id)
        if job.resolution == DISCARDED:
            return job, False
        if job.resolution == APPLIED:
            raise Refused(ALREADY_APPLIED)
        if not waiting(job):
            raise Refused(NOT_WAITING)
        result = job.result or {}
        job.result = {**{key: result[key] for key in KEPT if key in result}, 'discarded': True}
        job.resolution = DISCARDED
        job.save(update_fields=['result', 'resolution', 'updated_at'])
    return job, True
