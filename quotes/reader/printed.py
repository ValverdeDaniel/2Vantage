"""Synthetic carrier files from a printed-table spec, and the answer a perfect read gives (plan.md §12.8; Q.6).

The Eval corpus and GD3's renewal packet are built here, so a file and its key come from one spec and the key is
known by construction. A table spec:

    {'line': 'medical', 'carrier': 'Coastline Health', 'title': '2027 group renewal',
     'columns': [{'carrier', 'name', 'plan_number', 'codes', 'side', 'renews', 'replaces'}],   # renews: column index
     'rows': [('Deductible (single)', 'deductible_single', ['2500', '2500', ...]), ...],      # key '' = no field
     'counts': {column index: {'EE': 18, ...}}}

`pdf(tables, ...)` prints a cover letter, one page per table and a page carrying only the running header and footer
(which a read leaves out); `xlsx(tables)` one sheet per table. `answer(tables, pages)` is what a perfect read of
those pages returns, in the reader's schema. Synthetic only: every carrier, plan and rate is invented.
"""

import io

from .schema import NO_RENEWAL, TIERS, WHOLE_LINE

HEADER = '{carrier} · Group benefits · {title}'
FOOTER = 'Confidential: prepared for the employer group named on the cover. Rates are monthly.'
TIER_WORDS = {'EE': 'Employee only', 'ES': 'Employee + spouse', 'EC': 'Employee + child(ren)', 'FAM': 'Family'}


def _running(table, number, total):
    header = HEADER.format(carrier=table['carrier'], title=table['title'])
    return [(40, 760, header, 9), (40, 30, FOOTER, 7), (520, 16, f'Page {number} of {total}', 7)]


def _cover(table, number, total):
    lines = [
        (40, 700, 'Dear benefits partner,', 11),
        (40, 680, 'Enclosed are the plan options and monthly rates for your group, effective on the date shown in', 10),
        (40, 666, 'the agreement. Rates assume the enrollment shown and are subject to underwriting review.', 10),
    ]
    return _running(table, number, total) + lines


def _table_page(table, number, total):
    columns = table['columns']
    width = (612 - 220) / max(len(columns), 1)
    out = _running(table, number, total) + [(40, 720, f'{table["title"]}: plan options', 12, True)]
    y = 696
    for index, column in enumerate(columns):
        x = 220 + index * width
        side = {'current': 'Current', 'renewal': 'Renewal', 'quote': 'Proposed'}[column['side']]
        out += [(x, y, column['name'], 7, True), (x, y - 10, side, 7)]
        if column.get('plan_number'):
            out.append((x, y - 20, f'Plan {column["plan_number"]}', 7))
        if column.get('codes'):
            out.append((x, y - 30, 'Group ' + ', '.join(column['codes']), 6))
        if column.get('replaces'):
            out.append((x, y - 40, f'Replaces {column["replaces"]}', 6))
    y -= 56
    for label, _key, values in table['rows']:
        out.append((40, y, label, 8))
        for index, value in enumerate(values):
            out.append((220 + index * width, y, str(value), 8))
        y -= 14
    for tier in TIERS:
        if not any(tier in counts for counts in table.get('counts', {}).values()):
            continue
        out.append((40, y, f'Enrolled: {TIER_WORDS[tier]}', 8))
        for index, counts in table.get('counts', {}).items():
            if tier in counts:
                out.append((220 + index * width, y, str(counts[tier]), 8))
        y -= 14
    return out


def pdf(tables, *, blank_page=True):
    """The PDF bytes: a cover letter, one page per table, then (optionally) a header-only page."""
    from synthetic_files import pdf as write_pdf  # the root's tiny PDF writer (tests, seeds and this corpus)

    total = 1 + len(tables) + (1 if blank_page else 0)
    pages = [_cover(tables[0], 1, total)]
    pages += [_table_page(table, number, total) for number, table in enumerate(tables, start=2)]
    if blank_page:
        pages.append(_running(tables[0], total, total))
    return write_pdf(pages)


def table_pages(tables):
    """The page each table is printed on in `pdf(tables)`."""
    return {index: index + 2 for index in range(len(tables))}


def xlsx(tables):
    """A workbook with one sheet per table: labels in column A, one plan per column from B."""
    import openpyxl

    book = openpyxl.Workbook()
    book.remove(book.active)
    for number, table in enumerate(tables, start=1):
        sheet = book.create_sheet(f'Options {number}')
        sheet.append([table['title']])
        sheet.append(['Plan', *[column['name'] for column in table['columns']]])
        sheet.append(['Option', *[column['side'].title() for column in table['columns']]])
        for label, _key, values in table['rows']:
            sheet.append([label, *values])
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def _cell(table, row_index, col_index, sheet_cell):
    if sheet_cell is None:
        return ''
    from documents.sheets import column_letter

    return f'{sheet_cell}!{column_letter(col_index + 1)}{row_index + 4}'


def answer(tables, *, pages=None, sheets=False):
    """What a perfect read returns: one block per table, columns in printed order, every row, the printed counts."""
    blocks = []
    pages = pages or table_pages(tables)
    for index, table in enumerate(tables):
        page = 0 if sheets else pages[index]
        sheet = f'Options {index + 1}' if sheets else None
        columns = [
            {
                'col': number + 1,
                'carrier': column['carrier'],
                'plan_name': column['name'],
                'plan_number': column.get('plan_number', ''),
                'codes': list(column.get('codes', [])),
                'side': column['side'],
                'renews_col': column['renews'] + 1 if column.get('renews') is not None else NO_RENEWAL,
                'replaces': column.get('replaces', ''),
                'unsure': False,
            }
            for number, column in enumerate(table['columns'])
        ]
        rows = [
            {
                'label': label,
                'key': key,
                'cells': [
                    {
                        'col': number + 1,
                        'value': str(value),
                        'page': page,
                        'cell': _cell(table, r, number, sheet),
                        'unsure': False,
                    }
                    for number, value in enumerate(values)
                    if str(value).strip()
                ],
            }
            for r, (label, key, values) in enumerate(table['rows'])
        ]
        counts = [
            {
                'col': (number + 1) if number != WHOLE_LINE else WHOLE_LINE,
                'tier': tier,
                'count': tier_counts[tier],
                'page': page,
            }
            for number, tier_counts in sorted(table.get('counts', {}).items())
            for tier in TIERS
            if tier in tier_counts
        ]
        blocks.append({'line': table['line'], 'columns': columns, 'rows': rows, 'counts': counts})
    return {'lines': blocks}
