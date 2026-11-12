"""Stamping option numbers (plan.md §5.4, §7.12; J159, J.6.4, OQ35): the one writer of `Plan.option_number`.

Issue calls it inside its own transaction, under the Deal lock, with the plans it presents in the order the client
reads them (`proposals.numbering.reading_ids`); every draft before that shows the same numbers, worked out by
`labels.numbers`, so what a draft predicts is what Issue stamps. Locks the Deal, then the plans by id; a plan already
numbered keeps its number, so the same call twice writes nothing. Current plans and priced versions take none.

It records no Activity of its own: a number is a one-time stamp (N.3 #4) that rides the issue that made it, and the
caller records that issue with the numbers it returns.
"""

from django.db import transaction
from django.db.models import Max

from .. import labels
from ..models import Plan
from ..selectors.state import plan_data
from . import locks


def _tops(deal, line_keys):
    """{line: the highest number stored on it}, removed plans included (a number is never reused)."""
    rows = (
        Plan.all_objects.filter(deal=deal, line__in=line_keys)
        .order_by()
        .values_list('line')
        .annotate(top=Max('option_number'))
    )
    return {line: top or 0 for line, top in rows}


@transaction.atomic
def stamp_option_numbers(deal, ordered_ids):
    """Stamp the plans `ordered_ids` names (in reading order, line by line) that take a number and have none.
    Returns {plan id: number} for the plans it stamped."""
    deal = locks.deal(deal.id)
    ordered = list(dict.fromkeys(int(pid) for pid in ordered_ids))
    if not ordered:
        return {}
    rows = {plan.id: plan for plan in locks.plans(deal, ordered)}
    tops = _tops(deal, {plan.line for plan in rows.values()})
    stamped = {}
    for line, top in tops.items():
        plans = [rows[pid] for pid in ordered if rows[pid].line == line]
        stored = {plan.id: plan.option_number for plan in plans if plan.option_number}
        found = labels.numbers([plan_data(plan) for plan in plans], stored, top)
        stamped.update({pid: n for pid, n in found.items() if pid not in stored})
    changed = [rows[pid] for pid in stamped]
    for plan in changed:
        plan.option_number = stamped[plan.id]
    Plan.objects.bulk_update(changed, ['option_number'])
    return stamped
