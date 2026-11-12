"""How a tab of the client spreadsheet looks in Excel, read from the sheet model (plan.md §9.4; J116; Q.9 row 28):
exactly what documents' `look()` reads from the tab as the download's writer writes it — `look(write(model))`, which
the tests hold this to on the golden deals — without writing and re-reading the file. Re-reading costs seconds on a
large deal (openpyxl binds every merged cell: a 600-plan Composite Rates tab holds 30,000 merges).

What the round trip does, reproduced: each cell wears its XlsxWriter format as openpyxl reads it back
(`documents.sheet_style.cell_style`'s keys); a cell the model leaves empty wears the workbook's default (Calibri 11,
the theme's dark text); a merged cell other than the merge's own reads as openpyxl's MergedCell, the default with the
merge's outer borders; then documents settles borders between neighbours and draws a merge as its own cell, as
`look()` does. Pure.
"""

from documents.sheet_look import _cover, _settled  # the one way borders settle and merges draw (sheet_look.look)
from documents.sheet_style import BORDERS, H_ALIGN, V_ALIGN

from . import sizes

DEFAULT = {'ff': 'Calibri', 's': 11.0, 'fg': '#000000'}  # XlsxWriter's default font, its colour the theme's dk1
DEFAULT_ROW_PT = 15.0
DEFAULT_ROW_PX = 20  # Excel's 15 pt
# XlsxWriter's border indexes → Excel's style names; its alignment words → Excel's.
BORDER_NAMES = (
    None, 'thin', 'medium', 'dashed', 'dotted', 'thick', 'double', 'hair',
    'mediumDashed', 'dashDot', 'mediumDashDot', 'dashDotDot', 'mediumDashDotDot', 'slantDashDot',
)  # fmt: skip
EXCEL_H = {'center_across': 'centerContinuous'}
EXCEL_V = {'vcenter': 'center', 'vjustify': 'justify', 'vdistributed': 'distributed', 'vtop': 'top'}
SIDES = (('top', 'bt'), ('right', 'br'), ('bottom', 'bb'), ('left', 'bl'))


def _hex(value):
    return '#' + str(value).lstrip('#').upper()[-6:]


def _borders(style):
    """{look key: '1px solid #000000'} for the format's four sides."""
    out = {}
    for side, key in SIDES:
        index = style.get(side, style.get('border'))
        name = BORDER_NAMES[index] if isinstance(index, int) and 0 <= index < len(BORDER_NAMES) else None
        line = BORDERS.get(name)
        if line:
            colour = style.get(f'{side}_color', style.get('border_color'))
            out[key] = f'{line} {_hex(colour) if colour else "#000000"}'
    return out


def written_style(style):
    """The look of a cell wearing the XlsxWriter format `style` once the file is read back."""
    if not style:
        return dict(DEFAULT)
    out = {}
    if style.get('pattern') == 1 and (style.get('fg_color') or style.get('bg_color')):
        out['bg'] = _hex(style.get('fg_color') or style['bg_color'])
    out['ff'] = style.get('font_name', 'Calibri')
    for prop, key in (('bold', 'b'), ('italic', 'i'), ('font_strikeout', 'x'), ('underline', 'u')):
        if style.get(prop):
            out[key] = 1
    out['s'] = round(float(style.get('font_size', 11)), 1)
    out['fg'] = _hex(style['font_color']) if style.get('font_color') else '#000000'
    if style.get('align'):
        horizontal = H_ALIGN.get(EXCEL_H.get(style['align'], style['align']))
        if horizontal:
            out['ha'] = horizontal
    if style.get('valign'):
        vertical = V_ALIGN.get(EXCEL_V.get(style['valign'], style['valign']))
        if vertical:
            out['va'] = vertical
    if style.get('text_wrap'):
        out['wrap'] = 1
    if style.get('indent'):
        out['ind'] = int(style['indent'])
    out.update(_borders(style))
    return out


def _raw(sheet, rows, cols):
    """Each window cell's look before borders settle, rows × cols, 0-based."""
    raw = []
    for row in range(1, rows + 1):
        line = []
        for col in range(1, cols + 1):
            cell = sheet.cells.get((row, col))
            line.append(written_style(cell.style) if cell is not None else dict(DEFAULT))
        raw.append(line)
    for r1, c1, r2, c2 in sheet.merges:
        if r1 > rows or c1 > cols:
            continue
        head = sheet.cells.get((r1, c1))
        edges = {key: line for key, line in _borders(head.style if head else {}).items()}
        for row in range(r1, min(r2, rows) + 1):
            for col in range(c1, min(c2, cols) + 1):
                if (row, col) == (r1, c1):
                    continue
                merged = dict(DEFAULT)  # openpyxl's MergedCell, with the merge's outer borders on its edges
                for key, at_edge in (('bt', row == r1), ('bb', row == r2), ('bl', col == c1), ('br', col == c2)):
                    if at_edge and key in edges:
                        merged[key] = edges[key]
                raw[row - 1][col - 1] = merged
    return raw


def _merges(sheet, rows, cols):
    out = []
    for r1, c1, r2, c2 in sheet.merges:
        bottom, right = min(r2, rows), min(c2, cols)
        if r1 > bottom or c1 > right or (r1 == bottom and c1 == right):
            continue
        out.append([r1 - 1, c1 - 1, bottom - r1 + 1, right - c1 + 1])
    return out


def model_look(sheet, rows, cols):
    """`documents.sheet_look.look()`'s answer for the first `rows` × `cols` of the written tab (its module doc)."""
    merges = _merges(sheet, rows, cols)
    settled = _settled(_raw(sheet, rows, cols))
    covered = _cover(settled, merges) if settled else set()
    styles, index, cells = [{}], {(): 0}, []
    for r, line in enumerate(settled):
        ids = []
        for c, style in enumerate(line):
            if (r, c) in covered or not style:
                ids.append(0)
                continue
            key = tuple(sorted(style.items()))
            if key not in index:
                index[key] = len(styles)
                styles.append(style)
            ids.append(index[key])
        cells.append(ids)
    # A row set to Excel's default height is written as no height at all (XlsxWriter), and read back so.
    heights = [sheet.heights.get(row) for row in range(1, rows + 1)]
    heights = [height if height and height != DEFAULT_ROW_PT else None for height in heights]
    return {
        'styles': styles,
        'cells': cells,
        'merges': merges,
        'col_px': [sizes.col_px(sheet, col) for col in range(1, cols + 1)],
        'row_px': [round(height * sizes.PT_TO_PX) if height else None for height in heights],
        'default_row_px': DEFAULT_ROW_PX,
        'hidden_cols': [],
        'hidden_rows': [],
    }
