"""Cell helpers over the sheet model (plan.md §9.4; J153; old `presentation_styles` at 891f1b3). Three rules hold for
every cell of the client spreadsheet, and each helper enforces one:

- Text is text. `text()` stores a string (number format `@`, quote prefix), fixed labels included, so a carrier-typed
  `=…` or `#N/A` is never a formula or an error; the writer puts it through `xlsx_safe.write_text`.
- A formula is ours only. `formula()` takes a code-built template that passes `grammar.check`, with its stored result.
- A blank is an EMPTY cell, never a dash. `number()` leaves the cell empty for None and for a value that is not finite.
"""

import math
import re
from decimal import Decimal

from . import grammar
from . import styles as s
from .model import BLANK, FORMULA, NUMBER, TEXT, Cell

# Characters XML 1.0 forbids: the C0 controls but tab and newline, a lone surrogate, U+FFFE and U+FFFF.
_ILLEGAL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff￾￿]')


def clean(value):
    """`value` as text a cell or a property may hold ('' for None)."""
    return _ILLEGAL.sub('', '' if value is None else str(value))


def plain(number):
    """A number as the file stores it: an int when whole, else a float; None stays None."""
    if number is None:
        return None
    if isinstance(number, bool) or not isinstance(number, int | float | Decimal):
        raise TypeError(f'a number, not {type(number).__name__}')
    if isinstance(number, Decimal):
        return int(number) if number == number.to_integral_value() else float(number)
    if isinstance(number, float) and not math.isfinite(number):
        return None
    return number


def result(value):
    """A formula's stored result: a number, a text, or '' for the blank the formula's own "" gives."""
    if value is None or value == '':
        return ''
    if isinstance(value, str):
        return value
    return plain(value)


def blank(sheet, row, col, **style):
    """An EMPTY cell that carries a style: a value typed into it later shows as money, in blue on an input."""
    return sheet.put(row, col, Cell(BLANK, style=s.style(**style)))


def text(sheet, row, col, value, **style):
    """Text, always stored as a string; a blank value (None or '') leaves the cell empty with its style."""
    value = clean(value)
    if not value:
        return blank(sheet, row, col, **style)
    look = s.style(**{'num': s.TEXT, **style})
    look['quote_prefix'] = True
    return sheet.put(row, col, Cell(TEXT, value, style=look))


def number(sheet, row, col, value, num, **style):
    """A number cell; None or a value that is not finite leaves it EMPTY (a rate is a number or nothing)."""
    value = plain(value)
    if value is None:
        return sheet.put(row, col, Cell(BLANK, style=s.style(num=num, **style)))
    return sheet.put(row, col, Cell(NUMBER, value, style=s.style(num=num, **style)))


def formula(sheet, row, col, template, value, num, *, sheets=None, **style):
    """A live formula with its stored result. Only code-built templates: never pass text a client typed."""
    grammar.check(template, sheets)
    return sheet.put(row, col, Cell(FORMULA, template, result(value), style=s.style(num=num, **style)))


def unlock(sheet, row, col):
    """Leave an input editable when the sheet is protected."""
    cell = sheet.get(row, col)
    if cell is not None:
        cell.style = {**cell.style, **s.UNLOCKED}
    return cell


def band(sheet, row, last_col, label, *, size=s.FONT_SIZE, height=s.ROW_H):
    """A full-width navy band: columns 1..last_col filled, the label in column A in white bold, no merge (a merged band
    crossing a frozen pane or a page break scrolls and prints badly)."""
    look = s.font(size, bold=True, color=s.WHITE)
    for col in range(2, last_col + 1):
        blank(sheet, row, col, fill=s.FILL_NAVY, font=look)
    text(sheet, row, 1, label, font=look, fill=s.FILL_NAVY, align=s.PLAIN_LEFT)
    sheet.heights[row] = height


def spacer(sheet, row):
    """A short empty row: no fill, no border."""
    sheet.heights[row] = s.SPACER_H


def merge_pair(sheet, row, first, last):
    """Merge one row's columns `first`..`last`; the partner cells wear the anchor's border."""
    if last <= first:
        raise ValueError('a merge needs two columns')
    anchor = sheet.get(row, first)
    border = {key: value for key, value in (anchor.style if anchor else {}).items() if key in BORDER_KEYS}
    for col in range(first + 1, last + 1):
        partner = sheet.get(row, col)
        if partner is None:
            blank(sheet, row, col)
            partner = sheet.get(row, col)
        partner.style = {**{k: v for k, v in partner.style.items() if k not in BORDER_KEYS}, **border}
    sheet.merge(row, first, row, last)


BORDER_KEYS = ('border', 'left', 'right', 'top', 'bottom')


def row_height(pairs, minimum=s.ROW_H, cap=s.MAX_ROW_H, line_pt=s.LINE_PT):
    """A row tall enough for its wrapped text. `pairs` is [(text, characters per line)], one per cell; a cell wraps on
    its newlines first, then by length. The tallest decides: `line_pt` per line plus 5, within `minimum` and `cap`."""
    lines = 1
    for value, chars in pairs:
        per_line = max(1, int(chars))
        flat = ('' if value is None else str(value)).replace('\r\n', '\n').replace('\r', '\n')
        count = sum(max(1, math.ceil(len(part) / per_line)) for part in flat.split('\n'))
        lines = max(lines, count)
    return float(min(cap, max(minimum, line_pt * lines + 5)))


def sheet_height_pt(sheet, last_row):
    """The sheet's height in points through `last_row`: every row's own height, 15 for a row with none."""
    return sum(float(sheet.heights.get(row) or s.DEFAULT_ROW_PT) for row in range(1, int(last_row) + 1))


def dropdown(sheet, cells, source_sheet, column, first_row, last_row, *, prompt=''):
    """A list drop-down on `cells` (r1, c1, r2, c2) offering one column of a tab of this workbook. A value typed that
    is not in the list is refused with a sentence, since the formulas look the pick up by its exact text."""
    source = grammar.validation_source(source_sheet, column, first_row, last_row)
    sheet.validations.append({'cells': cells, 'source': source, 'prompt': str(prompt or '')[:250]})


def highlight(sheet, cells, condition, look):
    """Fill `cells` while `condition` holds (a conditional format relative to the range's top-left cell)."""
    grammar.check_condition(condition)
    sheet.highlights.append({'cells': cells, 'condition': condition, 'style': dict(look)})
