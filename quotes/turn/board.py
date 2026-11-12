"""Claude's `set_board`: what the Advisor's plan board shows (plan.md §10.6; D80, F24, F25, F108–F110; slice 24; the
old scan_chat SET_BOARD_TOOL, `board_patch` and `_tool_pick` at 891f1b3).

It writes nothing (D80). Each call is a patch in the board's own words (F110: the keys are the config's, named after
the fields, so "network" and the medical caps mean what the board means): only what Claude names changes, `clear`
starts from no filters, and every key is checked by `board.clean_config` — the same cleaner a saved setup passes —
so a key the board has no control for is refused in words. Claude's `pick` (F25) names plans it judged a match on
one line; its ids are cut to the plans the context listed for that line (F109), and it rides beside the config,
never in it, so it is never saved. The turn keeps the patch (`turn.board`); the browser applies it when the turn ends
(F108).
"""

from ai import tools
from ai.registry import Tool
from deals import lines

from .. import board as board_config
from .. import board_presets as presets
from . import table

MAX_PICK_LABEL = 40
MAX_PICK_KEYS = 4
BUDGETS = ['', *(str(rung['value']) for rung in presets.BUDGET if rung['value'] is not None)]
CAPS = ('ee_rate_max', 'copay_max')

RULE = tools.schema(
    {
        'key': {'type': 'string', 'description': "A field key from <plans>, or 'total' (the monthly total)."},
        'op': {'type': 'string', 'enum': [op['key'] for op in presets.RULE_OPS]},
        'value': {'type': 'string', 'description': 'A number for a number column, else the phrase.'},
        'line': {'type': 'string', 'enum': ['', *lines.LINE_KEYS], 'description': "'' applies on every line."},
    }
)
PROPERTIES = {
    'line': {'type': 'string', 'enum': list(lines.LINE_KEYS), 'description': 'The line of coverage to show.'},
    'clear': {'type': 'boolean', 'description': 'Reset every filter (and your pick) before the rest applies.'},
    'find': {'type': 'string', 'description': "The finder's words (name, number, carrier, network, type); '' clears."},
    'budget_pct': {
        'type': 'string',
        'enum': BUDGETS,
        'description': "Within N% of the current plans' cost ('5', '10', '15'), at least N% cheaper ('-5', '-10', "
        "'-15'), or '' for any budget.",
    },
    'rules': {
        'type': 'array',
        'items': RULE,
        'description': "Column rules; they replace the board's rules and [] removes them. Numbers take < <= > >= =, "
        'text takes contains or excludes. A blank cell never meets a rule.',
    },
    'ee_rate_max': {'type': 'number', 'description': 'The highest employee-only monthly rate; 0 removes it.'},
    'copay_max': {'type': 'number', 'description': 'The highest primary-care copay; 0 removes it.'},
    'hide': {'type': 'array', 'items': {'type': 'string', 'enum': [hide['key'] for hide in presets.HIDES]}},
    'starred_only': {'type': 'boolean'},
    'carriers': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Show only these carriers; [] all.'},
    'preset': {'type': 'string', 'enum': [key for key, _label in presets.PRESETS], 'description': 'The columns.'},
    'sort': tools.schema(
        {
            'key': {'type': 'string', 'description': "'proposal' (the client's order), 'total' or a field key."},
            'dir': {'type': 'integer', 'enum': [1, -1], 'description': '1 lowest first, -1 highest first.'},
        }
    ),
    'pick': tools.schema(
        {
            'label': {'type': 'string', 'description': "What they share, 2-5 words; '' removes your pick."},
            'plan_ids': {'type': 'array', 'items': {'type': 'integer'}},
            'keys': {'type': 'array', 'items': {'type': 'string'}, 'description': 'The column keys you judged on.'},
        }
    ),
}


def _rules(raw, line):
    out = []
    for rule in tools.objects(raw, 'rules'):
        cleaned = {key: rule.get(key) for key in ('key', 'op', 'value')}
        on = tools.text(rule.get('line'), 'A rule’s line', 20)
        if not on and cleaned['key'] == presets.TOTAL:
            on = line  # the monthly total is capped per line (F19)
        if on:
            cleaned['line'] = on
        out.append(cleaned)
    return out


def _patch(data, line):
    patch = {}
    if 'find' in data:
        patch['find'] = tools.text(data['find'], 'The finder', board_config.MAX_FIND)
    if 'budget_pct' in data:
        patch['budget_pct'] = None if data['budget_pct'] in ('', None) else tools.number(data['budget_pct'], 'Budget')
    if 'rules' in data:
        patch['rules'] = _rules(data['rules'], line)
    for key in CAPS:
        if key in data:
            amount = tools.number(data[key], key)
            patch[key] = amount if amount > 0 else None
    if 'hide' in data:
        patch['hide'] = tools.listed(data['hide'], 'hide')
    if 'starred_only' in data:
        patch['starred_only'] = tools.boolean(data['starred_only'], 'starred_only')
    if 'carriers' in data:
        patch['carriers'] = [
            tools.text(name, 'A carrier', board_config.MAX_CARRIER)
            for name in tools.listed(data['carriers'], 'carriers')
        ]
    if 'preset' in data:
        patch['preset'] = tools.text(data['preset'], 'preset', 20)
    if 'sort' in data:
        sort = tools.objects([data['sort']], 'sort')[0]
        patch['sort'] = {
            'key': tools.text(sort.get('key'), 'The sort', 60),
            'dir': tools.integer(sort.get('dir', 1), 'dir'),
        }
    try:
        return board_config.clean_config(patch, partial=True)
    except board_config.ConfigError as exc:
        raise tools.ToolRefused(' '.join(exc.errors.values())) from None


def _pick(deal, raw, line):
    pick = tools.objects([raw], 'pick')[0] if raw not in (None, '') else {}
    label = tools.text(pick.get('label'), 'The pick’s label', 200)[:MAX_PICK_LABEL]
    if not label:
        return None
    listed = table.listed(deal, line)
    wanted = tools.integers(pick.get('plan_ids') or [], 'plan_ids')
    keys = [key for key in tools.listed(pick.get('keys') or [], 'keys') if board_config.rule_kind(key)]
    return {
        'label': label,
        'line': line,
        'plan_ids': [pid for pid in wanted if pid in listed],
        'judged_ids': listed,
        'keys': keys[:MAX_PICK_KEYS],
    }


def _words(board, pick_set):
    line = lines.BY_KEY[board['line']]['label'] if board.get('line') in lines.BY_KEY else 'its line'
    said = table.filter_words(board['config'])
    if board['config'].get('preset'):
        said.append(f'the {board["config"]["preset"]} columns')
    if board['config'].get('sort'):
        sort = board['config']['sort']
        said.append(f'sorted by {sort["key"]} {"highest" if sort["dir"] == -1 else "lowest"} first')
    if pick_set and board.get('pick'):
        said.append(f'your pick "{board["pick"]["label"]}" ({len(board["pick"]["plan_ids"])} plans)')
    start = 'from no filters, ' if board.get('clear') else ''
    return (
        f'The board will show {line} {start}with '
        + ('; '.join(said) if said else 'no filters')
        + ' once your turn ends. Nothing on the deal changes.'
    )


def set_board(turn, data):
    line = tools.text(data.get('line'), 'line', 20)
    if line and line not in lines.BY_KEY:
        raise tools.ToolRefused(f'"{line}" is not a line of coverage.')
    shown = (turn.page.get('board') or {}).get('line')
    target = line or (turn.board or {}).get('line') or (shown if shown in lines.BY_KEY else '') or 'medical'
    patch = _patch(data, target)
    clear = tools.boolean(data.get('clear', False), 'clear')
    if turn.board is None or clear:
        turn.board = {'line': '', 'clear': clear, 'config': {}}
    turn.board['line'] = line or turn.board['line'] or target
    turn.board['config'].update(patch)
    if 'pick' in data:
        turn.board['pick'] = _pick(turn.deal, data['pick'], target)
    return _words(turn.board, 'pick' in data)


TOOL = Tool(
    name='set_board',
    owner='quotes',
    order=20,
    description=(
        "Change what the Advisor's plan board shows: its line, the finder, the budget, column rules, caps, hides, "
        'carriers, columns, sort and your pick. Pass only what should change; clear=true resets every filter first. '
        'It never changes any data, and it opens the board.'
    ),
    schema=tools.schema(PROPERTIES, required=[]),
    run=set_board,
)
