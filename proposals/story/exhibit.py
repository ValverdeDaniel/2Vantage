"""One plan set on one page: the format's heart (plan.md §9.5; J131, J133, J140; old Vantage 891f1b3
`proposal_presentation._cost_entries`, `_plan_cell`, `_build_exhibit`, `_exhibit`, `_page_notes`, `_exhibit_page`).
Pure.

Benefits, who enrolls at what rate, what each plan comes to and how far it moved, on one page down to the 8 pt floor
(Daniel, 2026-11-02). Each column is headed by its carrier and the client's name for the plan: CURRENT over a current
plan, "Option n ·" over an option, a priced version's label after its carrier, RECOMMENDED under a pick. The cost rows
are quotes' figures (rule 5): a row with nothing in it is not printed (why a figure is missing is the builder's to
say). Only a renewal set's columns are ever added up (`set_totals`): a page of options is a choice, and a sum across
a choice means nothing. The table fits by `layout.fit.exhibit`: it fits, its notes follow, or it runs on with its
header repeated, "(continued)".
"""

from quotes import math as m

from ..layout import fit, tokens
from ..layout import table as tb
from ..layout import text as words
from . import exhibit_rows, look

CREDIT_EXCEEDS = 'The credit is larger than the annual premium.'


def _base(plan, line, page_plans, key='monthly'):
    """The premium (`key`: monthly or annual) of what `plan` is compared with: its current plans', else the page's
    one current plan."""
    bases = plan['bases'] or [p['id'] for p in page_plans if p['current']][:1]
    found = [line['plans'][pid][key] for pid in bases if pid in line['plans']]
    return m.add(found) if found and len(found) == len(bases) else None


def cost_entries(page_plans, line, offers=None):
    """The cost rows: what each plan comes to and how far it moved. A page with no current column opens with what
    each plan is compared with, so its change is never against a figure the page does not show."""
    today, monthly, annual, delta, pct, credit, net = {}, {}, {}, {}, {}, {}, {}
    for plan in page_plans:
        key = plan['id']
        offer = (offers or {}).get(key)
        if offer is not None:
            monthly[key], annual[key] = offer['monthly'], offer['annual']
            base = _base(plan, line, page_plans)
            if offer['annual'] is not None and base and plan['change'] is not None:
                change = m.change(offer['annual'], _base(plan, line, page_plans, 'annual'))
                today[key], delta[key], pct[key] = base, change['delta'], change['pct']
            continue
        monthly[key], annual[key] = plan['monthly'], plan['annual']
        if plan['change'] is not None:
            delta[key], pct[key] = plan['change']['delta'], plan['change']['pct']
            today[key] = _base(plan, line, page_plans)
        found = plan['credit'] or {}
        if found.get('annual'):
            credit[key], net[key] = found['annual'], found.get('net_annual')
    ids = [p['id'] for p in page_plans]

    def row(label, values, shown):
        if not any(values.get(pid) is not None for pid in ids):
            return []
        cells = [label] + [shown(values[pid]) if values.get(pid) is not None else '—' for pid in ids]
        return [('cost', None, cells)]

    opening = [] if any(p['current'] for p in page_plans) else row('Monthly premium today', today, look.money)
    return (
        opening
        + row('Monthly premium', monthly, look.money)
        + row('Annual premium', annual, look.money)
        + row('Annual change', delta, look.signed)
        + row('% change', pct, look.pct)
        + row('First-year premium credit', credit, lambda value: f'− {look.money(value)}')
        + row('Net annual premium (after credit)', net, look.money)
    )


def set_totals(plans, line, offers=None):
    """What a renewal set comes to, added across its columns and against the current plans they renew, or None when
    any figure is missing or any column's own change refused (the same people on every plan): half a sum is not a
    total."""
    monthly, annual, today = [], [], []
    for plan in plans:
        if plan['change'] is None:
            return None
        found = (offers or {}).get(plan['id']) or plan
        monthly.append(found['monthly'])
        annual.append(found['annual'])
        today.append(_base(plan, line, plans, 'annual'))
    monthly, annual, today = m.add(monthly), m.add(annual), m.add(today)
    if monthly is None or annual is None or today is None:
        return None
    return {'monthly': monthly, 'annual': annual, 'today_annual': today, **m.change(annual, today)}


def total_entries(totals):
    return [
        ('total', None, ['Total annual premium today', look.money(totals['today_annual'])]),
        ('total', None, ['Total monthly premium', look.money(totals['monthly'])]),
        ('total', None, ['Total annual premium', look.money(totals['annual'])]),
        ('total', None, ['Change in annual premium', look.signed(totals['delta'])]),
        ('total', None, ['% change', look.pct(totals['pct'])]),
    ]


def column_name(plan):
    """A column's plan name without its priced version's own suffix, where the page says what the column is
    ("HMO 1000 — 5% concession" on a negotiated renewal's page reads "HMO 1000")."""
    suffix = f' — {plan["priced_label"]}' if plan['priced_label'] else ''
    name = plan['name']
    return name[: -len(suffix)] if suffix and name.endswith(suffix) else name


def plan_title(plan):
    """A plan column's carrier line: CURRENT first on a current plan, its number first on an option, a priced version's
    own label after it (old `proposal_pdf._plan_title`)."""
    prefix = 'CURRENT — ' if plan['current'] else (f'Option {plan["option"]} · ' if plan['option'] else '')
    suffix = f' ({plan["priced_label"]})' if plan['priced_label'] else ''
    return f'{prefix}{plan["carrier"]}{suffix}'


def heading_runs(plan, size, colours, recommended=False, plain=False):
    """A plan column's heading. `plain` on a renewal set's page, whose title says what its offers are: TODAY over the
    current plan and RENEWAL over its offer, because the pair share one name."""
    head = max(size, 9)
    small = max(size - 0.5, 8)
    white = '#ffffff'
    if plain:
        top = 'TODAY' if plan['current'] else 'RENEWAL'
        runs = [words.run(f'{top}\n', small, white, True), words.run(plan['carrier'], head, white, True)]
    else:
        runs = [words.run(plan_title(plan), head, white, True)]
    runs.append(words.run(f'\n{column_name(plan) if plain else plan["name"]}', small, white))
    if recommended:
        runs.append(words.run('\nRECOMMENDED', small, white, True))
    return runs


def build(entries, page_plans, picks, colours, size, pad, offers=None, plain=False):
    """The table at one type size and padding."""
    count = len(page_plans)
    width = min(tokens.MAX_COL, (tokens.BODY_W - tokens.LABEL_W) / max(1, count))
    widths = [tokens.LABEL_W] + [width] * count
    options = [p for p in page_plans if not p['current']]
    all_picked = len(options) > 1 and all(p['id'] in picks for p in options)
    badge = not offers and not all_picked
    rows = [{'kind': 'head', 'cells': [tb.cell('', size, '#ffffff')]}]
    # The plan headings lead at 1.25 × their type (old `_plan_cell`).
    lead = round(max(size, 9) * tokens.HEAD_LEADING, 2)
    rows[0]['cells'] += [
        tb.rich(heading_runs(p, size, colours, badge and p['id'] in picks, plain), align='c', leading=lead)
        for p in page_plans
    ]
    ink, soft = colours['ink'], colours['ink2']
    first_cost = True
    for kind, item, cells in entries:
        if kind == 'band':
            band = [tb.cell(cells[0], size, ink, True, span=count + 1)]
            rows.append({'kind': 'band', 'cells': band, 'keep_with_next': True, 'blanks': True})
        elif kind == 'total':
            cells_ = [tb.cell(cells[0], size, ink, True), tb.cell(cells[1], size, ink, True, 'c', span=count)]
            rows.append({'kind': 'total', 'cells': cells_, 'fill': colours['blue_bg'], 'blanks': count > 1})
        elif kind == 'cost':
            row = {'kind': 'cost', 'cells': [tb.cell(cells[0], size, ink, True)]}
            row['cells'] += [tb.cell(text, size, ink, True, 'c') for text in cells[1:]]
            if first_cost:
                row['rule_above'], first_cost = colours['navy'], False
            rows.append(row)
        else:
            indent = '   ' if item.get('indent') == 2 else ''
            row = {'kind': 'row', 'cells': [tb.cell(indent + cells[0], size, soft)]}
            row['cells'] += [tb.cell(text, size, ink, align='c') for text in cells[1:]]
            rows.append(row)
    if not offers and any(p['sbc'] for p in page_plans):
        sbc = [tb.cell('Summary of Benefits', size, soft)]
        for plan in page_plans:
            link = plan['sbc']
            sbc.append(
                tb.cell(
                    'See SBC' if link else '—', size, colours['blue'] if link else ink, align='c', link=link or None
                )
            )
        rows.append({'kind': 'plain', 'cells': sbc})
    current = [n + 1 for n, p in enumerate(page_plans) if p['current']]
    picked = [] if offers else [n + 1 for n, p in enumerate(page_plans) if p['id'] in picks]
    return look.grid(rows, widths, colours, pad=pad, current=current, picked=picked, h_align='CENTER')


def page_notes(line, page_plans, colours):
    """What sits under a page's table: the producer's own note first (it explains the table's marks), whose
    enrollment priced it, and a credit larger than its year."""
    notes = []
    if line['table_note'].strip():
        notes.append(line['table_note'].strip())
    if line['basis'] and any(p['monthly'] is not None for p in page_plans):
        notes.append(f'Enrollment basis: {line["basis"]}')
    if any((p['credit'] or {}).get('reason') == 'credit_exceeds_year' for p in page_plans):
        notes.append(CREDIT_EXCEEDS)
    return [look.para(text, 'note', colours) for text in notes]


def page(
    title, line, page_plans, colours, *, picks=(), offers=None, totals=None, with_cost=True, speak=None, plain=False
):
    """One plan set's page as a list of flowables, or [] when the set has nothing to say."""
    items_ = exhibit_rows.items(line)
    rows, notes = exhibit_rows.entries(items_, page_plans, offers=offers, with_cost=with_cost)
    if with_cost:
        rows += cost_entries(page_plans, line, offers)
    if totals:
        rows += total_entries(totals)
    if not rows:
        return []
    below = page_notes(line, page_plans, colours)
    note_flowables = [look.para(text, 'note', colours) for text in notes]

    def at(size, pad):
        return build(rows, page_plans, set(picks), colours, size, pad, offers, plain)

    table, fitted = fit.exhibit(at, fit.height_under(note_flowables + below), notes=len(note_flowables))
    chunk = [look.title(title, line=line['key'], fit=fitted), table, *note_flowables, *below]
    if speak:
        chunk.append(look.note(speak))
    return chunk
