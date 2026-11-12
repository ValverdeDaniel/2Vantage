"""The client spreadsheets compared (Q.5): the sheets and the tab the file opens on; per sheet the frozen panes,
zoom, gridlines, merges, drop-downs, conditional fills, pictures and print setup; per row its height (±0.75 pt), per
column its width (±0.5 character); per cell its value or formula, number format, font, fill and border.

Rows are lined up by their label (column A, else B) and columns by their heading cells (rows 1–8), so an inserted
row or plan column is one difference; formulas, merges, drop-downs and print ranges are read through that alignment
(`refs.translate`) before they are compared. Authors are not compared (masked, Q.5).

`compare(old_path, new_path)` → [{where, kind, old, new}].
"""

import re

import openpyxl
from openpyxl.utils import get_column_letter

from . import align, mask, xlsx_cells, xlsx_setup

WIDTH_TOLERANCE = 0.5  # characters
HEIGHT_TOLERANCE = 0.75  # points
DEFAULT_ROW_PT = 15.0
HEADING_ROWS = 8
_NUMBERED = re.compile(r'\b(Option|Current|Renewal) \d+\b')


def _text(ws, row, col):
    cell = ws._cells.get((row, col))
    raw = getattr(cell, 'value', None)
    if raw is None or getattr(cell, 'data_type', '') == 'f':
        return ''
    return mask.line(raw)


def _row_keys(ws):
    return [_heading(_text(ws, row, 1) or _text(ws, row, 2)) for row in range(1, ws.max_row + 1)]


def _heading(text):
    """A heading cell as the alignment reads it: option numbers and the ★ of a presented plan set aside, since a plan
    added before a column renumbers it."""
    return _NUMBERED.sub(r'\1', text).replace('★ ', '')


def _col_keys(ws):
    rows = range(1, min(ws.max_row, HEADING_ROWS) + 1)
    return ['|'.join(_heading(_text(ws, row, col)) for row in rows) for col in range(1, ws.max_column + 1)]


def _maps(old_ws, new_ws):
    rows = align.pairs(_row_keys(old_ws), _row_keys(new_ws))
    cols = align.pairs(_col_keys(old_ws), _col_keys(new_ws))
    shift = [(o + 1 if o is not None else None, n + 1 if n is not None else None) for o, n in rows]
    cshift = [(o + 1 if o is not None else None, n + 1 if n is not None else None) for o, n in cols]
    return shift, cshift


def _width(ws, col):
    dim = ws.column_dimensions.get(get_column_letter(col))
    if dim is not None and dim.width:
        return float(dim.width)
    for dim in ws.column_dimensions.values():
        if dim.min and dim.max and dim.min <= col <= dim.max and dim.width:
            return float(dim.width)
    return float(ws.sheet_format.defaultColWidth or 8.43)


def _height(ws, row):
    dim = ws.row_dimensions.get(row)
    height = getattr(dim, 'height', None) if dim is not None else None
    return float(height) if height else float(ws.sheet_format.defaultRowHeight or DEFAULT_ROW_PT)


def _sheet(title, old_ws, new_ws, row_pairs, col_pairs, maps):
    out = []

    def add(where, kind, old, new):
        out.append({'where': f'{title}!{where}', 'kind': kind, 'old': old, 'new': new})

    for o, n in row_pairs:
        if o is None:
            add(f'row {n}', 'row-added', None, _text(new_ws, n, 1) or _text(new_ws, n, 2) or '(no label)')
        elif n is None:
            add(f'row {o} (old)', 'row-removed', _text(old_ws, o, 1) or _text(old_ws, o, 2) or '(no label)', None)
        elif abs(_height(old_ws, o) - _height(new_ws, n)) > HEIGHT_TOLERANCE:
            add(f'row {n}', 'row-height', _height(old_ws, o), _height(new_ws, n))
    for o, n in col_pairs:
        if o is None:
            add(f'column {get_column_letter(n)}', 'column-added', None, _col_keys(new_ws)[n - 1] or '(no heading)')
        elif n is None:
            old_key = _col_keys(old_ws)[o - 1] or '(no heading)'
            add(f'column {get_column_letter(o)} (old)', 'column-removed', old_key, None)
        elif abs(_width(old_ws, o) - _width(new_ws, n)) > WIDTH_TOLERANCE:
            add(f'column {get_column_letter(n)}', 'column-width', round(_width(old_ws, o), 3), _width(new_ws, n))
    rows = [(o, n) for o, n in row_pairs if o and n]
    cols = [(o, n) for o, n in col_pairs if o and n]
    for o_row, n_row in rows:
        for o_col, n_col in cols:
            old_cell, new_cell = old_ws._cells.get((o_row, o_col)), new_ws._cells.get((n_row, n_col))
            if old_cell is None and new_cell is None:
                continue
            old = xlsx_cells.read(old_cell, title, maps)
            new = xlsx_cells.read(new_cell, title)
            both = old_cell is not None and new_cell is not None
            for kind, before, after in xlsx_cells.differences(old, new, both=both):
                add(f'{get_column_letter(n_col)}{n_row}', kind, before, after)
    removed = ({o for o, n in row_pairs if n is None}, {o for o, n in col_pairs if n is None})
    added = ({n for o, n in row_pairs if o is None}, {n for o, n in col_pairs if o is None})
    for where, kind, before, after in xlsx_setup.differences(title, old_ws, new_ws, maps, removed, added):
        add(where, kind, before, after)
    return out


def compare(old_path, new_path):
    old_book = openpyxl.load_workbook(old_path)
    new_book = openpyxl.load_workbook(new_path)
    out = []
    old_titles, new_titles = old_book.sheetnames, new_book.sheetnames
    for title in old_titles:
        if title not in new_titles:
            out.append({'where': title, 'kind': 'sheet-removed', 'old': title, 'new': None})
    for title in new_titles:
        if title not in old_titles:
            out.append({'where': title, 'kind': 'sheet-added', 'old': None, 'new': title})
    common = [t for t in new_titles if t in old_titles]
    if [t for t in old_titles if t in common] != common:
        out.append({'where': 'tab order', 'kind': 'sheet-order', 'old': old_titles, 'new': new_titles})
    if old_book.active.title != new_book.active.title:
        out.append({'where': 'opens on', 'kind': 'active-sheet', 'old': old_book.active.title,
                    'new': new_book.active.title})  # fmt: skip
    aligned, maps = {}, {}
    for title in common:
        row_pairs, col_pairs = _maps(old_book[title], new_book[title])
        aligned[title] = (row_pairs, col_pairs)
        maps[title] = (align.mapping(row_pairs), align.mapping(col_pairs))
    for title in common:
        row_pairs, col_pairs = aligned[title]
        out.extend(_sheet(title, old_book[title], new_book[title], row_pairs, col_pairs, maps))
    return out
