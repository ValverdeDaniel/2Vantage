"""census's part of review's marks across owners (plan.md §10.7, §8.6; M88–M91; M.6 `mark_document`; slice 64).

`mark(user, deal, action, document_id=…|refs=…, at=…)` marks census cells the way `marks.mark_values` does — the one
rule, `documents.review_rules.apply_mark` — but records no Activity of its own: review writes the one row for every
owner, holding marks, never a value (§3.8), and its Revert hands these entries back to census's own
(`marks.revert`, through `reverters['census']`). It names its cells one of two ways:
- `document_id`: the cells read or imported from that file that the action takes (`review_rules.takes`: Confirm all
  approves every one, census included; ignore and check its open warnings; clear its marked cells);
- `refs`: exactly those cells ("census:<member id>:<key>"), whatever their state; 400 for one not on this deal.
The caller has locked the Deal; this locks the people by id (O.3.7). Marks are bookkeeping: `updated_at` stays and no
stored count moves (open warnings are counted on read).
"""

from rest_framework.exceptions import ValidationError

from deals import activity
from documents.review_rules import apply_mark, marks_of, takes

from .. import fields
from ..models import Member
from . import rows
from .marks import NOT_HERE, PREFIX, parse_refs


def mark(user, deal, action, *, document_id=None, refs=None, at):
    cells = parse_refs(refs) if refs is not None else None
    live = Member.objects.select_for_update().filter(deal_id=deal.id)
    if cells is not None:
        live = live.filter(pk__in={member_id for member_id, _key in cells})
    people = {person.id: person for person in live.order_by('id')}
    if cells is not None and any(member_id not in people for member_id, _key in cells):
        raise ValidationError({'refs': [NOT_HERE]})
    if cells is None:
        cells = [
            (person.id, key)
            for person in people.values()
            for key in fields.KEYS
            if (person.sources.get(key) or {}).get('doc') == document_id and takes(action, person.sources.get(key))
        ]
    by = user.id if getattr(user, 'is_authenticated', False) else None
    diffs = {}
    for member_id, key in cells:
        person = people[member_id]
        if not person.values.get(key):
            continue  # a blank takes no mark
        entry = person.sources.get(key)
        after = apply_mark(entry, action, by, at)
        if after is None:
            continue
        person.sources = {**person.sources, key: after}
        diffs.setdefault(member_id, {})[PREFIX + key] = [marks_of(entry), marks_of(after)]
    if diffs:
        Member.all_objects.bulk_update([people[member_id] for member_id in diffs], ['sources'])  # `updated_at` stays
    return [activity.change(rows.target(member_id), diff) for member_id, diff in diffs.items()]
