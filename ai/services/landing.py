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
- `on_finish(job, change_set)` is the `read` kind's land hook (D71, slice 20): in the transaction that ends the job it
  asks `ai/land.py` whether the read lands by itself and, if so, lands it as proposed through the reader, exactly as
  "Use this scan ▸" would, with the same ↶ Undo this run. A landing the owner refuses (the deal changed meanwhile) is
  taken back and the read waits for review with the refusal's sentence.
- `on_recheck(job, change_set)` is the `recheck` kind's (slice 22): a re-check always waits for a person (D-119);
  `apply` and `undo` then go through the owner's checker (`registry.checkers`) as a read's go through its reader.
Each locks the Deal first, then the job (O.3.7), then the reader locks its owner's rows.
"""

import logging

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException

from deals import clock, rules
from deals.activity import Refused
from deals.models import Deal

from .. import kinds, land, registry
from ..models import DealAi, Job

logger = logging.getLogger(__name__)

DISCARDED, APPLIED, UNDONE = 'discarded', 'applied', 'undone'
NOT_WAITING = 'This read is not waiting for review, so there is nothing to discard.'
ALREADY_APPLIED = 'This read was already used, so it cannot be discarded. Undo it instead.'
NOT_TO_USE = 'This read is not waiting for review, so there is nothing to use.'
USED = 'This read was already used.'
NOT_USED = 'This read was not used, so there is nothing to undo.'
NOTHING_WRITTEN = 'Using this read changed nothing on the deal, so there is nothing to undo.'
NO_LANDING = 'Reads of this kind cannot be used here yet.'
RECHECK_WAITS = 'A re-check waits for you: nothing changes until you apply it.'
COULD_NOT = 'Claude’s read could not be put on the deal by itself, so it waits for review.'
KEPT = ('v', 'target', 'documents', 'summary', 'counts', 'model', 'cost_usd', 'estimate_usd', 'reply_id', 'board')


class UndoRefused(APIException):
    """Undo refused because something changed since (409): the sentence, the keys, and that Undo anyway can work."""

    status_code = status.HTTP_409_CONFLICT
    default_code = 'refused'

    def __init__(self, sentence, keys=()):
        self.sentence, self.keys = sentence, list(keys)
        super().__init__({'detail': sentence, 'keys': self.keys, 'can_force': 'true'})


def waiting(job):
    return (
        job.kind in (kinds.READ, kinds.RECHECK, kinds.TURN)
        and job.status in (kinds.DONE, kinds.CANCELLED)
        and job.land == land.STAGED
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
        if job.kind == kinds.TURN:  # a chat turn's changes land through their owners (slice 24)
            from .turns import land_turn

            landed = land_turn(user, job, select)
        else:
            owner = _owner(job)
            if owner is None or owner.apply is None:
                raise Refused(NO_LANDING)
            landed = owner.apply(user, job.deal, job, select=select, picks=picks)
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
        if job.kind == kinds.TURN:
            from .turns import undo_turn

            job.result = {**(job.result or {}), 'landed': {**landed, 'undone': undo_turn(user, job, landed)}}
            job.resolution = UNDONE
            job.save(update_fields=['result', 'resolution', 'updated_at'])
            return job, True
        owner = _owner(job)
        if owner is None or owner.undo is None:
            raise Refused(NO_LANDING)
        try:
            undone = owner.undo(user, job.deal, job, force=force)
        except Refused as exc:
            if force:
                raise
            raise UndoRefused(exc.sentence, exc.keys) from exc
        job.result = {**(job.result or {}), 'landed': {**landed, 'undone': undone}}
        job.resolution = UNDONE
        job.save(update_fields=['result', 'resolution', 'updated_at'])
    return job, True


def _owner(job):
    """Who lands the job's change set: a re-check's checker, else a read's reader."""
    if job.kind == kinds.RECHECK:
        return registry.checkers.get(job.target)
    return registry.readers.get(job.target)


def on_recheck(job, change_set):
    """A finished re-check's fields: waiting for a person whenever it proposes something (D-119)."""
    if not (change_set or {}).get('items'):
        return {}
    return {'land': land.STAGED, 'wait_reason': RECHECK_WAITS}


def is_direct(user):
    from accounts.access import can_direct

    return bool(getattr(user, 'is_staff', False)) or can_direct(user)


def _sentence(exc):
    detail = getattr(exc, 'detail', None)
    if isinstance(detail, dict):
        detail = next(iter(detail.values()), '')
    if isinstance(detail, list):
        detail = detail[0] if detail else ''
    return str(getattr(exc, 'sentence', '') or detail or COULD_NOT)[:200]


def on_finish(job, change_set):
    """The job fields a finished read ends with: landed by itself ({land: auto, resolution: applied, result with
    `landed`, activity}), or waiting with why ({land: staged, wait_reason}). Runs inside `running._finish`'s
    transaction, after its Deal and job are locked here."""
    reader = registry.readers.get(job.target)
    if reader is None or not (change_set or {}).get('items'):
        return {}
    locked = _locked(job.id)
    user = locked.created_by
    decision = land.decide(
        change_set,
        target=job.target,
        must_review=reader.must_review or reader.apply is None,
        direct=is_direct(user),
        asked_review=bool((job.params or {}).get('review')),
        locked=DealAi.objects.filter(deal_id=job.deal_id, locked_at__isnull=False).exists(),
        lost=rules.refuses(locked.deal, 'ai_land') or '',
    )
    if decision.mode != land.AUTO:
        return {'land': land.STAGED, 'wait_reason': decision.sentence[:200]}
    locked.result = change_set
    try:
        with transaction.atomic():  # a savepoint: a refused landing goes back alone, the job still ends
            landed = reader.apply(user, locked.deal, locked, select=None, picks=None)
    except (Refused, APIException) as exc:
        return {'land': land.STAGED, 'wait_reason': _sentence(exc)}
    except Exception as exc:  # noqa: BLE001 - the read stays, waiting; the class only, never its text (rule 10)
        logger.warning('Job %s could not land by itself: %s', job.id, exc.__class__.__name__)
        return {'land': land.STAGED, 'wait_reason': COULD_NOT}
    landed = {**landed, 'by': user.id, 'at': clock.now().isoformat(), 'auto': True}
    return {
        'land': land.AUTO,
        'wait_reason': '',
        'resolution': APPLIED,
        'result': {**change_set, 'landed': landed},
        'activity_id': landed.get('activity_id'),
    }
