"""A filled sheet as Excel's "Save As → CSV UTF-8" renders it (old `xlsx_fill.sheet_to_csv` 891f1b3; K91, K107).

Every row of the used range (styled empties included), every column of it, values as the cell's FORMAT displays
them, minimal quoting, CRLF and a UTF-8 BOM. Angle's instructions say to save their filled template as a CSV and
upload it; this is that file, derived from the workbook we would hand them, so the two can never disagree. One
exception to "as Excel would render it": a text cell a spreadsheet would run as a formula goes out behind a leading
apostrophe (`documents.xlsx_safe.csv_text`), and its coordinate is counted.
"""

import csv
import io
import re
from datetime import date, datetime

from documents.xlsx_safe import csv_text

from .refs import FillError
from .sheet import number_text, serial


def _date_text(value, number_format):
    """A date the way the cell's format shows it (mm/dd/yyyy, m/d/yyyy, mm-dd-yy…); else the serial."""
    code = re.sub(r'\[[^\]]*\]', '', (number_format or '').split(';')[0]).replace('\\', '')
    if not re.search(r'[ymd]', code, re.I) or code == 'General':
        return str(serial(value))
    out, i, lower = [], 0, code.lower()
    while i < len(lower):
        for token, fmt in (('yyyy', '%Y'), ('yy', '%y'), ('mm', '%m'), ('dd', '%d')):
            if lower.startswith(token, i):
                out.append(value.strftime(fmt))
                i += len(token)
                break
        else:
            ch = lower[i]
            if ch == 'm':
                out.append(str(value.month))
            elif ch == 'd':
                out.append(str(value.day))
            elif ch == 'y':
                out.append(value.strftime('%y'))
            else:
                out.append(code[i])
            i += 1
    return ''.join(out)


def _number_text(value, number_format):
    code = (number_format or 'General').split(';')[0]
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if code in ('General', '@') or not re.search(r'[0#]', code):
        if isinstance(value, float):
            return str(int(value)) if value.is_integer() else f'{value:.11g}'
        return number_text(value)
    prefix = ''.join(re.findall(r'"([^"]*)"', code.split('#')[0].split('0')[0]))
    dot = re.search(r'\.(0+)', code)
    decimals = len(dot.group(1)) if dot else 0
    grouped = ',' in code.replace('"', '')
    return f'{prefix}{value:,.{decimals}f}' if grouped else f'{prefix}{value:.{decimals}f}'


def sheet_to_csv(xlsx_bytes, sheet_name):
    """(CSV bytes, [coordinates of text cells given a leading apostrophe])."""
    import openpyxl

    book = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    if sheet_name not in book.sheetnames:
        raise FillError(f'No sheet named {sheet_name!r}')
    sheet = book[sheet_name]
    text = io.StringIO()
    writer = csv.writer(text, lineterminator='\r\n')
    fenced = []
    for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row, min_col=1, max_col=sheet.max_column):
        fields = []
        for cell in row:
            value = cell.value
            if value is None:
                fields.append('')
            elif isinstance(value, datetime | date):
                fields.append(_date_text(value, cell.number_format))
            elif isinstance(value, int | float):
                fields.append(_number_text(value, cell.number_format))
            else:
                shown = str(value)
                if cell.data_type == 's':
                    safe = csv_text(shown)
                    if safe != shown:
                        fenced.append(cell.coordinate)
                    shown = safe
                fields.append(shown)
        writer.writerow(fields)
    return text.getvalue().encode('utf-8-sig'), fenced
