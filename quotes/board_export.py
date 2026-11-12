"""⤓ Export: the Advisor board as Excel, equal to the screen (plan.md §9.14; F93, J167; O.6 #34: one exporter).

The screen says WHAT is on it — the line, the plans in the order drawn, the column keys in theirs and the orientation
— and every figure is taken again from the comparison payload the board drew (`selectors.comparison`), so the file
can never quote a number the board did not (the old AdvisorExportView's rule). Three rules hold it honest, as in the
old app: every current plan rides along as the baseline even when not listed, in its place first; a subset says it
is one in its third line; unknown plan ids and column keys are dropped, never refused, as the board drops a column
its line does not have. Screen-only columns (☐, ★ and Plan, which are pinned as their own columns, the sort-only
keys and the Flags chip) do not travel.

Text stays text (§3.8): written through `documents.xlsx_safe` with XlsxWriter, so a plan named "=1+1" prints as
typed. Internal and staff-only; a file that prints `sl_lasers` is logged as a download (the view, J98).
"""

import io

from deals import clock, lines

from . import board_presets, fields, selectors
from . import values as cleaning

SCREEN_ONLY = {'select', 'star', 'carrier', 'flags', 'closest', 'proposal', 'editact'}
PINNED = [('★', '_star'), ('Carrier', '_carrier'), ('Plan', '_plan'), ('Status', '_status')]
NUMERIC = {'amount', 'percent', 'rate', 'rate4', 'number'}
FORMATS = {
    'money': '"$"#,##0',
    'amount': '"$"#,##0',
    'rate': '"$"#,##0.00',
    'rate4': '"$"#,##0.00##',
    'percent': '0"%"',
    'delta': '+0.0"%";-0.0"%";0.0"%"',
}
NAVY = '#173A63'
TOP = 4  # the header row (0-based): the title, the date line and the scope line sit above it


def columns(line, keys=None):
    """[(label, key, kind)] for the keys given (the board's), or the line's Primary preset; kind is the number format
    ('money', 'delta', a field type, or 'text')."""
    derived = {d['key']: d['label'] for d in board_presets.DERIVED}
    own = set(fields.keys_for(line))
    wanted = keys if keys else board_presets.columns(board_presets.DEFAULT_PRESET, line)
    out = []
    for key in dict.fromkeys(wanted):
        if key in SCREEN_ONLY:
            continue
        if key in derived:
            kind = {'total': 'money', 'delta': 'delta'}.get(key, 'text')
            out.append((derived[key], key, kind))
        elif key in own:
            out.append((fields.BY_KEY[key]['label'], key, fields.BY_KEY[key]['type']))
    return out


def chosen(payload, plan_ids=None):
    """The plans in the order drawn: the ids given that are on the line, the current plans first when missing."""
    plans = payload['plans']
    if not plan_ids:
        return plans
    by_id = {plan['id']: plan for plan in plans}
    picked = [by_id[pid] for pid in dict.fromkeys(plan_ids) if pid in by_id]
    have = {plan['id'] for plan in picked}
    return [plan for plan in plans if plan['role'] == 'current' and plan['id'] not in have] + picked


def _status(plan, currents, superseded):
    """The Plan cell's chips as words: CURRENT k, SOLD, a priced version's label, superseded (F62)."""
    chips = []
    if plan['role'] == 'current':
        slot = currents.index(plan['id']) + 1
        chips.append(f'CURRENT {slot}' if len(currents) > 1 else 'CURRENT')
    if plan['sold']:
        chips.append('SOLD')
    derived = plan.get('derived') or {}
    if plan.get('derived_from') and derived.get('kind') not in (None, 'duplicate'):
        chips.append(str(derived.get('label') or derived['kind']).upper())
    if plan['id'] in superseded:
        chips.append('superseded')
    return ' · '.join(chips)


def value(plan, key, kind):
    """One cell as the board shows it: the server's figures for derived columns, a field's value typed by its kind."""
    if key == 'total':
        return (plan.get('premium') or {}).get('monthly')
    if key == 'delta':
        if plan['role'] == 'current':
            return 'baseline'
        return (plan.get('change') or {}).get('pct')
    if key == 'network_type':
        parts = [str(plan['values'].get(k) or '').strip() for k in ('network', 'plan_type')]
        return ' · '.join(p for p in parts if p) or None
    raw = plan['values'].get(key)
    if raw in (None, ''):
        return None
    if kind in NUMERIC:
        number = cleaning.as_float(raw)
        return number if number is not None else str(raw)
    return str(raw)


def table(deal, line, plan_ids=None, column_keys=None):
    """(payload, plans, header [(label, key, kind)], rows [[value per header]]) — what the file prints."""
    payload = selectors.comparison(deal, line)
    plans = chosen(payload, plan_ids)
    cols = columns(line, column_keys)
    currents = [plan['id'] for plan in payload['plans'] if plan['role'] == 'current']
    superseded = {
        plan['derived_from']
        for plan in payload['plans']
        if plan.get('derived_from') and (plan.get('derived') or {}).get('kind') not in (None, 'duplicate')
    }
    header = [(label, key, 'text') for label, key in PINNED] + cols
    rows = []
    for plan in plans:
        pinned = ['★' if plan['starred'] else '', plan['carrier'], plan['name'], _status(plan, currents, superseded)]
        rows.append(pinned + [value(plan, key, kind) for _, key, kind in cols])
    return payload, plans, header, rows


def _scope(payload, plans):
    quoted = sum(1 for plan in payload['plans'] if plan['role'] != 'current')
    shown = sum(1 for plan in plans if plan['role'] != 'current')
    currents = sum(1 for plan in plans if plan['role'] == 'current')
    if shown < quoted:
        scope = f'{shown} of {quoted} quoted plans — filtered on the advisor board'
    else:
        scope = f'all {quoted} quoted plans on this line'
    if currents > 1:
        scope += f', {currents} current plans included as baselines'
    elif currents == 1:
        scope += ', current plan included as the baseline'
    return scope


def export(deal, line, plan_ids=None, column_keys=None, transposed=False):
    """(xlsx bytes, the column keys printed)."""
    from documents import xlsx_safe

    payload, plans, header, rows = table(deal, line, plan_ids, column_keys)
    buffer = io.BytesIO()
    book = xlsx_safe.workbook(buffer, {'in_memory': True})
    sheet = book.add_worksheet(_sheet_name(lines.label(line)))
    title = book.add_format({'bold': True, 'font_size': 14, 'font_color': NAVY})
    small = book.add_format({'italic': True, 'font_size': 9})
    head = book.add_format(
        {'bold': True, 'font_color': '#FFFFFF', 'bg_color': NAVY, 'text_wrap': True, 'valign': 'top'}
    )
    plain = book.add_format({'border': 1, 'border_color': '#D9DEE7'})
    formats = {
        kind: book.add_format({'border': 1, 'border_color': '#D9DEE7', 'num_format': fmt})
        for kind, fmt in FORMATS.items()
    }

    xlsx_safe.write_text(sheet, 0, 0, f'{deal.client.name} — {lines.label(line)} Quote Comparison', title)
    if deal.effective_date:
        xlsx_safe.write_text(sheet, 1, 0, f'Effective date: {deal.effective_date:%m/%d/%Y}')
    stamp = f'Quote advisor export · {_scope(payload, plans)} · {clock.today():%B %d, %Y}'
    xlsx_safe.write_text(sheet, 2, 0, stamp, small)

    def put(row, col, item, kind):
        fmt = formats.get(kind, plain) if isinstance(item, int | float) and not isinstance(item, bool) else plain
        xlsx_safe.write(sheet, row, col, item, fmt)

    kinds = [kind for _, _, kind in header]
    if transposed:
        for r, (label, _, _) in enumerate(header):
            xlsx_safe.write_text(sheet, TOP + r, 0, label, head)
        for c, items in enumerate(rows):
            for r, item in enumerate(items):
                put(TOP + r, c + 1, item, kinds[r])
        sheet.set_column(0, 0, 26)
        sheet.set_column(1, max(len(rows), 1), 22)
        sheet.freeze_panes(TOP, 1)
    else:
        for c, (label, _, _) in enumerate(header):
            xlsx_safe.write_text(sheet, TOP, c, label, head)
        for r, items in enumerate(rows):
            for c, item in enumerate(items):
                put(TOP + 1 + r, c, item, kinds[c])
        for c, width in enumerate([5, 22, 30, 24]):
            sheet.set_column(c, c, width)
        sheet.set_column(len(PINNED), max(len(header) - 1, len(PINNED)), 18)
        sheet.freeze_panes(TOP + 1, len(PINNED))
    book.close()
    return buffer.getvalue(), [key for _, key, _ in header[len(PINNED) :]]


def _sheet_name(label):
    cleaned = ''.join('-' if ch in '[]:*?/\\' else ch for ch in f'{label} Quotes')
    return cleaned[:31]
