"""Rows of a repeating block (plan.md §6.8; G37, G43).

A row has a stable id from `last_row_id`, never reused, so removing one moves nothing: no slot key, note or review
entry is renumbered (G82's re-keying is gone). Add refuses past the block's maximum, remove below its minimum (400);
an unknown row is a 404 (B6's fix). Removing a row removes its answers, client entries and cleared marks with it. One
Activity row each (`rows`, never merged): the row's entry before and after, and on a removal the answers it held —
before and after for ordinary answers, so Revert can rebuild it; a row of a sensitive block (Florida Blue's medical
conditions, the SIIA claimants) keeps its keys only, so its removal is not revertible.
"""

from collections import namedtuple

from django.db import transaction
from django.http import Http404
from rest_framework.exceptions import ValidationError

from deals import activity, clock

from .. import forms, slots
from ..engine.spec import get_block
from . import common

Changed = namedtuple('Changed', 'row block row_id activity facts')
ROW = 'row:'


def _block(form, block_key):
    block = get_block(form, block_key)
    if block is None:
        raise Http404('Unknown block.')
    return block


def _by(user):
    return getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None


@transaction.atomic
def add_row(user, deal_id, form_key, block_key):
    deal = common.lock_deal(deal_id)
    row, _ctx, facts = common.open_row(user, deal, form_key)
    common.refuse_locked(row)
    block = _block(forms.FORMS[form_key], block_key)
    current = list((row.rows or {}).get(block_key) or [])
    if len(current) >= block['max_rows']:
        raise ValidationError({'block': [f'This section allows at most {block["max_rows"]} rows.']})
    row.last_row_id += 1
    entry = {'id': row.last_row_id, 'origin': 'typed', 'by': _by(user), 'at': clock.now().isoformat()}
    row.rows = {**(row.rows or {}), block_key: [*current, entry]}
    common.restamp(row, facts)
    row.save(update_fields=['rows', 'last_row_id', 'flags', 'updated_at'])
    summary = f'{forms.label(form_key)}: added {block["row_label"].lower()} {len(current) + 1}'
    record = activity.record(
        deal, user, common.AREA, 'rows', summary,
        changes=[activity.change(common.target(row), {f'{ROW}{block_key}.{entry["id"]}': [None, entry]})],
    )  # fmt: skip
    return Changed(row, block_key, entry['id'], record, facts)


def _slots_of(row, block_key, row_id):
    prefix = slots.row_prefix(block_key, row_id)
    return [key for key in {*row.answers, *row.client, *row.cleared} if key.startswith(prefix)]


@transaction.atomic
def remove_row(user, deal_id, form_key, block_key, row_id):
    deal = common.lock_deal(deal_id)
    row, _ctx, facts = common.open_row(user, deal, form_key)
    common.refuse_locked(row)
    block = _block(forms.FORMS[form_key], block_key)
    current = list((row.rows or {}).get(block_key) or [])
    entry = next((r for r in current if r['id'] == row_id), None)
    if entry is None:
        raise Http404('That row is not on this form.')
    if len(current) <= block['min_rows']:
        raise ValidationError({'block': [f'This section needs at least {block["min_rows"]} row.']})
    number = current.index(entry) + 1
    gone = _slots_of(row, block_key, row_id)
    answers, sources = dict(row.answers), dict(row.sources)
    held = {slot: [answers.pop(slot), None] for slot in gone if slot in answers}
    for slot in gone:
        sources.pop(slot, None)
    row.answers, row.sources = answers, sources
    row.client = {k: v for k, v in (row.client or {}).items() if k not in gone}
    row.cleared = [s for s in row.cleared if s not in gone]
    row.rows = {**row.rows, block_key: [r for r in current if r['id'] != row_id]}
    common.restamp(row, facts)
    row.save(update_fields=['answers', 'sources', 'client', 'cleared', 'rows', 'flags', 'updated_at'])
    summary = f'{forms.label(form_key)}: removed {block["row_label"].lower()} {number}'
    diff = {f'{ROW}{block_key}.{row_id}': [entry, None], **held}
    if block.get('sensitive'):
        record = activity.record(
            deal, user, common.AREA, 'rows', summary,
            changes=[activity.change(common.keys_target(row), list(diff))], keys_only=True,
        )  # fmt: skip
    else:
        record = activity.record(
            deal, user, common.AREA, 'rows', summary, changes=[activity.change(common.target(row), diff)]
        )
    return Changed(row, block_key, row_id, record, facts)


def revert(row_activity, user, row):
    """Undo an add (remove the row while it holds nothing) or a removal (put the row back where it was, with its
    answers). Refuses after a later write to the row."""
    diff = next((e['k'] for e in row_activity.changes if isinstance(e['k'], dict)), {})
    later = {key for _target, key in activity.later_keys(row_activity)}
    if later & set(diff):
        raise activity.Refused('This row was changed after this, so this change cannot be reverted.')
    written = {}
    rows = dict(row.rows or {})
    answers, sources = dict(row.answers), dict(row.sources)
    for key, (before, after) in diff.items():
        if not key.startswith(ROW):
            continue
        block_key, _, row_id = key.removeprefix(ROW).partition('.')
        current = list(rows.get(block_key) or [])
        if after and not before:  # an add: remove it, if nothing was written into it since
            if any(s.startswith(slots.row_prefix(block_key, int(row_id))) for s in answers):
                raise activity.Refused('Answers were typed into this row after it was added; remove the row instead.')
            rows[block_key] = [r for r in current if r['id'] != int(row_id)]
        else:  # a removal: put it back in id order (rows are added in id order), with its answers
            rows[block_key] = sorted([*current, before], key=lambda r: r['id'])
            for slot, (value, _gone) in diff.items():
                if not slot.startswith(ROW) and value is not None:
                    answers[slot] = value
                    sources[slot] = {'origin': 'typed', 'by': _by(user), 'at': clock.now().isoformat()}
                    written[slot] = [None, value]
        written[key] = [after, before]
    row.rows, row.answers, row.sources = rows, answers, sources
    return row, written
