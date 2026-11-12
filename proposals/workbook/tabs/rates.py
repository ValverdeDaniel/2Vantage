"""A composite line's rates tab (plan.md §9.4; J147; old `presentation_workbook._TierSheet` and `tier_line_map` at
891f1b3): up to 16 plans, two columns each (its tier counts, then its rates and values), column A the labels. Rows 1
to 6: the title band, the subtitle, the SOLD / RECOMMENDED markers, Carrier, Plan and Package; the design rows from
row 7; the premium block (`rates_cost`); the notes. Frozen at B7; a page break before each carrier.

Each plan's counts are the enrollment quotes' math priced it with: with exactly one current plan its counts are
inputs and every plan that carries the same people links to them (one edit flows through); any other plan's counts
are its own inputs. So every stored total is quotes' figure for the plan (the key, three ways).
"""

from quotes.math import TIERS

from .. import cells, design, values
from .. import print_plan as pp
from .. import styles as s
from . import common, rates_cost


def tier_line_map(spec):
    """Where everything on a rates tab sits (1-based). `spec`: {'plan_ids', 'current_ids', 'design' (item ids),
    'contrib' (tiers with a contribution row), 'has_g', 'has_credit', 'cost', 'notes'}. Package, change and credit rows
    exist only with exactly one current plan and another plan (`has_base`). Absent rows are None."""
    plan_ids = list(spec.get('plan_ids') or [])
    current_ids = list(spec.get('current_ids') or [])
    design_ids = list(spec.get('design') or [])
    wanted = set(spec.get('contrib') or [])
    cost, n = bool(spec.get('cost')), len(plan_ids)
    has_base = len(current_ids) == 1 and n > 1
    has_g = bool(spec.get('has_g')) and cost
    has_credit = bool(spec.get('has_credit')) and has_base and cost
    cols = [{'k': k, 'plan_id': pid, 'count': 2 + 2 * k, 'rate': 3 + 2 * k} for k, pid in enumerate(plan_ids)]
    current = None
    if len(current_ids) == 1 and current_ids[0] in plan_ids:
        k = plan_ids.index(current_ids[0])
        current = {'k': k, 'count': cols[k]['count'], 'rate': cols[k]['rate']}
    r, design_rows = 7, {}
    for item_id in design_ids:
        design_rows[item_id] = r
        r += 1
    names = ('spacer_design', 'band', 'sub', 'tiers', 'g', 'tm', 'ta', 'dp', 'pp', 'pm', 'pa', 'dk', 'pk', 'cr')
    at = dict.fromkeys((*names, 'na', 'nd', 'np', 'notes'))
    contrib = {}
    if cost:
        if design_ids:
            at['spacer_design'] = r
            r += 1
        at['band'], at['sub'] = r, r + 1
        at['tiers'] = (r + 2, r + 3, r + 4, r + 5)
        r += 6
        for tier in TIERS:
            if tier in wanted:
                contrib[tier] = r
                r += 1
        if has_g:
            at['g'] = r
            r += 1
        r += 1  # spacer
        at['tm'] = r
        r += 2  # the total, then a spacer
        at['ta'] = r
        r += 1
        if has_base:
            at['dp'], at['pp'] = r, r + 1
            r += 3  # the two change rows, then a spacer
            at['pm'], at['pa'], at['dk'], at['pk'] = r, r + 1, r + 2, r + 3
            r += 4
            if has_credit:
                r += 1  # spacer
                at['cr'], at['na'], at['nd'], at['np'] = r, r + 1, r + 2, r + 3
                r += 4
    notes = int(spec.get('notes') or 0)
    if notes:
        r += 1  # spacer
        at['notes'] = (r, r + notes - 1)
        r += notes
    return {
        'n': n,
        'last_col': 1 + 2 * n,
        'last_row': r - 1,
        'cols': cols,
        'current': current,
        'flags': {'has_base': has_base, 'has_g': has_g, 'has_credit': has_credit, 'cost': cost},
        'rows': {
            'title': 1,
            'subtitle': 2,
            'marker': 3,
            'carrier': 4,
            'plan': 5,
            'package': 6,
            'design': design_rows,
            'contrib': contrib,
            **at,
        },
    }


def spec(line):
    plans = line.presented
    items = design.items(line.field_set, line.picked, plans) if common.part(line, 'comparison') else []
    contrib = [
        tier
        for tier, key in zip(TIERS, rates_cost.CONTRIB_KEYS, strict=True)
        if key in line.picked and any(values.number(plan.values.get(key)) is not None for plan in plans)
    ]
    return {
        'plan_ids': [plan.id for plan in plans],
        'current_ids': line.current_ids,
        'design': [item['id'] for item in items],
        'contrib': contrib,
        'has_g': any(values.number(plan.values.get('group_premium_monthly')) is not None for plan in plans),
        'has_credit': any((plan.result.get('credit') or {}).get('annual') is not None for plan in plans),
        'cost': common.part(line, 'cost'),
        'notes': len(common.table_note_rows(line)) + 2,
    }, items


def _header(sheet, ctx, line, geometry):
    last = geometry['last_col']
    cells.band(sheet, 1, last, line.label, size=s.TITLE_SIZE, height=24)
    cells.band(sheet, 2, last, common.subtitle(ctx.facts), height=18)
    marked = False
    for col, plan in zip(geometry['cols'], line.presented, strict=True):
        word, look = common.marker(line, plan)
        if word:
            marked = True
            cells.text(sheet, 3, col['count'], word, font=look, align=s.CENTER)
            cells.merge_pair(sheet, 3, col['count'], col['rate'])
    if marked:
        sheet.heights[3] = 18
    else:
        cells.spacer(sheet, 3)
    carriers = [plan.carrier for plan in line.presented]
    names = [common.plan_label(plan, line.picked) for plan in line.presented]
    labels = [line.labels[plan.id] for plan in line.presented]
    for row, word, fill, look, shown in (
        (4, 'Carrier', s.FILL_NAVY, s.WHITE_BOLD, carriers),
        (5, 'Plan', s.FILL_WHITE, s.BOLD, names),
        (6, 'Package', s.FILL_SUBHEAD, s.BOLD, labels),
    ):
        cells.text(sheet, row, 1, word, font=look, fill=fill, border=s.THIN, align=s.label_align())
        for col, text in zip(geometry['cols'], shown, strict=True):
            cells.text(sheet, row, col['count'], text, font=look, fill=fill, border=s.THIN, align=s.CENTER)
            cells.merge_pair(sheet, row, col['count'], col['rate'])
        sheet.heights[row] = cells.row_height([(text, 24) for text in shown])


def design_value(sheet, row, column, plan, item):
    """One design value written into its cell; the text it shows ('' for a number or an empty cell)."""
    look = {'fill': s.FILL_WHITE, 'border': s.THIN, 'align': s.CENTER}
    if item['pair'] or item.get('inout'):
        shown = design.text(item, plan)
        cells.text(sheet, row, column, shown, **look)
        return shown
    key = item['keys'][0]
    kind, value, num = values.design_cell(key, plan.values.get(key))
    if kind == 'number':
        cells.number(sheet, row, column, value, num, **look)
        return ''
    if kind == 'text':
        cells.text(sheet, row, column, value, **look)
        return value
    cells.blank(sheet, row, column, **look)
    return ''


def _design(sheet, line, geometry, items):
    rows = geometry['rows']
    for item in items:
        row = rows['design'][item['id']]
        if item['kind'] == 'band':
            cells.band(sheet, row, geometry['last_col'], item['label'])
            continue
        common.label(sheet, row, item['label'], indent=item['indent'])
        shown = []
        for col, plan in zip(geometry['cols'], line.presented, strict=True):
            shown.append(design_value(sheet, row, col['count'], plan, item))
            cells.merge_pair(sheet, row, col['count'], col['rate'])
        sheet.heights[row] = cells.row_height([(item['label'], 42)] + [(text, 28) for text in shown])
    if rows['spacer_design']:
        cells.spacer(sheet, rows['spacer_design'])


def _notes(sheet, line, geometry):
    if geometry['rows']['notes'] is None:
        return
    currents = len(line.current_ids)
    found = [(text, s.BODY) for text in common.table_note_rows(line)]
    found += [(common.DISCLAIMER, s.BOLD_ITALIC), (rates_cost.enrollment_note(line, geometry), s.BODY)]
    common.notes(sheet, geometry['rows']['notes'][0], 1 + 2 * currents, found, common.note_chars(currents))


def _print(sheet, line, geometry, draft):
    lead = 0
    for plan in line.presented:
        if line.data.root(line.data.by_id[plan.id]).role != 'current':
            break
        lead += 1
    groups, run = [], None
    for plan in line.presented[lead:]:
        if groups and run == plan.identity:
            groups[-1] += 1
        else:
            groups.append(1)
            run = plan.identity
    plan = pp.print_plan(
        lead, len(line.current_ids), groups, height_pt=cells.sheet_height_pt(sheet, geometry['last_row'])
    )
    pp.with_breaks(sheet, geometry['last_col'], geometry['last_row'], plan, draft=draft)


def write(sheet, ctx, line):
    """Draw the tab; return its geometry (with `counts`, the single current plan's counts as written, for Compare)."""
    found, items = spec(line)
    geometry = tier_line_map(found)
    sheet.widths[1] = s.LABEL_W
    for col in geometry['cols']:
        sheet.widths[col['count']] = s.COUNT_W
        sheet.widths[col['rate']] = s.RATE_W
    _header(sheet, ctx, line, geometry)
    if geometry['rows']['design']:
        _design(sheet, line, geometry, items)
    geometry['counts'] = rates_cost.write(sheet, line, geometry)
    _notes(sheet, line, geometry)
    sheet.freeze = (7, 2)
    sheet.zoom = s.ZOOM
    _print(sheet, line, geometry, ctx.draft)
    return geometry
