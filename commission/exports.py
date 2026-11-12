"""The Book and By person workbooks (plan.md §9.15; H52, H68; 891f1b3 `commissions/workbooks.py`). Each takes the same
rows the screen shows, already filtered and scoped to the viewer's tier, so a file never widens what its reader may
see. Every text cell goes through `documents.xlsx_safe` (the injection guard); money is a number with a format.

- `book(answer, viewer)`: the Book sheet with the old 16 columns (Received and Open gap stay blank while the ledger
  waits, OQ6) and a Totals sheet by client, carrier and line.
- `by_person(people, records_of)`: the pivot, then a sheet per person with the records they hold a share of and their
  own share on each.
"""

import io
from decimal import Decimal

from deals import clock
from documents import xlsx_safe

NAVY = '#173A63'
BOOK_HEADERS = [
    'Client', 'LOB', 'Line', 'Carrier', 'Plan', 'Effective', 'Plan yr', 'Premium / yr', 'Rate', 'Expected / yr',
    'Received', 'Open gap', 'House share', 'Status', 'Who gets what', 'Holes',
]  # fmt: skip
BOOK_WIDTHS = [28, 6, 18, 18, 30, 11, 8, 12, 12, 12, 12, 10, 12, 11, 60, 14]
MONEY = '#,##0.00'


def _formats(workbook):
    return {
        'title': workbook.add_format({'bold': True, 'font_size': 14, 'font_color': NAVY}),
        'sub': workbook.add_format({'font_size': 9, 'font_color': '#5B6573'}),
        'head': workbook.add_format({'bold': True, 'font_size': 9, 'font_color': '#FFFFFF', 'bg_color': NAVY}),
        'cell': workbook.add_format({'font_size': 9}),
        'money': workbook.add_format({'font_size': 9, 'num_format': MONEY}),
        'pct': workbook.add_format({'font_size': 9, 'num_format': '0.0%'}),
    }


def _head(sheet, formats, title, subtitle, agency):
    xlsx_safe.write_text(sheet, 0, 0, title, formats['title'])
    xlsx_safe.write_text(sheet, 1, 0, subtitle or f'Exported {clock.today().isoformat()} - {agency}', formats['sub'])


def _table(sheet, formats, top, headers, rows, money_cols=(), widths=None, pct_cols=()):
    for col, text in enumerate(headers):
        xlsx_safe.write_text(sheet, top, col, text, formats['head'])
    for col, width in enumerate(widths or []):
        sheet.set_column(col, col, width)
    for r, row in enumerate(rows, start=top + 1):
        for col, value in enumerate(row):
            fmt = formats['money'] if col in money_cols else formats['pct'] if col in pct_cols else formats['cell']
            xlsx_safe.write(sheet, r, col, value, fmt)
    return top + len(rows) + 2


def who_gets_what(row):
    """The shares as one printable cell: "Primary Dana 24.0% ($7,173) · House 60.0% ($17,932)"."""
    bits = []
    for share in row['shares']:
        name = '' if share['role'] == 'house' else f' {share["name"]}'
        money = f' (${Decimal(str(share["amount"])):,.0f})' if share['amount'] is not None else ''
        bits.append(f'{share["role_label"]}{name} {share["pct_label"]}{money}')
    return ' · '.join(bits)


def _book_row(row):
    year = row['year_number'] or ('renewal' if row['is_renewal'] else '')
    return [
        row['client_name'], 'EB', row['line_label'], row['carrier'], row['plan_label'], row['effective_date'] or '',
        year, row['premium_annual'], row['rate_label'] or 'not set', row['expected'], None, None, row['house_share'],
        row['status_label'], who_gets_what(row), ', '.join(row['holes']),
    ]  # fmt: skip


def _sums(rows, key):
    out = {}
    for row in rows:
        entry = out.setdefault(row[key], {'records': 0, 'expected': Decimal(0), 'premium': Decimal(0)})
        entry['records'] += 1
        entry['expected'] += Decimal(str(row['expected'] or 0))
        entry['premium'] += Decimal(str(row['premium_annual'] or 0))
    return sorted(out.items(), key=lambda item: -item[1]['expected'])


def book(answer, agency):
    """The Book workbook's bytes for a `book.book` answer (its rows and totals)."""
    buffer = io.BytesIO()
    workbook = xlsx_safe.workbook(buffer, {'in_memory': True})
    formats = _formats(workbook)
    sheet = workbook.add_worksheet('Book')
    _head(sheet, formats, 'Commission book', '', agency)
    rows = answer['rows']
    _table(sheet, formats, 3, BOOK_HEADERS, [_book_row(row) for row in rows], (7, 9, 10, 11, 12), BOOK_WIDTHS)
    sheet.freeze_panes(4, 0)
    totals = workbook.add_worksheet('Totals')
    expected = answer['totals'].get('expected')
    _head(totals, formats, 'Totals', f'{len(rows)} records - expected ${Decimal(str(expected or 0)):,.0f}/yr', agency)
    top = 3
    by_client = [[name, 'EB', e['records'], e['expected']] for name, e in _sums(rows, 'client_name')]
    top = _table(totals, formats, top, ['Client', 'LOB', 'Records', 'Expected / yr'], by_client, (3,), [28, 6, 9, 14])
    by_carrier = [[name or '—', e['records'], e['premium'], e['expected']] for name, e in _sums(rows, 'carrier')]
    top = _table(totals, formats, top, ['Carrier', 'Records', 'Premium / yr', 'Expected / yr'], by_carrier, (2, 3))
    by_line = [[name, e['records'], e['expected']] for name, e in _sums(rows, 'line_label')]
    _table(totals, formats, top, ['Line', 'Records', 'Expected / yr'], by_line, (2,))
    workbook.close()
    return buffer.getvalue()


def _sheet_name(name, used):
    base = ''.join('-' if ch in '[]:*?/\\' else ch for ch in name)[:28] or 'Person'
    title, n = base, 2
    while title.lower() in used:
        title, n = f'{base[:25]} ({n})', n + 1
    used.add(title.lower())
    return title


def by_person(people, records_of, agency):
    """The By person workbook's bytes: `people` is `book.people`'s answer, `records_of(key)` a person's rows."""
    buffer = io.BytesIO()
    workbook = xlsx_safe.workbook(buffer, {'in_memory': True})
    formats = _formats(workbook)
    sheet = workbook.add_worksheet('By person')
    _head(sheet, formats, 'Commission book - by person', '', agency)
    rows = [
        [p['name'], p['kind'], p['records'], p['expected'], p['share_of_book'] / 100 if p['share_of_book'] else None]
        for p in people['rows']
    ]
    _table(sheet, formats, 3, ['Person', 'Kind', 'Records', 'Expected / yr', 'Share of book'], rows, (3,),
           [28, 16, 9, 14, 13], (4,))  # fmt: skip
    used = {'by person'}
    for person in people['rows']:
        theirs = records_of(person['key'])
        if not theirs:
            continue
        page = workbook.add_worksheet(_sheet_name(person['name'], used))
        subtitle = f'{len(theirs)} records - expected ${Decimal(str(person["expected"] or 0)):,.0f}/yr'
        _head(page, formats, person['name'], subtitle, agency)
        lines = [
            [r['client_name'], r['line_label'], r['carrier'], r['effective_date'] or '', r['expected'],
             r['mine']['pct_label'], r['mine']['amount']]
            for r in theirs
        ]  # fmt: skip
        headers = ['Client', 'Line', 'Carrier', 'Effective', 'Record expected', 'Their share', 'Their $']
        _table(page, formats, 3, headers, lines, (4, 6), [28, 18, 18, 11, 14, 11, 12])
    workbook.close()
    return buffer.getvalue()
