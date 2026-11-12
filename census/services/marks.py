"""Reviewing census values: approve, ignore, needs checking and clear (plan.md §7.7, §10.7; C8, E85–E88, OQ28).

`mark_values` is census's one marks writer, behind `POST deals/{id}/census/marks/` (the roster's ☑ Select cells bar and
its review bar). It names its cells one of two ways (E86):
- `refs`: exactly those cells ("census:<member id>:<key>"), whatever their state — a blank takes no mark;
- none: every open warning on the roster (for `clear`, every marked cell), so the review bar never touches more than
  it counts.
It locks the Deal, then the people by id (O.3.7), applies `documents.review_rules.apply_mark` to each source entry and
records one Activity row (action `marked`, never merged) holding each cell's marks before and after under
`mark.<key>` — marks, never the value (§3.8). Marks are bookkeeping: the person's `updated_at` stays (§3.7), and no
stored count moves (open warnings are counted on read). Revert (E88, census/revert.py) puts back the marks of the cells
still as it left them, and is refused when none is.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from documents.review_rules import ACTIONS, CLEAR, apply_mark, mark_state, marks_of, open_warning, with_marks

from .. import fields
from ..models import Member
from . import rows

Marked = namedtuple('Marked', 'action cells row')  # cells: [(member id, key)] whose marks changed

MARKED = 'marked'
PREFIX = 'mark.'
DONE = {'approve': 'Approved', 'ignore': 'Ignored', 'check': 'Flagged', 'clear': 'Unmarked'}
NOT_HERE = 'Some of those are not census cells on this deal.'
LIMIT = 5000  # cells in one request


def parse_refs(raw):
    """["census:<member id>:<key>", ...] → [(id, key)]; 400 for an empty list or a ref that is not a census cell."""
    if not isinstance(raw, list) or not raw or len(raw) > LIMIT:
        raise ValidationError({'refs': ['Name the census cells to review.']})
    found = []
    for ref in raw:
        kind, _, rest = str(ref).partition(':')
        ident, _, key = rest.partition(':')
        if kind != 'census' or not ident.isdigit() or len(ident) > 18 or key not in fields.BY_KEY:
            raise ValidationError({'refs': [NOT_HERE]})
        found.append((int(ident), key))
    return list(dict.fromkeys(found))


def _summary(action, count):
    what = 'census value' if count == 1 else 'census values'
    tail = ' as needing checking' if action == 'check' else ''
    return f'{DONE[action]} {count} {what}{tail}'


def _scoped(people, action):
    wanted = mark_state if action == CLEAR else open_warning
    return [(person.id, key) for person in people for key in fields.KEYS if wanted(person.sources.get(key))]


@transaction.atomic
def mark_values(user, deal_id, action, *, refs=None):
    """Mark census cells; returns Marked(action, [(member id, key)], Activity row or None)."""
    if action not in ACTIONS:
        raise ValidationError({'action': ['The action is approve, ignore, check or clear.']})
    cells = parse_refs(refs) if refs is not None else None
    deal = rows.lock_deal(deal_id)
    live = Member.objects.select_for_update().filter(deal_id=deal_id)
    if cells is not None:
        live = live.filter(pk__in={member_id for member_id, _key in cells})
    people = {person.id: person for person in live.order_by('id')}
    if cells is not None and any(member_id not in people for member_id, _key in cells):
        raise ValidationError({'refs': [NOT_HERE]})
    picked = cells if cells is not None else _scoped(people.values(), action)
    by = getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None
    at = clock.now().isoformat()
    diffs, changed = {}, []
    for member_id, key in picked:
        person = people[member_id]
        if not person.values.get(key):
            continue  # a blank takes no mark
        entry = person.sources.get(key)
        after = apply_mark(entry, action, by, at)
        if after is None:
            continue
        person.sources = {**person.sources, key: after}
        diffs.setdefault(member_id, {})[PREFIX + key] = [marks_of(entry), marks_of(after)]
        changed.append((member_id, key))
    if not changed:
        return Marked(action, [], None)
    Member.all_objects.bulk_update([people[member_id] for member_id in diffs], ['sources'])  # `updated_at` stays
    row = activity.record(
        deal,
        user,
        rows.AREA,
        MARKED,
        _summary(action, len(changed)),
        count=len(changed),
        changes=[activity.change(rows.target(member_id), diff) for member_id, diff in diffs.items()],
    )
    return Marked(action, changed, row)


def revert(row, user):
    """Put back the marks of one `marked` row on the cells still as it left them (E88). Runs inside
    `deals.activity.revert`'s transaction, after the Deal lock."""
    ids = sorted(int(entry['t'].partition(':')[2]) for entry in row.changes)
    people = {person.id: person for person in Member.objects.select_for_update().filter(pk__in=ids).order_by('id')}
    written, missed, touched = [], [], {}
    for entry in row.changes:
        person = people.get(int(entry['t'].partition(':')[2]))
        diff = {}
        for name, (before, after) in entry['k'].items():
            key = name.removeprefix(PREFIX)
            current = person.sources.get(key) if person else None
            if current is None or marks_of(current) != after:
                missed.append((name, key))
                continue
            person.sources = {**person.sources, key: with_marks(current, before)}
            diff[name] = [after, before]
        if diff:
            touched[person.id] = person
            written.append(activity.change(entry['t'], diff))
    if not written:
        raise activity.changed_since([fields.label(key) for _name, key in missed], [name for name, _key in missed])
    Member.all_objects.bulk_update(list(touched.values()), ['sources'])
    return written
