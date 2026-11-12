"""The one guard against spreadsheet injection (plan.md §3.8, §9; D114, J153, K107; O.6 #34).

Text written into a generated workbook stays text, whoever typed it (a person, a client or Claude):
- XlsxWriter (the client workbook, the stop-loss workbook, the Book export): `workbook()` turns string-to-formula,
  string-to-URL and string-to-number conversion off; `write_text` writes with `write_string`; links are written one
  by one with `write_link`, and only web and mail links.
- openpyxl (the plan and census templates): `put` writes text as a string cell, with the quote prefix when it begins
  like a formula, so Excel never evaluates it.
- CSV: `csv_text` gives text that begins like a formula a leading apostrophe.
Formulas the code writes on purpose (with the app's number as the stored result, §9) are exempt: they use
`worksheet.write_formula` directly.
"""

import datetime
from decimal import Decimal

RISKY = ('=', '+', '-', '@', '\t', '\r')
SAFE_OPTIONS = {'strings_to_formulas': False, 'strings_to_urls': False, 'strings_to_numbers': False}
LINK_SCHEMES = ('http://', 'https://', 'mailto:')


def workbook(target, options=None):
    """An XlsxWriter workbook (to a path or a BytesIO) with every string conversion off."""
    import xlsxwriter

    return xlsxwriter.Workbook(target, {**(options or {}), **SAFE_OPTIONS})


def write_text(worksheet, row, col, value, cell_format=None):
    """Text, always as text: '=SUM(A1)' prints as typed and never runs."""
    return worksheet.write_string(row, col, '' if value is None else str(value), cell_format)


def write(worksheet, row, col, value, cell_format=None):
    """A value by its Python type: numbers as numbers, dates as dates, None as a blank, anything else as text."""
    if value is None:
        return worksheet.write_blank(row, col, None, cell_format)
    if isinstance(value, bool):
        return worksheet.write_boolean(row, col, value, cell_format)
    if isinstance(value, int | float | Decimal):
        return worksheet.write_number(row, col, float(value), cell_format)
    if isinstance(value, datetime.date | datetime.datetime):
        return worksheet.write_datetime(row, col, value, cell_format)
    return write_text(worksheet, row, col, value, cell_format)


def write_link(worksheet, row, col, url, text=None, cell_format=None):
    """One explicit link (J153): web and mail addresses only; anything else is written as plain text."""
    url = str(url or '').strip()
    if not url.lower().startswith(LINK_SCHEMES):
        return write_text(worksheet, row, col, text if text is not None else url, cell_format)
    return worksheet.write_url(row, col, url, cell_format, string=text if text is not None else url)


def put(ws, row, column, value):
    """openpyxl: write a value; text that begins like a formula is a literal string with the quote prefix."""
    cell = ws.cell(row=row, column=column)
    cell.value = value
    if isinstance(value, str):
        cell.data_type = 's'
        if value.startswith(RISKY):
            cell.quotePrefix = True
    return cell


def csv_text(value):
    """A CSV field: text that begins like a formula gets a leading apostrophe (K107)."""
    text = '' if value is None else str(value)
    return f"'{text}" if text.startswith(RISKY) else text
