"""intake's part of review's marks across owners (plan.md §10.7, §8.6; M88–M91; M.6 `mark_document`; slice 64).

`mark(user, deal, action, document_id=…|refs=…, at=…)` marks intake answers the way `marks.mark_answers` does — the
one rule, `documents.review_rules.apply_mark`, then `Intake.flags` restamped — but records no Activity of its own:
review writes the one row for every owner, and its Revert hands these entries back to intake's own (`marks.revert`,
through `reverters['intake']`). It names its answers one of two ways:
- `document_id`: the answers read from that file that the action takes (`review_rules.takes`: Confirm all approves
  every one; ignore and check its open warnings; clear its marked answers);
- `refs`: exactly those answers ("intake:fein"), whatever their state; 400 for a ref that is not an intake question.
The caller has locked the Deal; this locks the Intake row (O.3.7). A deal with no row has nothing to mark, and the
row is never made here. Marks are bookkeeping: `updated_at` stays (§3.7).
"""

from deals import activity
from documents.review_rules import apply_mark, marks_of, takes

from .. import flags, values
from ..models import Intake
from . import rows
from .marks import PREFIX, parse_refs


def mark(user, deal, action, *, document_id=None, refs=None, at):
    keys = parse_refs(refs) if refs is not None else None
    intake = Intake.objects.select_for_update().filter(deal_id=deal.id).first()
    if intake is None:
        return []
    sources = dict(intake.sources)
    if keys is None:
        keys = [k for k, entry in sources.items() if (entry or {}).get('doc') == document_id and takes(action, entry)]
    by = user.id if getattr(user, 'is_authenticated', False) else None
    diff = {}
    for key in keys:
        if values.blank(intake.answers.get(key)):
            continue  # a blank takes no mark
        entry = sources.get(key)
        after = apply_mark(entry, action, by, at)
        if after is None:
            continue
        sources[key] = after
        diff[PREFIX + key] = [marks_of(entry), marks_of(after)]
    if not diff:
        return []
    intake.sources = sources
    flags.stamp(deal, intake)
    intake.save(update_fields=['sources', 'flags'])  # bookkeeping: `updated_at` stays (§3.7)
    return [activity.change(rows.intake_target(deal.id), diff)]
