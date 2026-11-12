"""A read-only window onto an uploaded spreadsheet (plan.md §7.4; E27–E29, D-119, D-167; OQ25).

`window()` answers `GET documents/{id}/sheet/`: the sheet list, one window of 200 rows as text, and, for "As in Excel",
the window's look (`sheet_look.look`). Every cell's text is what a reader sees (dates MM/DD/YYYY, float noise
rounded); the look never changes it. Hidden sheets, rows and columns are shown and tagged (OQ25), since a read skips
them. `.xlsx`/`.xlsm` read through openpyxl (a macro never runs), `.xls` through xlrd, a CSV as one sheet.

One parse per request and nothing cached (E29, ch. 29): Plain streams the workbook read-only; "As in Excel" loads it
once in full (up to 5 MB) and reads both the text and the look from that one load. Limits: 15 MB, 20,000 rows and
150 columns read per sheet, 200 characters sent per cell. Pure: bytes in, a dict out; nothing is logged.
"""

import csv
import datetime
import io
import re
import warnings

from . import kinds

WINDOW_ROWS = 200
MAX_COLS = 150
MAX_ROWS = 20000
MAX_CELL = 200
MAX_BYTES = 15 * 1024 * 1024
MAX_LOOK_BYTES = 5 * 1024 * 1024  # a full load costs far more memory than a read-only one
CONTEXT_ROWS = 15  # rows shown above a cell that is opened
CSV_SHEET = 'Sheet1'
STYLED = ('.xlsx', '.xlsm')


class SheetError(ValueError):
    """Said in words: the view's 400."""


def column_letter(index):
    """0 -> A, 25 -> Z, 26 -> AA."""
    out, n = '', index + 1
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


_A1 = re.compile(r'^([A-Za-z]{1,3})([0-9]{1,7})$')


def parse_ref(ref, sheet=''):
    """'Medical!C7' (or 'C7' with `sheet`) -> (sheet, row, col), 0-based; None when it is not a cell reference."""
    ref = (ref or '').strip()
    if '!' in ref:
        sheet, ref = ref.rsplit('!', 1)
        sheet = sheet.strip("'")
    match = _A1.match(ref)
    if not match:
        return None
    col = 0
    for ch in match.group(1).upper():
        col = col * 26 + (ord(ch) - 64)
    return sheet, int(match.group(2)) - 1, col - 1


def cell_text(value):
    """A parsed cell as display text, as the readers write it: dates MM/DD/YYYY, whole floats without '.0'."""
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, datetime.datetime) and value.time() != datetime.time():
        return value.strftime('%m/%d/%Y %H:%M')
    if isinstance(value, datetime.date | datetime.datetime):
        return value.strftime('%m/%d/%Y')
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return repr(round(value, 6)).rstrip('0').rstrip('.')
    return str(value).strip()


def _trimmed(rows):
    while rows and not any(rows[-1]):
        rows.pop()
    return rows


def _openpyxl(raw, full):
    import openpyxl

    try:
        with warnings.catch_warnings():  # a carrier's print areas and data validations warn on load
            warnings.simplefilter('ignore')
            return openpyxl.load_workbook(io.BytesIO(raw), read_only=not full, data_only=True)
    except Exception as exc:  # noqa: BLE001 - a corrupt or password-protected workbook
        raise SheetError("This workbook can't be opened.") from exc


def _rows_of(ws):
    width = min(ws.max_column or MAX_COLS, MAX_COLS)
    rows = []
    for index, row in enumerate(ws.iter_rows(values_only=True, max_col=width)):
        if index >= MAX_ROWS:
            break
        rows.append([cell_text(value) for value in row])
    return _trimmed(rows)


def _xls_sheets(raw, pick=None):
    import xlrd

    try:
        book = xlrd.open_workbook(file_contents=raw, on_demand=True)
    except Exception as exc:  # noqa: BLE001
        raise SheetError("This workbook can't be opened.") from exc
    sheets = []
    try:
        wanted = pick(book.sheet_names()) if pick else None
        for index in range(book.nsheets):
            sheet = book.sheet_by_index(index)
            rows = []
            if wanted is None or sheet.name == wanted:
                for r in range(min(sheet.nrows, MAX_ROWS)):
                    rows.append([cell_text(_xls_value(cell, book.datemode)) for cell in sheet.row(r)[:MAX_COLS]])
            sheets.append({'name': sheet.name, 'rows': _trimmed(rows), 'hidden': bool(sheet.visibility)})
            book.unload_sheet(index)
    finally:
        book.release_resources()
    return sheets


def _xls_value(cell, datemode):
    import xlrd

    if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK, xlrd.XL_CELL_ERROR):
        return None
    if cell.ctype == xlrd.XL_CELL_DATE:
        try:
            return xlrd.xldate_as_datetime(cell.value, datemode)
        except (ValueError, OverflowError, xlrd.xldate.XLDateError):
            return cell.value
    if cell.ctype == xlrd.XL_CELL_BOOLEAN:
        return bool(cell.value)
    return cell.value


def _csv_sheet(raw):
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('latin-1')
    rows = []
    for index, row in enumerate(csv.reader(io.StringIO(text))):
        if index >= MAX_ROWS:
            break
        rows.append([cell.strip() for cell in row[:MAX_COLS]])
    return [{'name': CSV_SHEET, 'rows': _trimmed(rows), 'hidden': False}]


def _check(filename, raw):
    if kinds.shape_of(filename) != kinds.SHEET:
        raise SheetError('That file is not a spreadsheet.')
    if len(raw) > MAX_BYTES:
        raise SheetError('This workbook is too large to preview — download the file.')


def load_sheets(filename, raw, pick=None, book=None):
    """[{name, rows, hidden}] for every sheet. With `pick` (sheet names -> one of them) only the picked sheet's rows
    are read; the others come back empty. `book` is an openpyxl workbook already open on these bytes."""
    _check(filename, raw)
    extension = kinds.extension(filename)
    if extension == '.csv':
        return _csv_sheet(raw)
    if extension == '.xls':
        return _xls_sheets(raw, pick)
    opened = book is None
    book = book or _openpyxl(raw, full=False)
    try:
        if not book.sheetnames:
            raise SheetError('This workbook has no sheets.')
        wanted = pick(book.sheetnames) if pick else None
        return [
            {
                'name': ws.title,
                'rows': _rows_of(ws) if wanted is None or ws.title == wanted else [],
                'hidden': ws.sheet_state != 'visible',
            }
            for ws in book.worksheets
        ]
    finally:
        if opened:
            book.close()


def window(filename, raw, *, sheet=None, start=None, cell=None, look=True):
    """The sheet list and one window of rows. `cell` ('Medical!C7') opens its sheet around it and names it as the
    `match`; otherwise `sheet` (default the first) from `start` (default 0). With `look`, an .xlsx or .xlsm up to
    5 MB carries `format` (sheet_look.look); any other file, or a look that cannot be read, has `format` None."""
    from .sheet_look import look as read_look

    _check(filename, raw)
    target = parse_ref(cell, sheet or '') if cell else None
    styled = look and kinds.extension(filename) in STYLED and len(raw) <= MAX_LOOK_BYTES
    book = _openpyxl(raw, full=True) if styled else None
    picked = []

    def pick(names):
        picked.append(_chosen(names, sheet, target))
        return picked[0]

    sheets = load_sheets(filename, raw, pick=pick, book=book)
    wanted = picked[0] if picked else sheets[0]['name']
    rows = next(s for s in sheets if s['name'] == wanted)['rows']
    match = None
    if target and target[0] in ('', wanted) and target[2] < MAX_COLS:
        letter = column_letter(target[2])
        match = {'sheet': wanted, 'row': target[1], 'col': target[2], 'cell': f'{letter}{target[1] + 1}'}
    if start is None:
        start = max(0, match['row'] - CONTEXT_ROWS) if match else 0
    start = max(0, min(int(start), max(0, len(rows) - 1)))
    shown = [[text[:MAX_CELL] for text in row] for row in rows[start : start + WINDOW_ROWS]]
    cols = max((len(row) for row in shown), default=0)
    fmt = None
    if book is not None:
        try:
            fmt = read_look(book, wanted, start, len(shown), cols)
        except Exception:  # noqa: BLE001 - a look we can't read is no look, never an error
            fmt = None
    return {
        'sheets': [{'name': s['name'], 'hidden': s['hidden']} for s in sheets],
        'sheet': wanted,
        'start': start,
        'window': WINDOW_ROWS,
        'total_rows': len(rows),
        'cols': cols,
        'col_letters': [column_letter(i) for i in range(cols)],
        'rows': [row + [''] * (cols - len(row)) for row in shown],
        'match': match,
        'format': fmt,
    }


def _chosen(names, sheet, target):
    for candidate in (sheet, target[0] if target else None):
        if candidate and candidate in names:
            return candidate
    return names[0]
