"""quotes' part of review's marks across owners (plan.md §10.7, §8.6; M88–M91; M.6 `mark_document`; slice 64).

`mark(user, deal, action, document_id=…|refs=…, at=…)` marks plan values the way `review.mark_values` does — the one
rule, `documents.review_rules.apply_mark`, then `flags` rewritten in the same statement — but records no Activity of
its own: review writes the one row for every owner (action `marked`, never merged), and its Revert hands these
entries back to quotes' own (`services.review.revert`, through `reverters['quotes']`). It names its values one of two
ways:
- `document_id`: the values read from that file that the action takes (`review_rules.takes`: Confirm all approves
  every one; ignore and check its open warnings; clear its marked values);
- `refs`: exactly those values ("plan:41:rate_ee"), whatever their state; 400 for a ref not on this deal.
The caller has locked the Deal; this locks the plans by id (O.3.7). Returns [`activity.change`] of marks, never values.
"""

from deals import activity
from documents.review_rules import apply_mark, marks_of, takes

from .. import fields, flags
from ..models import Plan
from .review import PREFIX, _named, parse_refs


def _from_file(deal, action, document_id):
    picked = []
    for plan in Plan.objects.select_for_update().filter(deal=deal).order_by('id'):
        keys = [
            key
            for key in fields.keys_for(plan.line)
            if key in plan.values
            and (plan.sources.get(key) or {}).get('doc') == document_id
            and takes(action, plan.sources.get(key))
        ]
        if keys:
            picked.append((plan, keys))
    return picked


def mark(user, deal, action, *, document_id=None, refs=None, at):
    picked = _named(deal, parse_refs(refs)) if refs is not None else _from_file(deal, action, document_id)
    by = user.id if getattr(user, 'is_authenticated', False) else None
    changes, changed = [], []
    for plan, keys in picked:
        diff = {}
        for key in keys:
            if key not in plan.values:
                continue  # a blank takes no mark
            entry = plan.sources.get(key)
            after = apply_mark(entry, action, by, at)
            if after is None:
                continue
            plan.sources[key] = after
            diff[PREFIX + key] = [marks_of(entry), marks_of(after)]
        if diff:
            flags.stamp(plan)
            changed.append(plan)
            changes.append(activity.change(f'plan:{plan.id}', diff))
    if changed:
        Plan.objects.bulk_update(changed, ['sources', 'flags'])  # bookkeeping: `updated_at` stays (§3.7)
    return changes
