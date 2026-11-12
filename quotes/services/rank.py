"""Rank's stars, written through the star rule (plan.md §5.4; D96, D97, F50, F51, F111, OQ44; slice 37).

`rank(user, deal, line, picks, among=None)` lands what Claude ranked: under the Deal lock, then the line's plans by
id, it takes off the stars Rank replaces (every star on the line, or with `among` — a filtered board — only those
among its plans: a star outside the filter stays, OQ44), then stars Claude's picks in its order, each with its reason
and the ★'s own auto-link (F51, `marks.star_on`), while `room()` holds them (`rank.rules.choose`). One Activity row,
Claude's own (it never merges with a person's stars), with every star key before and after, so Revert — and the
job's ↶ Undo this run — puts the shortlist back as it was. Refused with a sentence when none of the picks is a quoted
plan of the line, or none fits.
"""

from collections import namedtuple

from django.db import transaction

from deals import activity, clock, lines

from .. import presented, signals
from ..rank import rules
from ..selectors.state import line_data
from . import locks
from .batch import Batch
from .marks import STAR_KEYS, star_off, star_on

Ranked = namedtuple('Ranked', 'changed row starred left_out')  # plans written, Activity row or None, ids, ids

FALLBACK = 'Ranked against the client guidance'  # a pick Claude gave no words for
NO_PICK = 'Claude named no quoted plan of {line} that can be starred, so the stars are as they were.'


@transaction.atomic
def rank(user, deal, line_key, picks, among=None):
    """`picks`: [(plan id, reason)] in Claude's order; `among`: the plan ids a filtered board showed, else None."""
    deal = locks.deal(deal.id)
    rows, data = locks.line(deal, line_key)
    ids = rules.scope(data, among)
    chosen, left_out = rules.choose(data, picks, ids)
    label = lines.label(line_key)
    if not chosen:
        if left_out:
            raise activity.Refused(presented.refusal(rules.cleared(data, ids), label, 1))
        raise activity.Refused(NO_PICK.format(line=label))
    reasons = {plan_id: why or FALLBACK for plan_id, why in chosen}
    touched = [plan for plan in rows.values() if plan.id in ids and (plan.starred or plan.role != 'current')]
    batch = Batch(touched, STAR_KEYS)
    for (
        plan
    ) in touched:  # a pick already starred for the same reason keeps its star as it is: the same rank writes nothing
        if plan.starred and reasons.get(plan.id) != plan.star_reason:
            star_off(plan)
    after = line_data(line_key, list(rows.values()))
    now, field_set = clock.now(), lines.BY_KEY[line_key]['field_set']
    for plan_id, why in reasons.items():
        if not rows[plan_id].starred:
            star_on(rows[plan_id], user, why, now, after, field_set)
    changed, changes = batch.write()
    starred = [plan_id for plan_id, _why in chosen]
    if not changes:
        return Ranked([], None, starred, left_out)
    signals.changed(deal.id, [line_key])
    count = len(starred)
    summary = f'Ranked the {label} plans against the client guidance: starred {count} plan{"s" if count != 1 else ""}'
    row = activity.record(deal, user, 'quotes', 'updated', summary, len(changed), changes=changes, actor_kind='claude')
    return Ranked(changed, row, starred, left_out)
