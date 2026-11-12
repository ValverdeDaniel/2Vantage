"""What a chat turn is told about the plan table and the board (plan.md §10.6; D78, D82, F109, F114; slice 24).

- `<plans>`: every live plan, line by line in the board's order, with its id, role, carrier, name, plan number,
  marks (starred, recommended, sold) and its monthly total from the Advisor's own priced figures (F114: the old
  context priced every plan with the medical count), then each value it holds as `key=value`. Capped at 120,000
  characters (D82); the plans past the cap are counted, and a pick can name only plans listed (F109, at most 150 a
  line).
- `<board>`: what the producer's Advisor board shows now (its line, filters, how many plans and which), from what the
  browser sent with the message; a board the server cannot read is left out.
Data, never instructions: the system prompt says so. Lasers are never sent (§3.8).
"""

from deals import lines

from .. import board as board_config
from .. import fields
from ..selectors.state import deal_state

MAX_CHARS = 120_000
MAX_LISTED = 150  # plans a line may list for Claude's pick (F109)
MAX_CELL = 80
NEVER = {'sl_lasers'}


def _cell(value):
    text = ' '.join(str(value or '').split()).replace('|', '/')
    return text if len(text) <= MAX_CELL else text[: MAX_CELL - 1] + '…'


def _money(amount):
    return f'${amount:,.0f}/mo' if amount is not None else 'no monthly total yet'


def _head(plan, monthly):
    marks = [
        mark for mark, on in (('starred', plan.starred), ('recommended', plan.recommended), ('SOLD', plan.sold)) if on
    ]
    parts = [f'id {plan.id}', {'alternate': 'quote'}.get(plan.role, plan.role), _cell(plan.carrier), _cell(plan.name)]
    if plan.plan_number:
        parts.append(f'no. {_cell(plan.plan_number)}')
    if plan.role == 'renewal' and plan.renews_id:
        parts.append(f'renews id {plan.renews_id}')
    parts.append(_money(monthly))
    return '- ' + ' · '.join(parts + marks)


def _values(plan, keys):
    held = plan.values or {}
    cells = [f'{key}={_cell(held[key])}' for key in keys if key not in NEVER and str(held.get(key) or '').strip()]
    return '  ' + ('; '.join(cells) if cells else '(no values)')


def tables(deal):
    """(text, {line: [listed plan ids]}): the <plans> block and the plans it lists, line by line."""
    states = deal_state(deal)
    out = ["<plans>\nMonthly totals are the Advisor's own figures. A blank value is unknown."]
    used, listed, cut = len(out[0]), {}, 0
    for line, state in states.items():
        if not state.plans:
            continue
        keys = fields.keys_for(line)
        legend = '; '.join(f'{key} = {fields.BY_KEY[key]["label"]}' for key in keys if key not in NEVER)
        block = [f'{lines.BY_KEY[line]["label"]} ({len(state.plans)} plans). Fields: {legend}']
        listed[line] = []
        for plan in state.plans:
            monthly = (state.results.get(plan.id) or {}).get('monthly')
            entry = _head(plan, monthly) + '\n' + _values(plan, keys)
            if used + len(entry) > MAX_CHARS:
                cut += 1
                continue
            block.append(entry)
            used += len(entry) + 1
            if plan.role != 'current' and len(listed[line]) < MAX_LISTED:
                listed[line].append(plan.id)
        out.append('\n'.join(block))
    if cut:
        out.append(f'({cut} plans were left out at {MAX_CHARS:,} characters: name only the plans listed.)')
    if len(out) == 1:
        out.append('(no plans on the table yet)')
    return '\n\n'.join(out) + '\n</plans>', listed


def listed(deal, line):
    """The plans of `line` a pick may name: the quoted ones the <plans> block lists."""
    return tables(deal)[1].get(line, [])


def filter_words(config):
    said = []
    if config.get('find'):
        said.append(f'finder "{config["find"]}"')
    if config.get('budget_pct') is not None:
        pct = config['budget_pct']
        said.append(f'at least {abs(pct)}% cheaper than current' if pct < 0 else f'within {pct}% of current')
    for rule in config.get('rules') or []:
        said.append(
            f'{rule["key"]} {rule["op"]} {rule["value"]}' + (f' (on {rule["line"]})' if rule.get('line') else '')
        )
    for key, words in (('ee_rate_max', 'EE rate ≤ $'), ('copay_max', 'PCP copay ≤ $')):
        if config.get(key) is not None:
            said.append(f'{words}{config[key]:,}')
    for key, value in (config.get('sliders') or {}).items():
        said.append(f'{key} slider at {value:,}')
    said += [f'hiding {key}' for key in config.get('hide') or []]
    said += [words for key, words in (('starred_only', 'starred only'), ('needs_check', 'needs checking only'),
                                      ('to_review', 'to review only')) if config.get(key)]  # fmt: skip
    if config.get('carriers'):
        said.append('carriers ' + ', '.join(config['carriers']))
    return said


def board_text(page):
    """The <board> block from what the browser sent ('' off the Advisor or for a board it cannot read)."""
    board = (page or {}).get('board')
    if not isinstance(board, dict) or board.get('line') not in lines.BY_KEY:
        return ''
    try:
        config = board_config.clean_config(board.get('config') or {}, partial=True)
    except board_config.ConfigError:
        config = {}
    shown = [int(pid) for pid in board.get('shown_ids') or [] if str(pid).isdigit()][:MAX_LISTED]
    total = board.get('total')
    filters = filter_words(config)
    lines_said = [
        f'The producer has the Advisor board open on {lines.BY_KEY[board["line"]]["label"]}.',
        f'It shows {len(shown)} of {total} quotes: ids {", ".join(str(pid) for pid in shown) or "none"}.'
        if isinstance(total, int)
        else '',
        'Filters: ' + '; '.join(filters) + '.' if filters else 'No filters are set.',
    ]
    pick = board.get('pick')
    if isinstance(pick, dict) and pick.get('label'):
        lines_said.append(f'Your pick "{_cell(pick["label"])}" is on the board.')
    return '<board>\n' + '\n'.join(line for line in lines_said if line) + '\n</board>'


def provide(deal, page):
    """The context provider: the plans, then the board."""
    text, _listed = tables(deal)
    board = board_text(page)
    return f'{text}\n\n{board}' if board else text
