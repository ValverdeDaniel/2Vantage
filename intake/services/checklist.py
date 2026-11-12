"""The marketing checklist's ticks (plan.md §5.2, §7.6; B26, B27, C25, O.6 #2).

`set_checklist_item` is the one writer of `Intake.checklist`. Slice 41 brings it for the COBRA tick, which the Census
tab shows (census asks through this door: it never writes intake's rows); slice 40 adds the other items and the
requirement controls. Lock order: the Deal, then the Intake row (O.3.7). One Activity row (area `intake`, action
`checklist`, never merged) with the item's entry before and after under `checklist:<deal id>`, so intake's reverter
puts it back (and refuses after a later tick). Ticking an item already ticked changes nothing.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock

from .. import checklist
from . import rows

Ticked = namedtuple('Ticked', 'item entry activity')  # entry: the stored entry after the call

ACTION = 'checklist'
NOT_AN_ITEM = 'That is not a checklist item you can tick here.'
WORDS = {True: 'Ticked', False: 'Unticked'}


def target(deal_id):
    return f'checklist:{deal_id}'


def _check(item, checked):
    if item not in checklist.ATTESTED:
        raise ValidationError({'item': [NOT_AN_ITEM]})
    if not isinstance(checked, bool):
        raise ValidationError({'checked': ['Send checked as true or false.']})


@transaction.atomic
def set_checklist_item(user, deal_id, item, *, checked):
    """Tick or untick one checklist item. Returns Ticked(item, entry, Activity row or None)."""
    _check(item, checked)
    deal = rows.lock_deal(deal_id)
    intake = rows.lock_intake(deal_id)
    before = checklist.entry_of(intake.checklist, item)
    by = getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None
    after = checklist.ticked(before, checked, by, clock.now().isoformat())
    if after is None:
        return Ticked(item, before, None)
    stored = dict(intake.checklist or {})
    if after:
        stored[item] = after
    else:
        stored.pop(item, None)
    intake.checklist = stored
    intake.save(update_fields=['checklist', 'updated_at'])
    row = activity.record(
        deal,
        user,
        rows.AREA,
        ACTION,
        f'{WORDS[checked]} "{checklist.LABELS[item]}" on the marketing checklist',
        changes=[activity.change(target(deal_id), {item: [before or None, after or None]})],
    )
    return Ticked(item, after, row)


def revert(deal_id, diff):
    """Put the items of one `checklist` entry back (intake/revert.py, after the Deal and Intake locks). Returns the
    diff it wrote."""
    intake = rows.lock_intake(deal_id)
    stored, written = dict(intake.checklist or {}), {}
    for item, (before, _after) in diff.items():
        current = stored.get(item) or None
        if current == (before or None):
            continue
        if before:
            stored[item] = before
        else:
            stored.pop(item, None)
        written[item] = [current, before or None]
    if written:
        intake.checklist = stored
        intake.save(update_fields=['checklist', 'updated_at'])
    return written
