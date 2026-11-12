"""What becomes of a read's change set (plan.md §10.5; D28, D72–D75, D.6). The owner's reader writes; ai keeps the job.

- `waiting(job)`: a finished read whose change set waits for a person (its `land` is staged, nothing has resolved it).
- `discard(user, job_id)` drops the change set: the job keeps its summary and counts, its `result` loses the items
  (D74), and nothing on the deal changes, so no Activity is recorded. Discarding again changes nothing; a change set
  that was applied cannot be discarded (409).
- `apply(user, job_id, select, picks)` is "Use this scan ▸" / "Apply N selected ▸" (D72): the reader's `apply` lands
  the chosen parts through its owner's services and returns what it wrote (`landed`), which the job keeps beside its
  change set; the job is `applied` and points at the landing's main Activity row. A read that finds nothing new is
  applied too, writing nothing on the deal (D60). Applying twice is refused (409).
- `undo(user, job_id, force)` is ↶ Undo this run (D73): the reader's `undo` reverts the landing; when something
  changed since, the 409 says what and that "Undo anyway" (`force`) can leave those and put back the rest.
Each locks the Deal first, then the job (O.3.7), then the reader locks its owner's rows.
"""

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException

from deals import clock
from deals.activity import Refused
from deals.models import Deal

from .. import kinds, registry
from ..models import Job

STAGED = 'staged'
DISCARDED, APPLIED, UNDONE = 'discarded', 'applied', 'undone'
NOT_WAITING = 'This read is not waiting for review, so there is nothing to discard.'
ALREADY_APPLIED = 'This read was already used, so it cannot be discarded. Undo it instead.'
NOT_TO_USE = 'This read is not waiting for review, so there is nothing to use.'
USED = 'This read was already used.'
NOT_USED = 'This read was not used, so there is nothing to undo.'
NOTHING_WRITTEN = 'Using this read changed nothing on the deal, so there is nothing to undo.'
NO_LANDING = 'Reads of this kind cannot be used here yet.'
KEPT = ('v', 'target', 'documents', 'summary', 'counts', 'model', 'cost_usd', 'estimate_usd')


class UndoRefused(APIException):
    """Undo refused because something changed since (409): the sentence, the keys, and that Undo anyway can work."""

    status_code = status.HTTP_409_CONFLICT
    default_code = 'refused'

    def __init__(self, sentence, keys=()):
        self.sentence, self.keys = sentence, list(keys)
        super().__init__({'detail': sentence, 'keys': self.keys, 'can_force': 'true'})


def waiting(job):
    return (
        job.kind in (kinds.READ, kinds.RECHECK)
        and job.status in (kinds.DONE, kinds.CANCELLED)
        and job.land == STAGED
        and not job.resolution.startswith((DISCARDED, APPLIED, UNDONE))
        and bool((job.result or {}).get('items'))
    )


def _locked(job_id):
    """The job, locked after its Deal (the lock order)."""
    deal_id = Job.objects.values_list('deal_id', flat=True).get(pk=job_id)
    Deal.objects.select_for_update().only('id').get(pk=deal_id)
    return Job.objects.select_for_update().select_related('deal').get(pk=job_id)


def discard(user, job_id):
    """(job, changed)."""
    with transaction.atomic():
        job = _locked(job_id)
        if job.resolution == DISCARDED:
            return job, False
        if job.resolution in (APPLIED, UNDONE):
            raise Refused(ALREADY_APPLIED)
        if not waiting(job):
            raise Refused(NOT_WAITING)
        result = job.result or {}
        job.result = {**{key: result[key] for key in KEPT if key in result}, 'discarded': True}
        job.resolution = DISCARDED
        job.save(update_fields=['result', 'resolution', 'updated_at'])
    return job, True


def apply(user, job_id, select=None, picks=None):
    """(job, landed): the read used; `landed` is what it wrote ({activity_ids, plan_ids, areas, summary, …})."""
    with transaction.atomic():
        job = _locked(job_id)
        if job.resolution in (APPLIED, UNDONE):
            raise Refused(USED)
        if not waiting(job):
            raise Refused(NOT_TO_USE)
        reader = registry.readers.get(job.target)
        if reader is None or reader.apply is None:
            raise Refused(NO_LANDING)
        landed = reader.apply(user, job.deal, job, select=select, picks=picks)
        landed = {**landed, 'by': getattr(user, 'id', None), 'at': clock.now().isoformat()}
        job.result = {**(job.result or {}), 'landed': landed}
        job.resolution = APPLIED
        job.activity_id = landed.get('activity_id')
        job.save(update_fields=['result', 'resolution', 'activity', 'updated_at'])
    return job, landed


def undo(user, job_id, force=False):
    """(job, changed): the landing reverted; an Undo already done changes nothing."""
    with transaction.atomic():
        job = _locked(job_id)
        if job.resolution == UNDONE:
            return job, False
        if job.resolution != APPLIED:
            raise Refused(NOT_USED)
        landed = (job.result or {}).get('landed') or {}
        if not landed.get('activity_ids'):
            raise Refused(NOTHING_WRITTEN)
        reader = registry.readers.get(job.target)
        if reader is None or reader.undo is None:
            raise Refused(NO_LANDING)
        try:
            undone = reader.undo(user, job.deal, job, force=force)
        except Refused as exc:
            if force:
                raise
            raise UndoRefused(exc.sentence, exc.keys) from exc
        job.result = {**(job.result or {}), 'landed': {**landed, 'undone': undone}}
        job.resolution = UNDONE
        job.save(update_fields=['result', 'resolution', 'updated_at'])
    return job, True
