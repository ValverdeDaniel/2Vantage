"""The intake's part of the review queue (plan.md §8.8; L20, B38; old 891f1b3 `IntakeQueue.jsx`, `items.py`): one item
per answer waiting, the questions in the form's order (those required to market first), then the blocks (contacts,
current coverage, lines to quote) as one item each. What we hold beside what the client sent, in words: a block's rows
as lines ("Dana Diaz (HR Admin) · dana@example.com"). Staff only.
"""

from deals import contacts as contact_roles
from deals import lines as line_vocab
from intake import client_view, form
from intake.models import Intake

from ..rules import items as item_rules
from . import queue_common as common

SECTION_LABELS = dict(form.SECTIONS)
BLOCK_LABELS = {
    client_view.CONTACTS: 'Contacts',
    client_view.COVERAGE: 'Current coverage',
    client_view.LINES: 'Lines to quote',
}
BLOCKS_SECTION = 'Contacts & coverage'
FUNDING = dict(line_vocab.FUNDING)


def _contact(row):
    head = f'{row.get("name") or "—"} ({contact_roles.label(row.get("role"))})'
    return ' · '.join(part for part in (head, row.get('title'), row.get('email'), row.get('phone')) if part)


def _coverage(row):
    renews = f'renews {row["renewal_date"]}' if row.get('renewal_date') else ''
    parts = (line_vocab.label(row.get('line')), row.get('carrier'), FUNDING.get(row.get('funding'), ''), renews)
    return ' · '.join(part for part in parts if part)


def shown(slot, value):
    """A value in words: a block as a list of lines, a list answer joined, anything else as text."""
    if slot == client_view.CONTACTS:
        return [_contact(row) for row in value or []]
    if slot == client_view.COVERAGE:
        return [_coverage(row) for row in value or []]
    if slot == client_view.LINES:
        return [line_vocab.label(key) for key in value or []]
    if isinstance(value, list):
        return ', '.join(str(part) for part in value)
    return '' if value is None else str(value)


def _order(slot):
    if slot in client_view.BLOCK_SLOTS:
        return (2, client_view.BLOCK_SLOTS.index(slot))
    question = form.BY_KEY.get(slot) or {}
    return (0 if question.get('need') == 'Q' else 1, form.KEYS.index(slot) if slot in form.KEYS else 0)


def items(deal, entries, links, now):
    intake = Intake.objects.filter(deal_id=deal.id).first()
    stored = client_view.stored(deal, intake)
    out = []
    for entry in sorted(entries, key=lambda entry: _order(entry.slot)):
        slot = entry.slot
        block = slot in client_view.BLOCK_SLOTS
        question = form.BY_KEY.get(slot) or {}
        held = stored.get(slot, [] if block else '')
        section = BLOCKS_SECTION if block else SECTION_LABELS.get(question.get('section'), '')
        change = item_rules.change(held, entry.value)
        item = common.item(entry, links, now, change=change, group=f'{section}:{change}', group_label=section)
        item.update(
            kind='block' if block else 'answer',
            label=BLOCK_LABELS.get(slot) or question.get('label') or slot,
            section=section,
            ours=shown(slot, held),
            theirs=shown(slot, entry.value),
            required=question.get('need') == 'Q',
            editable=not block,
        )
        out.append(item)
    return out
