"""A tab's column widths and row heights as the written file carries them (plan.md §9.4; J116, J117): the sheet model
holds each width in characters as the file stores it, and the writer (`write._pixels`) sets the column in whole pixels,
as Excel draws it (a stored 46 draws at 322 pixels). The viewer measures with what the file holds, so its checks, its
grid and documents' `look()` of the written file agree. Pure.
"""

from ..workbook import styles as s

MAX_DIGIT_PX = 7  # Calibri 11's widest digit at 100%: the unit of a stored width
DEFAULT_COL_PX = 64  # a column no one sized (8.43 characters)
PT_TO_PX = 4 / 3


def stored_width(width):
    """The width the file stores for a column the model sized `width` characters wide: its whole pixels (the writer's
    `set_column_pixels`) back in characters, to 1/256 as XlsxWriter writes it."""
    if not width:
        return 0.0
    pixels = int(float(width) * MAX_DIGIT_PX + 0.5)
    return (pixels * 256 // MAX_DIGIT_PX) / 256


def col_px(sheet, col):
    """Column `col` (1-based) on screen at 100%, in pixels, as documents' look() reads the written file."""
    width = sheet.widths.get(col)
    if width is None:
        return DEFAULT_COL_PX
    return max(8, min(1200, round(stored_width(width) * MAX_DIGIT_PX)))


def row_pt(sheet, row):
    """Row `row` (1-based) in points: its own height, else Excel's default."""
    return float(sheet.heights.get(row) or s.DEFAULT_ROW_PT)


def extent(sheet):
    """(rows, cols) the written tab spans: its last cell or merge, at least one of each."""
    rows = [row for row, _col in sheet.cells] + [merge[2] for merge in sheet.merges]
    cols = [col for _row, col in sheet.cells] + [merge[3] for merge in sheet.merges]
    return max(rows, default=1), max(cols, default=1)
