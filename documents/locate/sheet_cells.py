"""A workbook's visible cells, as the locator searches them (E82, D-122; OQ25). Pure: bytes in, rows out.

A quote read skips what Excel hides, so the locator does too: hidden sheets are left out, and hidden rows and columns
read as blank, keeping every other cell at its own address ("Medical!C10"). Text is the viewer's (`sheets.cell_text`:
dates MM/DD/YYYY, float noise rounded), so a cell the locator names opens on the same text. `.xlsx`/`.xlsm` through
openpyxl (a macro never runs), `.xls` through xlrd, a CSV as its one sheet. Nothing here logs a cell.
"""

import io
import warnings

from .. import kinds
from ..sheets import CSV_SHEET, MAX_BYTES, MAX_COLS, MAX_ROWS, SheetError, _xls_value, cell_text, load_sheets


class TooLarge(SheetError):
    """Past the viewer's 15 MB: not searched."""


def _trimmed(rows):
    while rows and not any(rows[-1]):
        rows.pop()
    return rows


def _hidden_columns(sheet):
    from openpyxl.utils import column_index_from_string

    hidden = set()
    for key, dim in list(sheet.column_dimensions.items()):
        if not dim.hidden:
            continue
        try:
            low = dim.min or column_index_from_string(key)
        except ValueError:
            continue
        hidden.update(range(low - 1, min(dim.max or low, MAX_COLS)))
    return hidden


def _xlsx(raw):
    import openpyxl

    try:
        with warnings.catch_warnings():  # a carrier's print areas and data validations warn on load
            warnings.simplefilter('ignore')
            book = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)  # full mode: row and column dimensions
    except Exception as exc:  # noqa: BLE001 - a corrupt or password-protected workbook
        raise SheetError("This workbook can't be opened.") from exc
    sheets = []
    try:
        for sheet in book.worksheets:
            if sheet.sheet_state != 'visible':
                continue
            hidden_cols = _hidden_columns(sheet)
            dims = sheet.row_dimensions
            rows = []
            width = min(sheet.max_column or MAX_COLS, MAX_COLS)
            for index, row in enumerate(sheet.iter_rows(values_only=True, max_col=width)):
                if index >= MAX_ROWS:
                    break
                dim = dims.get(index + 1)  # .get: indexing would add a row
                if dim is not None and dim.hidden:
                    rows.append([])
                    continue
                rows.append(['' if c in hidden_cols else cell_text(value) for c, value in enumerate(row)])
            sheets.append((sheet.title, _trimmed(rows)))
    finally:
        book.close()
    return sheets


def _xls(raw):
    import xlrd

    try:
        book = xlrd.open_workbook(file_contents=raw, formatting_info=True)
    except Exception as exc:  # noqa: BLE001
        raise SheetError("This workbook can't be opened.") from exc
    sheets = []
    for sheet in book.sheets():
        if sheet.visibility:
            continue
        rows = []
        for r in range(min(sheet.nrows, MAX_ROWS)):
            info = sheet.rowinfo_map.get(r)
            if info is not None and info.hidden:
                rows.append([])
                continue
            line = []
            for c, cell in enumerate(sheet.row(r)[:MAX_COLS]):
                col = sheet.colinfo_map.get(c)
                line.append('' if col is not None and col.hidden else cell_text(_xls_value(cell, book.datemode)))
            rows.append(line)
        sheets.append((sheet.name, _trimmed(rows)))
    book.release_resources()
    return sheets


def visible_sheets(filename, raw):
    """[(sheet name, rows of cell text)] for every visible sheet. Raises SheetError (unreadable) or TooLarge."""
    if kinds.shape_of(filename) != kinds.SHEET:
        raise SheetError('That file is not a spreadsheet.')
    if len(raw) > MAX_BYTES:
        raise TooLarge('This workbook is too large to search.')
    extension = kinds.extension(filename)
    if extension == '.csv':
        return [(CSV_SHEET, sheet['rows']) for sheet in load_sheets(filename, raw)]
    if extension == '.xls':
        return _xls(raw)
    return _xlsx(raw)
