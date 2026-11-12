"""The recommendation pages (plan.md §9.5; J136, J165; old Vantage 891f1b3 `proposal_presentation._recommendation_
pages` and `_several_recommendations_page`, `proposal_pdf._why_for`, KEEP_CURRENT_WORDS). Pure.

One plan answering the line (or each current plan, one answer each): the WE RECOMMEND panel, the plan on the brand's
navy with its option number, its carrier and what it replaces, its figures beside it (the line's card stats, the
monthly and annual premium, the change from today), and "Why we recommend it." under them. Several current plans, or
several plans answering one (2V allows several picks, J165): one table, each current plan with the 2–3 plans that
answer it in rows under it, and one set of reasons. A line with no pick prints the producer's words alone, if any.
The words are `why_for`'s (J57): the line's own, else the deal-wide ones only while no line has its own.
"""

from .. import catalog, formatting
from ..layout import items, tokens
from ..layout import table as tb
from . import exhibit_rows, look

KEEP_CURRENT_WORDS = 'We recommend keeping your current plan.'
BODY_W = tokens.BODY_W


def answers(line):
    """[(plan, the current plan it answers or None)] in the line's order."""
    plans = line['plans']
    if line['groups']:
        return [(plans[pid], plans[current]) for current, ids in line['groups'] for pid in ids]
    currents = [p for p in plans.values() if p['current']]
    only = currents[0] if len(currents) == 1 else None
    return [(plans[pid], only if only and only['id'] != pid else None) for pid in line['order'] if pid in line['picks']]


def _why(line, rationale, colours):
    if not rationale:
        return []
    return [
        look.lead_para('Why we recommend it.', rationale, 'rationale', colours, space_before=12),
        look.note(rationale),
    ]


# The panel's rows (old `composition.highlights`): the line's card stats, then its price rows, in a client's words.
HIGHLIGHT_RATES = {
    'medical': ('rate_ee', 'rate_es', 'rate_ec', 'rate_fam'),
    'dental': ('rate_ee', 'rate_fam'),
    'vision': ('rate_ee', 'rate_fam'),
    'life': ('unit_rate',),
    'disability': ('unit_rate',),
    'stop_loss': (),
    'generic': ('unit_rate',),
}
HIGHLIGHT_LABELS = {
    'deductible_single': 'Deductible (single)',
    'oop_max_single': 'Out-of-pocket max (single)',
    'sl_spec_rate': 'Specific premium PEPM',
    'sl_agg_rate': 'Aggregate premium PEPM',
    'rate_ee': 'Employee only rate',
    'rate_es': 'Employee + spouse rate',
    'rate_ec': 'Employee + child(ren) rate',
    'rate_fam': 'Family rate',
}
MAX_FACTS = 9


def highlights(line):
    """The keys the panel prints for a line: its card stats, then its price rows (only client fields)."""
    keys = list(line['card_stats'] or catalog.card_stats(line['key']))
    allowed = set(catalog.client_keys(line['key']))
    rates = [key for key in HIGHLIGHT_RATES[catalog.field_set(line['key'])] if key not in keys and key in allowed]
    return keys + rates


def _facts(plan, line):
    found = []
    for key in highlights(line):
        value = formatting.value(key, plan['values'].get(key)) if key in plan['values'] else ''
        # In a client's words, as the tables say it (old `presentation_model.client_stats`): "Primary care copay".
        label = HIGHLIGHT_LABELS.get(key) or exhibit_rows.client_label(catalog.stat_label(key))
        found.append((label, value or '—'))
    if plan['monthly'] is not None:
        found.append(('Monthly premium', look.money(plan['monthly'])))
    if plan['annual'] is not None:
        found.append(('Annual premium', look.money(plan['annual'])))
    change = plan['change'] if not plan['current'] else None
    if change:
        pct = f' ({look.pct(change["pct"])})' if change['pct'] is not None else ''
        found.append(('Change from today', f'{look.signed(change["delta"])} a year{pct}'))
    return found[:MAX_FACTS]


def panel(plan, current, line, colours):
    """The WE RECOMMEND panel and the plan's figures beside it, as one block of frames."""
    left_w, label_w = BODY_W * 0.44, BODY_W * 0.3
    value_w = BODY_W - left_w - label_w
    inner = left_w - 36
    silver, white = colours['silver'], tokens.WHITE
    lines = [('WE RECOMMEND', 11, silver, True, 15)]
    if plan['option'] and not plan['current']:
        lines.append((f'Option {plan["option"]}', 13, silver, False, 18))
    lines.append((plan['name'], 24, white, True, 29))
    lines.append((plan['carrier'], 14, white, False, 20))
    if plan['current']:
        lines.append((KEEP_CURRENT_WORDS, 12, silver, False, 17))
    if current is not None and line['several']:
        lines.append((f'In place of {current["carrier"]} {current["name"]}', 12, silver, False, 17))
    words = []
    y = 0.0
    for text, size, ink, bold, leading in lines:
        if not text:
            continue
        item = items.words(20, y, inner, text, size, ink, bold=bold, leading=leading)
        words.append(item)
        y += item['h']
    rows, row_y = [], 0.0
    for name, value in _facts(plan, line) or [('', '')]:
        label = items.words(left_w + 14, 0, label_w - 20, name, 11.5, colours['ink2'], leading=15)
        figure = items.words(left_w + label_w + 14, 0, value_w - 20, value, 12.5, colours['ink'], True, leading=16)
        tall = max(label['h'], figure['h']) + 16
        label['y'] = row_y + (tall - label['h']) / 2
        figure['y'] = row_y + (tall - figure['h']) / 2
        rows += [label, figure, items.line(left_w, row_y + tall, BODY_W, row_y + tall, colours['hairline'])]
        row_y += tall
    height = max(y + 32, row_y)
    for item in words:
        item['y'] += (height - y) / 2
    return look.block([items.rect(0, 0, left_w, height, fill=colours['navy']), *words, *rows], height + 4)


def several(pairs, line, colours, rationale):
    """One table: what each current plan becomes and what it does to the bill."""
    size = 12
    ink = colours['ink']
    rows = [look.heads(['What you have today', 'What we recommend', 'Annual premium', 'Change', '%'], colours, size, 2)]
    last = None
    for plan, current in pairs:
        kept = plan['current']
        today = (
            ''
            if current is not None and current is last
            else f'{current["carrier"]} — {current["name"]}'
            if current
            else ''
        )
        last = current
        change = plan['change'] if not kept else {'delta': 0, 'pct': 0.0}
        cells = [tb.cell(today, size, ink), tb.cell('Keep this plan' if kept else plan['name'], size, ink, True)]
        figures = [
            look.money(plan['annual']),
            look.signed((change or {}).get('delta')),
            look.pct((change or {}).get('pct')),
        ]
        cells += [tb.cell(text, size, ink, align='c') for text in figures]
        rows.append({'kind': 'plain', 'cells': cells})
    table = look.grid(rows, look.shares([0.34, 0.3, 0.14, 0.12, 0.1]), colours, pad=7)
    return [look.title(f'{line["label"]} — our recommendation'), table, *_why(line, rationale, colours)]


def pages(line, colours):
    rationale = line['reasons']
    pairs = answers(line)
    title = f'{line["label"]} — our recommendation'
    if not pairs:
        return [[look.title(title), look.para(rationale, 'rationale', colours)]] if rationale else []
    if len(pairs) > 1:
        return [several(pairs, line, colours, rationale)]
    plan, current = pairs[0]
    return [[look.title(title), panel(plan, current, line, colours), *_why(line, rationale, colours)]]
