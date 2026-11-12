"""Editing a deal and moving its stage: by hand, automatically (`advance`), lost and reopened (plan.md §5.1, §7.3)."""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .. import activity, clock, stages
from ..models import Deal
from ..values import locked
from .snapshots import diff, snapshot

DEAL_FIELDS = ('stage', 'effective_date', 'owner_id')  # the lines to quote have their own door: lines.set_lines
LOST_FIELDS = ('stage', 'lost_reason', 'lost_at', 'lost_from_stage')


def _deal_change(deal, changed, key):
    return activity.change(f'deal:{deal.id}', {key: changed[key]} if key in changed else {})


@transaction.atomic
def update_deal(user, deal_id, **changes):
    deal = locked(Deal, deal_id)
    before = snapshot(deal, DEAL_FIELDS)
    notes = []
    if 'stage' in changes:
        stage = changes['stage']
        if stage in ('sold', 'lost'):
            raise ValidationError({'stage': ['Mark a plan sold or use Mark lost.']})
        if stage not in stages.MANUAL:
            raise ValidationError({'stage': ['Unknown stage.']})
        if deal.stage == 'lost':
            raise ValidationError({'stage': ['Reopen the deal first.']})
        if stage != deal.stage:
            deal.stage = stage
            notes.append(('stage', f'Moved to {stages.label(stage)}'))
    if 'effective_date' in changes and changes['effective_date'] != deal.effective_date:
        deal.effective_date = changes['effective_date']
        notes.append(('effective_date', 'Changed the effective date'))
    if 'owner' in changes and changes['owner'] != deal.owner:
        deal.owner = changes['owner']
        notes.append(('owner', 'Changed the owner'))
    if notes:
        deal.save()
        changed = diff(before, snapshot(deal, DEAL_FIELDS))
        for key, note in notes:
            activity.record(deal, user, 'deal', 'updated', note, changes=[_deal_change(deal, changed, key)])
    return deal


def set_effective_date(deal_id, value):
    """Write the deal's one effective date for intake's `target_effective_date` answer, its door (B1, N.1); returns
    {'effective_date': [before, after]} (ISO text), or {} when unchanged. Like `set_lines`, it records no Activity:
    intake records one row holding this change beside the answers, and intake's reverter puts it back. Runs inside
    the caller's transaction and locks the Deal row (the caller has usually locked it already)."""
    deal = locked(Deal, deal_id)
    if value == deal.effective_date:
        return {}
    before = snapshot(deal, ('effective_date',))
    deal.effective_date = value
    deal.save(update_fields=['effective_date', 'updated_at'])
    return diff(before, snapshot(deal, ('effective_date',)))


def advance(deal, user, stage, reason):
    """An automatic move (a quote read lands → quoting, Issue → proposal, a sale → sold; §5.1).

    Reloads and locks the Deal row itself, so a stale copy never moves the stage back; moves only forward along the
    ladder (`stages.forward`; a lost deal stays lost); writes one Activity row, never merged. Runs in the caller's
    transaction when there is one. Returns the caller's `deal` carrying the stage it now has.
    """
    with transaction.atomic():
        current = Deal.objects.select_for_update().get(pk=deal.pk)
        new_stage = stages.forward(current.stage, stage)
        if new_stage != current.stage:
            changed = {'stage': [current.stage, new_stage]}
            current.stage = new_stage
            current.save(update_fields=['stage', 'updated_at'])
            summary = f'Moved to {stages.label(new_stage)} ({reason})'
            entries = [activity.change(f'deal:{deal.pk}', changed)]
            activity.record(current, user, 'deal', 'updated', summary, changes=entries)
        deal.stage, deal.updated_at = current.stage, current.updated_at
    return deal


@transaction.atomic
def mark_lost(user, deal_id, reason):
    deal = locked(Deal, deal_id)
    reason = (reason or '').strip()
    if not reason:
        raise ValidationError({'reason': ['Give a reason.']})
    if len(reason) > 300:
        raise ValidationError({'reason': ['Keep the reason under 300 characters.']})
    if deal.stage == 'sold':
        return None  # the view answers 409
    before = snapshot(deal, LOST_FIELDS)
    if deal.stage != 'lost':
        deal.lost_from_stage = deal.stage
    deal.stage = 'lost'
    deal.lost_reason = reason
    deal.lost_at = clock.now()
    deal.save()
    changed = diff(before, snapshot(deal, LOST_FIELDS))
    activity.record(deal, user, 'deal', 'lost', 'Marked lost', changes=[activity.change(f'deal:{deal.id}', changed)])
    return deal


@transaction.atomic
def reopen(user, deal_id):
    deal = locked(Deal, deal_id)
    if deal.stage == 'lost':
        before = snapshot(deal, LOST_FIELDS)
        deal.stage = deal.lost_from_stage or 'intake'
        deal.lost_reason, deal.lost_at, deal.lost_from_stage = '', None, ''
        deal.save()
        changed = diff(before, snapshot(deal, LOST_FIELDS))
        entries = [activity.change(f'deal:{deal.id}', changed)]
        activity.record(deal, user, 'deal', 'reopened', 'Reopened', changes=entries)
    return deal
