"""The figures of priced versions not saved yet (plan.md §5.4, §7.8; F76): the dry run's preview.

`preview(line, rows, drafts)`: `rows` are the line's live plans (model rows with `replaces_ids`), `drafts` the
versions as model rows not saved (a new version, its id still None) or changed in memory (✎ re-price). Each draft is
priced the way the comparison prices a saved plan, by `packages.evaluate` over the whole line, so the preview's
figures are the ones the committed version shows: "5% off" previews its total (F76's dry run equals the commit).
"""

from dataclasses import replace

from deals import lines

from .. import packages as pk
from ..shapes import LineData
from .comparison import premium
from .state import plan_data


def figures(result):
    """What a version's draft row shows: its premium, change, credit and the enrollment that priced it."""
    return {
        'premium': premium(result),
        'change': result['change'],
        'part_of': result['part_of'],
        'credit': result['credit'],
        'enrollment_used': result['enrollment_used'],
        'enrollment_source': result['enrollment_source'],
    }


def preview(line, rows, drafts):
    """[figures] in `drafts`' order. New drafts take stand-in ids below zero for the length of the sum."""
    ids, plans = [], []
    for at, draft in enumerate(drafts):
        plan_id = draft.id if draft.id is not None else -(at + 1)
        ids.append(plan_id)
        plans.append(replace(plan_data(draft), id=plan_id))
    plans += [plan_data(row) for row in rows if row.id not in ids]
    results = pk.evaluate(LineData(lines.BY_KEY[line]['rate_basis'], plans, key=line))
    return [figures(results[plan_id]) for plan_id in ids]
