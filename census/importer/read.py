"""Reading a census file into a table (plan.md §5.3.2 steps 1–2; C12). Pure: bytes in, rows of text out.

`.csv` (UTF-8 with or without BOM, else Latin-1), `.xlsx`/`.xlsm` (read-only, cached values: a formula never runs) and
`.xls` (xlrd) go through documents' one sheet loader, so every cell is text the way a reader sees it: dates MM/DD/YYYY,
whole numbers without `.0`, everything else trimmed. Anything else is refused. The header row is the first of the top
10 rows with at least three label-like cells; the member may choose another sheet, header row and first data row
(Warner's own template has its header on row 3 and people from row 7, §9.8). Errors never name the file: a census
file's name may carry a person's (§3.8).
"""

import re
from collections import namedtuple

from documents import kinds, sheets
from documents.sheets import SheetError, column_letter

from ..values import mask_ssn

HEADER_SCAN = 10
MIN_LABELS = 3
SAMPLES = 3
NOT_A_SHEET = 'This file is not a spreadsheet or CSV census file.'
NO_HEADER = 'Could not find a header row in this file.'
_NOT_LABEL = re.compile(r'[\d/.,$-]+')
_SSN_LIKE = re.compile(r'^\s*\d{3}-?\d{2}-?\d{4}\s*$')

# headers: the header row's cells, trailing blanks dropped. rows: the data rows as text, padded to the headers, fully
# blank rows dropped. numbers: each kept row's own 1-based row number in the sheet (its source cell, §5.3.2 step 6).
Table = namedtuple('Table', 'sheet headers rows numbers')


class CensusFileError(ValueError):
    """A census file that cannot be read, said in words (the 400)."""


def sheet_grids(filename, raw, sheet=None):
    """(sheet names, the chosen sheet's name, its rows as text). `sheet` defaults to the first sheet."""
    if kinds.shape_of(filename) != kinds.SHEET:
        raise CensusFileError(NOT_A_SHEET)
    chosen = []

    def pick(names):
        chosen.append(sheet if sheet in names else names[0])
        return chosen[0]

    try:
        loaded = sheets.load_sheets(filename, raw, pick=pick)
    except SheetError as exc:
        raise CensusFileError(NOT_A_SHEET) from exc
    names = [entry['name'] for entry in loaded]
    name = chosen[0] if chosen else names[0]
    rows = next(entry['rows'] for entry in loaded if entry['name'] == name)
    return names, name, rows


def _labels(row):
    return sum(1 for text in row if text and not _NOT_LABEL.fullmatch(text))


def find_header_row(rows):
    """The 1-based header row: the first of the top 10 rows with three or more label-like cells, else None."""
    for index, row in enumerate(rows[:HEADER_SCAN]):
        if _labels(row) >= MIN_LABELS:
            return index + 1
    return None


def table(sheet, rows, header_row, first_data_row=None):
    """The table under `header_row` (1-based); data from `first_data_row` (default the row below)."""
    if header_row is None or header_row < 1 or header_row > len(rows):
        raise CensusFileError(NO_HEADER)
    headers = [text.strip() for text in rows[header_row - 1]]
    while headers and not headers[-1]:
        headers.pop()
    if not headers:
        raise CensusFileError(NO_HEADER)
    start = first_data_row or header_row + 1
    kept, numbers = [], []
    for number in range(start, len(rows) + 1):
        row = (list(rows[number - 1]) + [''] * len(headers))[: len(headers)]
        if any(row):
            kept.append(row)
            numbers.append(number)
    return Table(sheet, headers, kept, numbers)


def samples(table_, column, limit=SAMPLES):
    """Up to three values a column holds, read for one answer and never stored (§5.3.2 step 4). Anything shaped like
    an SSN shows its last four only (OQ16)."""
    found = []
    for row in table_.rows:
        text = row[column] if column < len(row) else ''
        if text:
            found.append(mask_ssn(text) if _SSN_LIKE.match(text) else text)
        if len(found) >= limit:
            break
    return found


def cell(table_, column, index):
    """The source cell of data row `index`, column `column`: 'Census!D12' (§5.3.2 step 6)."""
    return f'{table_.sheet}!{column_letter(column)}{table_.numbers[index]}'
