"""Claude's `merge_plans` (plan.md §5.4, §10.6; F142, O.6 #32; slice 22): two columns of one line that are one plan —
a rate page's row and its SBC's column, read under different names — proposed as one, through the Advisor's one merge
service (`services.merge`), so the kept plan takes each value it lacks with its file and page and the merged plans
are removed, in one revertible row.

Refused to Claude in words: a plan not on the table, plans of different lines, a sold plan on either side, the kept
plan among those merged, and the two halves of one plan filed under two numbers (`split.halves`): pairing is not
merging, halves stay two plans (D-219). Nothing is written here: the merge is an item of the turn's change set (owner
`quotes`), landed by `apply.py` when the turn ends or when the producer applies it, with ↶ Undo this run.
"""

from ai import tools
from ai.registry import Tool

from .. import fields, split
from ..models import Plan

HALVES = (
    '{a} and {b} are the two halves of one plan filed under two numbers: they stay two plans (pairing, not merging).'
)
LANDS = 'It goes on the table when your turn ends; the producer can undo it.'
WAITS = 'It waits for the producer to review and apply it.'


def label(plan):
    return f'{plan.carrier} {plan.name}'


def merge_plans(turn, data):
    keep_id = tools.integer(data.get('keep_id'), 'keep_id')
    merge_ids = list(dict.fromkeys(tools.integers(data.get('merge_ids'), 'merge_ids')))
    overwrite = [
        tools.text(key, 'An overwrite key', 60) for key in tools.listed(data.get('overwrite') or [], 'overwrite')
    ]
    if not merge_ids:
        raise tools.ToolRefused('Name at least one plan to merge into the kept one.')
    if keep_id in merge_ids:
        raise tools.ToolRefused('The kept plan cannot be merged into itself.')
    plans = {plan.id: plan for plan in Plan.objects.filter(deal=turn.deal, pk__in=[keep_id, *merge_ids])}
    missing = [str(pid) for pid in [keep_id, *merge_ids] if pid not in plans]
    if missing:
        raise tools.ToolRefused(f'There is no plan {", ".join(missing)} on this deal’s table.')
    keep, others = plans[keep_id], [plans[pid] for pid in merge_ids]
    if any(other.line != keep.line for other in others):
        raise tools.ToolRefused('Plans of different lines cannot be merged.')
    sold = [plan for plan in (keep, *others) if plan.sold]
    if sold:
        raise tools.ToolRefused(f'{label(sold[0])} is sold, so it cannot be merged.')
    for other in others:
        if split.halves(split.shape(keep), split.shape(other)):
            raise tools.ToolRefused(HALVES.format(a=label(keep), b=label(other)))
    unknown = [key for key in overwrite if key not in fields.keys_for(keep.line)]
    if unknown:
        raise tools.ToolRefused(f'"{unknown[0]}" is not a field of {label(keep)}’s line.')
    names = ', '.join(label(other) for other in others)
    turn.add(
        {
            'owner': 'quotes',
            'op': 'merge_plans',
            'plan': keep.id,
            'merge': merge_ids,
            'overwrite': overwrite,
            'line': keep.line,
            'label': f'Merge {names} into {label(keep)}',
        }
    )
    return f'Proposed: merge {names} into {label(keep)}; {names} then leave the table. {LANDS if turn.lands else WAITS}'


MERGE = Tool(
    name='merge_plans',
    owner='quotes',
    order=45,
    description=(
        'Join columns of one line that are the same plan (a rate page and its SBC read under different names) into '
        'the kept plan: it takes each value it lacks, and `overwrite` keys take the merged value even where it has '
        'one; the merged plans then leave the table. Never for two halves of one plan filed under two numbers.'
    ),
    schema=tools.schema(
        {
            'keep_id': {'type': 'integer', 'description': 'The plan id from <plans> that stays.'},
            'merge_ids': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Plan ids merged into it.'},
            'overwrite': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Field keys; may be empty.'},
        }
    ),
    run=merge_plans,
)
