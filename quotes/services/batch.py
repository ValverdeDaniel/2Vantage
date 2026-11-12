"""Writing a rule's changes to several plans at once (plan.md §3.7, O.3.2, C24).

A `Batch` remembers the plans' columns before the rule changes them in memory; `write()` saves only the plans that
changed, with one `bulk_update` of only the columns the rule owns (and their `replaces` sets), and returns them with
the Activity `changes` holding each key's before and after. Nothing changed, nothing written.
"""

from deals import activity, clock

from .. import columns
from ..models import Plan


class Batch:
    def __init__(self, plans, keys):
        self.keys = tuple(keys)
        self.plans = {plan.id: plan for plan in plans}
        self.before = {plan.id: self._now(plan) for plan in plans}

    def _now(self, plan):
        return columns.snapshot(plan, self.keys, plan.replaces_ids)

    def diffs(self):
        out = {}
        for plan_id, plan in self.plans.items():
            diff = columns.diff(self.before[plan_id], self._now(plan))
            if diff:
                out[plan_id] = diff
        return out

    def write(self):
        """([changed plans], [Activity changes]) after saving them."""
        diffs = self.diffs()
        if not diffs:
            return [], []
        changed = [self.plans[plan_id] for plan_id in sorted(diffs)]
        now = clock.now()
        for plan in changed:
            plan.updated_at = now
        written = {key for diff in diffs.values() for key in diff}
        Plan.objects.bulk_update(changed, [*columns.fields_of(written), 'updated_at'])
        for plan in changed:
            if columns.REPLACES in diffs[plan.id]:
                plan.replaces.set(plan.replaces_ids)
        return changed, [activity.change(f'plan:{plan.id}', diffs[plan.id]) for plan in changed]
