"""A line without a tier grid (life, disability, PEPM, stop-loss): one column a plan (plan.md §9.4; J151; old
`presentation_workbook._GenericSheet` and `generic_line_map` at 891f1b3). Rows 1 to 6: the title, the subtitle, the
markers, Carrier, Plan and Status; the picked design and rate rows as values; then the estimated monthly premium as
the figure quotes' math prices (`monthly_premium` for every basis: volume ÷ 1,000, weekly benefit ÷ 10, payroll ÷ 12 ÷
100, lives; OQ103), its annual as a formula, with exactly one current plan the % change from it, and when a plan
carries a first-year credit the credit and the net annual. The figures come from quotes, never from counts here.
"""

import math

from quotes import math as m
from quotes.math import pricing

from .. import cells, design, formulas
from .. import print_plan as pp
from .. import styles as s
from ..model import column_letter
from . import common
from .all_plans import fraction
from .rates import design_value

PLANS_PER_PAGE = 6  # a generic tab prints this many plan columns a page across
WHITE = {'fill': s.FILL_WHITE, 'border': s.THIN, 'align': s.CENTER}


def generic_line_map(plan_ids, current_ids, design_ids, has_credit, cost, notes):
    """Where everything sits (1-based): column A the labels, plan k the column 2+k. Absent rows are None."""
    n = len(plan_ids)
    has_base = len(current_ids) == 1 and n > 1
    has_credit = has_credit and cost
    cols = [{'k': k, 'plan_id': pid, 'col': 2 + k} for k, pid in enumerate(plan_ids)]
    current = None
    if len(current_ids) == 1 and current_ids[0] in plan_ids:
        k = plan_ids.index(current_ids[0])
        current = {'k': k, 'col': cols[k]['col']}
    r, design_rows = 7, {}
    for item_id in design_ids:
        design_rows[item_id] = r
        r += 1
    at = dict.fromkeys(('spacer_design', 'em', 'ea', 'pc', 'cr', 'na', 'notes'))
    if cost:
        if design_ids:
            at['spacer_design'] = r
            r += 1
        at['em'], at['ea'] = r, r + 1
        r += 2
        if has_base:
            at['pc'] = r
            r += 1
        if has_credit:
            r += 1  # spacer
            at['cr'], at['na'] = r, r + 1
            r += 2
    if notes:
        r += 1  # spacer
        at['notes'] = (r, r + notes - 1)
        r += notes
    return {
        'n': n,
        'last_col': 1 + n,
        'last_row': r - 1,
        'cols': cols,
        'current': current,
        'rows': {
            'title': 1,
            'subtitle': 2,
            'marker': 3,
            'carrier': 4,
            'plan': 5,
            'status': 6,
            'design': design_rows,
            **at,
        },
    }


def status_word(plan):
    """Row 6: Current, a priced version's own label, or Proposed."""
    if plan.role == 'current':
        return 'Current'
    return plan.priced or 'Proposed'


def _header(sheet, ctx, line, g):
    cells.band(sheet, 1, g['last_col'], line.label, size=s.TITLE_SIZE, height=24)
    cells.band(sheet, 2, g['last_col'], common.subtitle(ctx.facts), height=18)
    marked = False
    for col, plan in zip(g['cols'], line.presented, strict=True):
        word, look = common.marker(line, plan)
        if word:
            marked = True
            cells.text(sheet, 3, col['col'], word, font=look, align=s.CENTER)
    if marked:
        sheet.heights[3] = 18
    else:
        cells.spacer(sheet, 3)
    shown_rows = (
        (4, 'Carrier', s.FILL_NAVY, s.WHITE_BOLD, [plan.carrier for plan in line.presented]),
        (5, 'Plan', s.FILL_WHITE, s.BOLD, [common.plan_label(plan, line.picked) for plan in line.presented]),
        (6, 'Status', s.FILL_SUBHEAD, s.BOLD, [status_word(plan) for plan in line.presented]),
    )
    for row, word, fill, look, shown in shown_rows:
        cells.text(sheet, row, 1, word, font=look, fill=fill, border=s.THIN, align=s.label_align())
        for col, text in zip(g['cols'], shown, strict=True):
            cells.text(sheet, row, col['col'], text, font=look, fill=fill, border=s.THIN, align=s.CENTER)
        sheet.heights[row] = cells.row_height([(text, 24) for text in shown])


def _premium(sheet, line, g):
    rows = g['rows']
    em, ea, pc = rows['em'], rows['ea'], rows['pc']
    bold = {'font': s.BOLD, 'fill': s.FILL_WHITE, 'border': s.TOTAL, 'align': s.CENTER}
    common.label(sheet, em, 'Estimated Monthly Premium', bold=True, border=s.TOTAL)
    common.label(sheet, ea, 'Estimated Annual Premium', bold=True, border=s.TOTAL)
    for col, plan in zip(g['cols'], line.presented, strict=True):
        letter = column_letter(col['col'])
        cells.number(sheet, em, col['col'], plan.result.get('monthly'), s.MONEY_WHOLE, **bold)
        cells.formula(
            sheet, ea, col['col'], formulas.annual(letter, em), plan.result.get('annual'), s.MONEY_WHOLE, **bold
        )
    sheet.heights[em] = sheet.heights[ea] = s.ROW_H
    if pc is None:
        return
    base = line.presented[g['current']['k']].result.get('annual')
    cv = column_letter(g['current']['col'])
    common.label(sheet, pc, '% Change from Current')
    for col, plan in zip(g['cols'], line.presented, strict=True):
        if col['k'] == g['current']['k']:
            cells.blank(sheet, pc, col['col'], num=s.CHANGE, **WHITE)
            continue
        annual = plan.result.get('annual')
        found = fraction(m.change(annual, base)) if annual is not None and base is not None else None
        letter = column_letter(col['col'])
        cells.formula(
            sheet, pc, col['col'], formulas.pct(letter, ea, cv, ea), '' if found is None else found, s.CHANGE, **WHITE
        )
    sheet.heights[pc] = s.ROW_H


def _credit(sheet, line, g):
    rows = g['rows']
    cr, na, ea = rows['cr'], rows['na'], rows['ea']
    if cr is None:
        return
    cells.spacer(sheet, cr - 1)
    common.label(sheet, cr, 'First-year premium credit')
    common.label(sheet, na, 'Net annual premium (after credit)', bold=True, border=s.TOTAL)
    for col, plan in zip(g['cols'], line.presented, strict=True):
        credit = (plan.result.get('credit') or {}).get('annual')
        cells.number(sheet, cr, col['col'], credit, s.MONEY_WHOLE, **WHITE)
        annual = plan.result.get('annual')
        if annual is None:
            net = None
        elif credit is None:
            net = annual
        else:
            net = pricing.net_after_credit(line.data.by_id[plan.id].credit, plan.result['monthly'], annual, None)
            net = net['net_annual']
        letter = column_letter(col['col'])
        cells.formula(
            sheet,
            na,
            col['col'],
            formulas.net(letter, ea, cr),
            net,
            s.MONEY_WHOLE,
            font=s.BOLD,
            fill=s.FILL_WHITE,
            border=s.TOTAL,
            align=s.CENTER,
        )
    sheet.heights[cr] = sheet.heights[na] = s.ROW_H


def write(sheet, ctx, line):
    plans = line.presented
    items = design.generic_items(line.picked, plans) if common.part(line, 'comparison') else []
    notes = len(common.table_note_rows(line)) + 1
    has_credit = any((plan.result.get('credit') or {}).get('annual') is not None for plan in plans)
    g = generic_line_map(
        [p.id for p in plans], line.current_ids, [i['id'] for i in items], has_credit, common.part(line, 'cost'), notes
    )
    sheet.widths[1] = s.LABEL_W
    for col in g['cols']:
        sheet.widths[col['col']] = s.GENERIC_W
    _header(sheet, ctx, line, g)
    for item in items:
        row = g['rows']['design'][item['id']]
        common.label(sheet, row, item['label'], indent=item['indent'])
        shown = [design_value(sheet, row, col['col'], plan, item) for col, plan in zip(g['cols'], plans, strict=True)]
        sheet.heights[row] = cells.row_height([(item['label'], 42)] + [(text, 28) for text in shown])
    if g['rows']['spacer_design']:
        cells.spacer(sheet, g['rows']['spacer_design'])
    if g['rows']['em'] is not None:
        _premium(sheet, line, g)
        _credit(sheet, line, g)
    wide = len(g['cols']) > PLANS_PER_PAGE
    if g['rows']['notes']:
        found = [(text, s.BODY) for text in common.table_note_rows(line)] + [(common.DISCLAIMER, s.BOLD_ITALIC)]
        common.notes(
            sheet,
            g['rows']['notes'][0],
            1 if wide else g['last_col'],
            found,
            common.note_chars(0 if wide else len(g['cols'])),
        )
    sheet.freeze = (7, 2)
    sheet.zoom = s.ZOOM
    pp.fitted(
        sheet,
        g['last_col'],
        g['last_row'],
        draft=ctx.draft,
        fit_wide=math.ceil(len(g['cols']) / PLANS_PER_PAGE) if wide else 1,
        title_cols=(1, 1) if wide else None,
        title_rows=pp.TITLE_ROWS,
        best_fit=True,
    )
