"""`Plan.flags`: a plan's open warnings, a stored count (plan.md §3.7, §5.4; O.3.7, OQ9 c, Q.3 #9).

The count is the plan's `to_check` statuses over its line's fields, so it is `documents.review_rules.open_warning`
(OQ28) and nothing else: the board's `facts.flags`, the station's strip and the stored count can never disagree.
It is rewritten in the same transaction as every write that changes a plan's values or sources: `Plan.save()` stamps
it, and the services that save with `bulk_update` (moves, marks, the locator's answers) call `stamp` and write
`flags` with their own columns. `rebuild` is registered in `deals.stored_counts`, so `manage.py rebuild_facts` (backend,
the composition root) reports any difference and, with `--fix`, writes the right count.
"""

from . import facts

TO_CHECK = 'to_check'  # facts.statuses' word for an open warning


def count(line, values, sources):
    """The open warnings on a plan's values: its `to_check` statuses."""
    return sum(1 for state in facts.statuses(line, values, sources).values() if state == TO_CHECK)


def stamp(plan):
    """Set `plan.flags` from its values and sources, in memory. True when the count changed."""
    fresh = count(plan.line, plan.values or {}, plan.sources or {})
    if fresh == plan.flags:
        return False
    plan.flags = fresh
    return True


def rebuild(deal_ids=None, write=False):
    """[(f'plan:{id}', stored, rebuilt)] for every plan (removed ones too) whose stored count is wrong; with `write`,
    the right counts are saved (only `flags`: a rebuild changes no value and moves no `updated_at`)."""
    from .models import Plan

    plans = Plan.all_objects.only('id', 'line', 'values', 'sources', 'flags').order_by('id')
    if deal_ids is not None:
        plans = plans.filter(deal_id__in=deal_ids)
    wrong, differences = [], []
    for plan in plans.iterator(chunk_size=500):
        stored = plan.flags
        if stamp(plan):
            differences.append((f'plan:{plan.id}', stored, plan.flags))
            wrong.append(plan)
    if write and wrong:
        Plan.all_objects.bulk_update(wrong, ['flags'], batch_size=500)
    return differences
