"""Claude's changes to the plan table, proposed in a chat turn (plan.md §10.6; D85, D86, D88, D92, F61; slice 24).

- `propose_changes`: `set_values` (explicit values per plan, each cleaned per cell by the Advisor's own cleaner, D92;
  a value the producer stated is `dictated` and lands as typed, D85; one equal to the table's writes nothing, D60) and
  `remove_plan` (D86: a sold or recommended plan is refused). Each plan's values are checked as they would stand
  (`read_checks.for_values`, D88), and the checks go back to Claude with the answer.
- `clear_line`: every quoted plan of one line removed (the Advisor's Clear, F61); current and sold plans stay.
Nothing is written here: each change is an item of the turn's change set (owner `quotes`), which lands through
`apply.py` when the turn ends or when the producer applies it.
"""

from rest_framework.exceptions import ValidationError

from ai import tools
from ai.registry import Tool
from deals import lines

from .. import fields, read_checks
from ..models import Plan
from ..services.plans import clean_values

OPS = ('set_values', 'remove_plan')
MAX_CHANGES = 60
MAX_VALUE = 500
LANDS = 'They go on the table when your turn ends; the producer can undo them.'
WAITS = 'They wait for the producer to review and apply them.'


def label(plan):
    return f'{plan.carrier} {plan.name}'


def _cleaned(plan, key, raw):
    """The value as the table would store it, or ToolRefused naming the problem."""
    if key not in fields.keys_for(plan.line) or key == 'sl_lasers':
        raise tools.ToolRefused(f'{label(plan)}: "{key}" is not a field of its line.')
    try:
        return clean_values(plan.line, {key: raw})[key]
    except ValidationError as exc:
        problem = exc.detail.get('values', exc.detail) if isinstance(exc.detail, dict) else exc.detail
        if isinstance(problem, dict):
            problem = problem.get(key, problem)
        if isinstance(problem, list):
            problem = problem[0] if problem else ''
        raise tools.ToolRefused(f'{label(plan)}: {fields.BY_KEY[key]["label"]}: {problem}') from None


def _values(turn, plan, raw_values, refused):
    staged = []
    for raw in tools.objects(raw_values, 'values'):
        key = tools.text(raw.get('key'), 'A value’s key', 60)
        try:
            value = _cleaned(plan, key, tools.text(raw.get('value'), 'A value', MAX_VALUE))
        except tools.ToolRefused as exc:
            refused.append(exc.sentence)
            continue
        old = (plan.values or {}).get(key, '')
        if value == old:
            continue
        staged.append(
            {
                'key': key,
                'label': fields.BY_KEY[key]['label'],
                'old': old,
                'new': value,
                'dictated': tools.boolean(raw.get('dictated', False), 'dictated'),
            }
        )
    if not staged:
        return []
    item = next((i for i in turn.staged('quotes', 'set_values') if i['plan'] == plan.id), None)
    if item is None:
        item = turn.add({'owner': 'quotes', 'op': 'set_values', 'plan': plan.id, 'line': plan.line, 'values': []})
    by_key = {value['key']: value for value in item['values']}
    by_key.update({value['key']: value for value in staged})
    item['values'] = list(by_key.values())
    count = len(item['values'])
    item['label'] = f'{label(plan)}: {count} value{"s" if count != 1 else ""}'
    return staged


def _remove(turn, plan, reason, refused):
    if plan.sold:
        refused.append(f'{label(plan)} is sold, so it stays.')
        return False
    if plan.recommended:
        refused.append(f'{label(plan)} is recommended for the client, so it stays: the producer can un-recommend it.')
        return False
    if any(item['plan'] == plan.id for item in turn.staged('quotes', 'remove_plan')):
        return False
    turn.add(
        {
            'owner': 'quotes',
            'op': 'remove_plan',
            'plan': plan.id,
            'line': plan.line,
            'label': f'Remove {label(plan)} ({lines.BY_KEY[plan.line]["label"]})',
            'reason': reason,
        }
    )
    return True


def propose_changes(turn, data):
    changes = tools.objects(data.get('changes'), 'changes')
    if not changes:
        raise tools.ToolRefused('Name at least one change.')
    if len(changes) > MAX_CHANGES:
        raise tools.ToolRefused(f'Propose at most {MAX_CHANGES} changes at once.')
    ids = [tools.integer(change.get('plan_id'), 'plan_id') for change in changes]
    plans = {plan.id: plan for plan in Plan.objects.filter(deal=turn.deal, pk__in=ids)}
    done, refused, checks = [], [], []
    for change, plan_id in zip(changes, ids, strict=True):
        op, plan = tools.text(change.get('op'), 'op', 20), plans.get(plan_id)
        if plan is None:
            refused.append(f'There is no plan {plan_id} on this deal’s table.')
        elif op not in OPS:
            refused.append(f'"{op}" is not a change: use set_values or remove_plan.')
        elif op == 'remove_plan':
            if _remove(turn, plan, tools.text(change.get('reason'), 'reason', 300), refused):
                done.append(f'remove {label(plan)}')
        elif plan.sold:
            refused.append(f'{label(plan)} is sold: its values stay as they were sold.')
        else:
            staged = _values(turn, plan, change.get('values') or [], refused)
            if staged:
                done.append(f'{len(staged)} value{"s" if len(staged) != 1 else ""} on {label(plan)}')
                checks += read_checks.for_values(plan, {value['key']: value['new'] for value in staged})
    for check in checks:
        turn.finding(check['text'], check['hard'])
    words = [f'Proposed: {"; ".join(done)}. {LANDS if turn.lands else WAITS}' if done else 'Nothing changes.']
    if refused:
        words.append('Not proposed: ' + ' '.join(refused))
    if checks:
        words.append('Checks: ' + '; '.join(check['text'] for check in checks))
    return '\n'.join(words)


def clear_line(turn, data):
    line = tools.text(data.get('line'), 'line', 20)
    if line not in lines.BY_KEY:
        raise tools.ToolRefused(f'"{line}" is not a line of coverage.')
    going = list(Plan.objects.filter(deal=turn.deal, line=line).exclude(role='current').exclude(sold=True))
    if not going:
        raise tools.ToolRefused(f'{lines.BY_KEY[line]["label"]} has no quoted plans to clear.')
    if turn.staged('quotes', 'clear_line') and any(
        item['line'] == line for item in turn.staged('quotes', 'clear_line')
    ):
        return 'That line is already being cleared.'
    count = len(going)
    turn.add(
        {
            'owner': 'quotes',
            'op': 'clear_line',
            'line': line,
            'plans': [plan.id for plan in going],
            'label': f'Clear {lines.BY_KEY[line]["label"]}: remove {count} quoted plan{"s" if count != 1 else ""}',
        }
    )
    return (
        f'Proposed: clear {lines.BY_KEY[line]["label"]}, removing {count} quoted plans; current and sold plans stay. '
        f'{LANDS if turn.lands else WAITS}'
    )


VALUE = tools.schema(
    {
        'key': {'type': 'string', 'description': 'A field key of the plan’s line, from <plans>.'},
        'value': {'type': 'string', 'description': "The value as printed or said; '' clears it."},
        'dictated': {'type': 'boolean', 'description': 'True when the producer stated it.'},
    }
)
CHANGE = tools.schema(
    {
        'op': {'type': 'string', 'enum': list(OPS)},
        'plan_id': {'type': 'integer', 'description': 'A plan id from <plans>.'},
        'values': {'type': 'array', 'items': VALUE, 'description': 'set_values only; [] for remove_plan.'},
        'reason': {'type': 'string', 'description': 'Why, in a few words (for remove_plan); may be empty.'},
    }
)
PROPOSE = Tool(
    name='propose_changes',
    owner='quotes',
    order=30,
    description=(
        'Change the plan table: set_values writes values on a plan, remove_plan removes one. Sold and recommended '
        'plans are never removed. The answer says whether the changes land when your turn ends or wait for review.'
    ),
    schema=tools.schema({'changes': {'type': 'array', 'items': CHANGE}}),
    run=propose_changes,
)
CLEAR = Tool(
    name='clear_line',
    owner='quotes',
    order=40,
    description='Remove every quoted plan on one line of coverage, to start over. Current and sold plans stay.',
    schema=tools.schema({'line': {'type': 'string', 'enum': list(lines.LINE_KEYS)}}),
    run=clear_line,
)
