"""The marketing checklist's controls (plan.md §5.2, §7.6; B26, B27, C25, O.6 #2).

`set_checklist_item` is the one writer of `Intake.checklist`: the "On file" / "Confirmed" tick (with an optional
note), and the requirement — Not needed (`waived`), Still needed ▸ (`required`, with a note the client sees) or Undo
(''). Each half writes only when sent, so a tick never clobbers a requirement and the reverse (the old door's rule).
The Census tab ticks COBRA through it (C25); census never writes intake's rows. The two derived items (coverage
intent, census) take neither: their escape is Market anyway (B34).

Lock order: the Deal, then the Intake row (O.3.7). One Activity row (area `intake`, action `checklist`, never merged)
with the item's entry before and after under `checklist:<deal id>`, so intake's reverter puts it back (and refuses
after a later change to the item). A change that changes nothing writes nothing.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock

from .. import checklist
from . import rows

Ticked = namedtuple('Ticked', 'item entry activity')  # entry: the stored entry after the call

ACTION = 'checklist'
UNSET = object()
NOT_AN_ITEM = 'That is not a checklist item you can tick here.'
NOTHING_SENT = 'Send checked, or a requirement.'
WORDS = {True: 'Ticked', False: 'Unticked'}
REQUIREMENT_WORDS = {
    checklist.WAIVED: 'Marked "{label}" not needed',
    checklist.REQUIRED: 'Marked "{label}" still needed',
    '': 'Restored the usual rule for "{label}"',
}


def target(deal_id):
    return f'checklist:{deal_id}'


def _text(name, value):
    if value is None:
        return ''
    if not isinstance(value, str):
        raise ValidationError({name: ['Send text.']})
    text = ' '.join(value.split())
    if len(text) > checklist.NOTE_LIMIT:
        raise ValidationError({name: [f'Keep the note under {checklist.NOTE_LIMIT} characters.']})
    return text


def _check(item, checked, requirement):
    if item not in checklist.ATTESTED:
        raise ValidationError({'item': [NOT_AN_ITEM]})
    if checked is UNSET and requirement is UNSET:
        raise ValidationError({'non_field_errors': [NOTHING_SENT]})
    if checked is not UNSET and not isinstance(checked, bool):
        raise ValidationError({'checked': ['Send checked as true or false.']})
    if requirement is not UNSET and requirement not in checklist.REQUIREMENTS:
        raise ValidationError({'requirement': ['Send required, waived, or an empty requirement.']})


def _summary(item, before, after, checked, requirement):
    label = checklist.LABELS[item]
    parts = []
    if checked is not UNSET and bool(before.get('checked')) != bool(after.get('checked')):
        parts.append(f'{WORDS[checked]} "{label}"')
    if requirement is not UNSET and (before.get('requirement') or '') != (after.get('requirement') or ''):
        parts.append(REQUIREMENT_WORDS[requirement].format(label=label))
    if not parts:
        parts.append(f'Edited "{label}"')
    return f'{" · ".join(parts)} on the marketing checklist'


@transaction.atomic
def set_checklist_item(user, deal_id, item, *, checked=UNSET, note=None, requirement=UNSET, client_note=''):
    """Tick or untick one item, and/or set its requirement. Returns Ticked(item, entry, Activity row or None)."""
    _check(item, checked, requirement)
    note = None if note is None else _text('note', note)
    client_note = _text('client_note', client_note)
    deal = rows.lock_deal(deal_id)
    intake = rows.lock_intake(deal_id)
    before = checklist.entry_of(intake.checklist, item)
    after = dict(before)
    if checked is not UNSET:
        by = getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None
        changed = checklist.ticked(after, checked, by, clock.now().isoformat(), note)
        after = after if changed is None else changed
    if requirement is not UNSET:
        changed = checklist.required_as(after, requirement, client_note)
        after = after if changed is None else changed
    if after == before:
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
        _summary(item, before, after, checked, requirement),
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
