"""Claude's `pair_plans` (plan.md §5.4, §10.6; D-219, J15, J161, O.6 #4; slice 37; the old ai/table_agent.py
`PAIR_PLANS_TOOL` at 891f1b3): one plan a carrier files under two plan numbers (Florida Blue's 05182 and 05183: one
holds the employee-only figures and rate, the other the dependent tiers) prints as ONE column in the client files,
while both stay columns on the table; `split: true` prints a pair as two columns again.

Checked here as the pair service checks it, each refusal in its own words, so Claude can act on it: both plans on the
deal's table, not one plan twice, one line, one carrier, one kind (two current plans, or two quotes: a current pair's
renewals follow it), neither already paired. Nothing is written here: the pair is an item of the turn's change set
(owner `quotes`), landed by `apply.py` through `services.pair_plans` / `split_pair` (one revertible `plan.pair_of`
row each) when the turn ends or when the producer applies it, with ↶ Undo this run.
"""

from ai import tools
from ai.registry import Tool
from deals import activity, lines

from .. import pairs
from ..models import Plan
from ..selectors.state import line_state
from ..services.pairs import check

LANDS = 'It goes on the table when your turn ends; the producer can undo it.'
WAITS = 'It waits for the producer to review and apply it.'


def label(plan):
    return f'{plan.carrier} {plan.name}'.strip()


def _plans(turn, ids):
    found = {plan.id: plan for plan in Plan.objects.filter(deal=turn.deal, pk__in=ids)}
    missing = [str(pid) for pid in ids if pid not in found]
    if missing:
        raise tools.ToolRefused(f'There is no plan {", ".join(missing)} on this deal’s table.')
    return found


def _staged(turn, ids):
    return any({item['plan'], item.get('with')} & set(ids) for item in turn.staged('quotes', 'pair_plans'))


def _split(turn, plan):
    partner = pairs.partner(line_state(turn.deal, plan.line).data, plan.id)
    if partner is None:
        raise tools.ToolRefused(f'{label(plan)} is not printed as one column with another plan.')
    other = Plan.objects.get(pk=partner)
    turn.add(
        {
            'owner': 'quotes',
            'op': 'split_pair',
            'plan': plan.id,
            'with': other.id,
            'line': plan.line,
            'label': f'Print {label(plan)} and {label(other)} as two columns again',
        }
    )
    return f'Proposed: {label(plan)} and {label(other)} print as two columns again. {LANDS if turn.lands else WAITS}'


def pair_plans(turn, data):
    ids = list(dict.fromkeys(tools.integers(data.get('plan_ids'), 'plan_ids')))
    split = tools.boolean(data.get('split', False), 'split')
    if split:
        if not ids:
            raise tools.ToolRefused('Name one plan of the pair to split (plan_ids).')
        return _split(turn, _plans(turn, ids[:1])[ids[0]])
    if len(ids) != 2:
        raise tools.ToolRefused('Name the two plans to print as one column (plan_ids), the first one first.')
    found = _plans(turn, ids)
    first, second = found[ids[0]], found[ids[1]]
    try:
        check(first, second)
    except activity.Refused as exc:
        raise tools.ToolRefused(exc.sentence) from None
    held = pairs.stored(line_state(turn.deal, first.line).data)
    if {first.id, second.id} in [set(pair) for pair in held]:
        return f'{label(first)} and {label(second)} already print as one column, so nothing changes.'
    taken = [plan for plan in (first, second) if any(plan.id in pair for pair in held)]
    if taken or _staged(turn, ids):
        names = ' and '.join(label(plan) for plan in taken) or 'One of them'
        raise tools.ToolRefused(f'{names} already prints as one column with another plan: split it first.')
    turn.add(
        {
            'owner': 'quotes',
            'op': 'pair_plans',
            'plan': first.id,
            'with': second.id,
            'line': first.line,
            'label': f'Print {label(first)} and {label(second)} as one column ({lines.label(first.line)})',
        }
    )
    return (
        f'Proposed: {label(first)} and {label(second)} print as one column in the client documents; both stay columns '
        f'on this table. {LANDS if turn.lands else WAITS}'
    )


PAIR = Tool(
    name='pair_plans',
    owner='quotes',
    order=60,
    description=(
        'Print two plans as ONE column in the client documents (the PDF, the PowerPoint and the client spreadsheet) '
        'while both stay columns on the table: for one plan a carrier files as two numbers, one holding the '
        'employee-only figures and rate and the other the dependent tiers. Both on one line, from one carrier, both '
        'current or both quotes; a current pair’s renewals follow it. The first id keeps the column’s place. '
        'split: true (with either plan of the pair) prints them as two columns again. Never merge_plans them.'
    ),
    schema=tools.schema(
        {
            'plan_ids': {
                'type': 'array',
                'items': {'type': 'integer'},
                'description': 'The two plan ids from <plans>, first one first; for split, either plan of the pair.',
            },
            'split': {'type': 'boolean', 'description': 'True to print a pair as two columns again.'},
        }
    ),
    run=pair_plans,
)
