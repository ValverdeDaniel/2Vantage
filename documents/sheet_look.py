"""How one window of a sheet looks in Excel: `look(workbook, sheet, start, rows, cols)` (plan.md §3.1, O.3.5; E29,
D-167, D-194; OQ25). Pure over an openpyxl workbook already open in full mode: an uploaded file the sheet viewer
loaded (`sheets.window`), or the client spreadsheet the Export viewer builds in memory and never saves (slice 33).

    {styles: [{}, {...}], cells: [[style index per cell]], merges: [[r, c, rows, cols]], col_px, row_px,
     default_row_px, hidden_cols, hidden_rows}

`styles[0]` is no look; `cells` has the shape of the window's rows; merges, hidden rows and hidden columns are
window-relative, and what Excel hides is reported so the viewer greys it (OQ25). It never reads a cell's value.
"""

from .sheet_style import cell_style, theme_palette

DEFAULT_COL_WIDTH = 9.14  # Excel's default column, as stored (8.43 characters plus padding)
PX_PER_WIDTH = 7  # pixels per character of a stored width (Calibri 11)
PT_TO_PX = 4 / 3
EDGES = ('bt', 'br', 'bb', 'bl')


def _width_px(width):
    return max(8, min(1200, round(width * PX_PER_WIDTH)))


def _columns(sheet, n_cols):
    """(col_px, hidden_cols) for the first n_cols columns. A stored dimension may span several columns (min..max)."""
    from openpyxl.utils import column_index_from_string

    default = sheet.sheet_format.defaultColWidth or DEFAULT_COL_WIDTH
    widths, hidden = {}, set()
    for key, dim in list(sheet.column_dimensions.items()):
        try:
            lo = dim.min or column_index_from_string(key)
        except ValueError:
            continue
        for col in range(lo, min(dim.max or lo, n_cols) + 1):
            if dim.width:
                widths[col] = dim.width
            if dim.hidden:
                hidden.add(col - 1)
    return [_width_px(widths.get(col) or default) for col in range(1, n_cols + 1)], sorted(hidden)


def _rows(sheet, start, n_rows):
    """(row_px, hidden_rows, default_row_px): heights for the window's rows (None = the sheet's default)."""
    row_px, hidden = [], []
    dims = sheet.row_dimensions
    for i in range(n_rows):
        dim = dims.get(start + 1 + i)  # .get: indexing would add a row
        height = getattr(dim, 'height', None) if dim is not None else None
        row_px.append(round(height * PT_TO_PX) if height else None)
        if dim is not None and dim.hidden:
            hidden.append(i)
    return row_px, hidden, round((sheet.sheet_format.defaultRowHeight or 15) * PT_TO_PX)


def _merges(sheet, start, n_rows, n_cols):
    """[[r, c, rows, cols]], window-relative, each clipped to the window."""
    top_row, last_row = start + 1, start + n_rows
    out = []
    for rng in sheet.merged_cells.ranges:
        top, bottom = max(rng.min_row, top_row), min(rng.max_row, last_row)
        left, right = max(rng.min_col, 1), min(rng.max_col, n_cols)
        if top > bottom or left > right or (top == bottom and left == right):
            continue
        out.append([top - top_row, left - 1, bottom - top + 1, right - left + 1])
    return out


def _raw_looks(sheet, palette, start, n_rows, n_cols):
    by_style, looks = {}, []
    if not (n_rows and n_cols):
        return looks
    for row in sheet.iter_rows(min_row=start + 1, max_row=start + n_rows, min_col=1, max_col=n_cols):
        line = []
        for cell in row:
            key = cell.style_id
            if key not in by_style:
                by_style[key] = cell_style(cell, palette)
            line.append(by_style[key])
        looks.append(line)
    return looks


def _settled(raw):
    """Borders between neighbours: Excel may store the line under A1 as A1's bottom or A2's top. Each cell draws its
    right and bottom edge (the first row and column also their top and left), so a line is drawn once."""

    def edge(r, c, key):
        return raw[r][c].get(key) if 0 <= r < len(raw) and 0 <= c < len(raw[r]) else None

    out = []
    for r, line in enumerate(raw):
        row = []
        for c, style in enumerate(line):
            cell = {k: v for k, v in style.items() if k not in EDGES}
            bottom, right = style.get('bb') or edge(r + 1, c, 'bt'), style.get('br') or edge(r, c + 1, 'bl')
            if bottom:
                cell['bb'] = bottom
            if right:
                cell['br'] = right
            if r == 0 and style.get('bt'):
                cell['bt'] = style['bt']
            if c == 0 and style.get('bl'):
                cell['bl'] = style['bl']
            row.append(cell)
        out.append(row)
    return out


def _cover(settled, merges):
    """A merge draws as its top-left cell, with the edges of its far cells; the cells it covers draw nothing."""
    covered = set()
    for r, c, rs, cs in merges:
        head = settled[r][c]
        far_right, far_bottom = settled[r][c + cs - 1].get('br'), settled[r + rs - 1][c].get('bb')
        head.pop('br', None)
        head.pop('bb', None)
        if far_right:
            head['br'] = far_right
        if far_bottom:
            head['bb'] = far_bottom
        covered.update((i, j) for i in range(r, r + rs) for j in range(c, c + cs) if (i, j) != (r, c))
    return covered


def look(book, sheet_name, start, n_rows, n_cols):
    """The look of rows start..start+n_rows and the first n_cols columns of one sheet (see the module doc)."""
    sheet = book[sheet_name]
    palette = theme_palette(book)
    col_px, hidden_cols = _columns(sheet, n_cols)
    row_px, hidden_rows, default_row_px = _rows(sheet, start, n_rows)
    merges = _merges(sheet, start, n_rows, n_cols)
    settled = _settled(_raw_looks(sheet, palette, start, n_rows, n_cols))
    covered = _cover(settled, merges) if settled else set()
    styles, index, cells = [{}], {(): 0}, []
    for r, row in enumerate(settled):
        ids = []
        for c, style in enumerate(row):
            if (r, c) in covered or not style:
                ids.append(0)
                continue
            key = tuple(sorted(style.items()))
            if key not in index:
                index[key] = len(styles)
                styles.append(style)
            ids.append(index[key])
        cells.append(ids)
    return {
        'styles': styles,
        'cells': cells,
        'merges': merges,
        'col_px': col_px,
        'row_px': row_px,
        'default_row_px': default_row_px,
        'hidden_cols': hidden_cols,
        'hidden_rows': hidden_rows,
    }
