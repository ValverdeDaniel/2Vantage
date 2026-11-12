"""Where Excel breaks a tab of the client spreadsheet into printed pages (plan.md §9.4; J117; old `workbook_pages.py`
at 891f1b3, D-194): each tab on letter paper as Excel prints it, from the print setup the tab wrote (`sheet.print`,
`workbook.print_plan`): the orientation, the margins, centred across, the page number in the footer, a set scale or Fit
To, the rows and columns repeated on every page and the manual breaks.

Excel measures a column for print with the printer's own type, so a column prints wider than it shows on screen:
`PRINT_WIDTH` is the writer's own constant (fitted 2026-11-05 to Excel's breaks), so the plan and this view cannot
drift apart. Another printer can differ by a few percent, so a tab that only just fits may break elsewhere there:
`near_edge` says so. Pure: the sheet model in, a dict out (0-based rows and columns). Reads no value.
"""

import math

from ..workbook.print_plan import PRINT_WIDTH
from . import sizes

PAGE_IN = (11.0, 8.5)  # letter, landscape
MIN_SCALE, MAX_SCALE = 10, 400
# Fit To over more than one page across: Excel settles below the tightest scale that fits (about 10% below), so its
# column breaks can fall a column or two differently from these.
FIT_WIDE_SLACK = 0.9
DEFAULT_WIDTH = 9.140625  # a column with no width of its own (8.43 characters), as stored


def _col_pt(stored, print_width):
    """A column of stored width `stored`, printed, in points at 100%: its whole pixels on screen times print_width."""
    px = math.floor(((256 * stored + math.floor(128 / sizes.MAX_DIGIT_PX)) / 256) * sizes.MAX_DIGIT_PX)
    return px * 0.75 * print_width


def _bands(sz, first, last, usable, titles, breaks):
    """Excel's page bands along one axis: (start, end) 1-based inclusive. A band holds what fits beside the repeated
    titles and ends at a manual break; a size wider than a page still gets a page of its own."""
    bands, start = [], first
    while start <= last:
        room = usable
        if titles and start > titles[1]:
            room -= sum(sz.get(i, 0) for i in range(titles[0], titles[1] + 1))  # a later page repeats the titles
        end, used = start, sz[start]
        while end < last and end not in breaks and used + sz[end + 1] <= room + 1e-6:
            end += 1
            used += sz[end]
        bands.append((start, end))
        start = end + 1
    return bands


def _area(sheet, setup):
    r1, c1, r2, c2 = setup.get('area') or (1, 1, *sizes.extent(sheet))
    return c1, r1, c2, r2


def _layout(sheet, setup, print_width, scale):
    portrait = not setup.get('landscape')
    page_w, page_h = (PAGE_IN[1], PAGE_IN[0]) if portrait else PAGE_IN
    left, right, top, bottom = setup.get('margins') or (0.7, 0.7, 0.75, 0.75)
    usable_w, usable_h = (page_w - left - right) * 72, (page_h - top - bottom) * 72
    c1, r1, c2, r2 = _area(sheet, setup)
    cols = {
        c: _col_pt(sizes.stored_width(sheet.widths[c]) if c in sheet.widths else DEFAULT_WIDTH, print_width)
        for c in range(1, c2 + 1)
    }
    rows = {r: sizes.row_pt(sheet, r) for r in range(1, r2 + 1)}
    title_rows, title_cols = setup.get('repeat_rows'), setup.get('repeat_cols')
    factor = scale / 100
    col_bands = _bands(
        {c: w * factor for c, w in cols.items()}, c1, c2, usable_w, title_cols, set(setup.get('col_breaks') or ())
    )
    row_bands = _bands(
        {r: h * factor for r, h in rows.items()}, r1, r2, usable_h, title_rows, set(setup.get('row_breaks') or ())
    )
    return col_bands, row_bands


def _fit_scale(sheet, setup, print_width):
    """The scale Fit To prints at: the largest whole percent (never over 100) at which the tab spans no more pages
    across than its width count and, when a height count is set, no more down."""
    wide, tall = (int(n) for n in setup['fit'])
    for scale in range(100, MIN_SCALE - 1, -1):
        col_bands, row_bands = _layout(sheet, setup, print_width, scale)
        if (not wide or len(col_bands) <= wide) and (not tall or len(row_bands) <= tall):
            return max(MIN_SCALE, int(scale * FIT_WIDE_SLACK)) if wide > 1 else scale
    return MIN_SCALE


def pages(sheet, print_width=PRINT_WIDTH):
    """How the tab prints: the scale, whether Fit To chose it, the repeated rows and columns (0-based, inclusive) and
    each page's rows and columns, numbered down then across as Excel numbers them. None for a tab with no setup."""
    setup = sheet.print
    if not setup:
        return None
    fit = bool(setup.get('fit'))
    scale = _fit_scale(sheet, setup, print_width) if fit else max(MIN_SCALE, min(MAX_SCALE, setup.get('scale') or 100))
    col_bands, row_bands = _layout(sheet, setup, print_width, scale)
    out = []
    for cols in col_bands:
        for rows in row_bands:
            out.append({'n': len(out) + 1, 'rows': [rows[0] - 1, rows[1] - 1], 'cols': [cols[0] - 1, cols[1] - 1]})
    left, right, top, bottom = setup.get('margins') or (0.7, 0.7, 0.75, 0.75)
    portrait = not setup.get('landscape')
    title_rows, title_cols = setup.get('repeat_rows'), setup.get('repeat_cols')
    return {
        'scale': int(scale),
        'fit': fit,
        'paper': {'w': PAGE_IN[1] if portrait else PAGE_IN[0], 'h': PAGE_IN[0] if portrait else PAGE_IN[1]},
        'margins': {'left': left, 'right': right, 'top': top, 'bottom': bottom, 'footer': 0.3},
        'centered': bool(setup.get('center_h')),
        'title_rows': [title_rows[0] - 1, title_rows[1] - 1] if title_rows else None,
        'title_cols': [title_cols[0] - 1, title_cols[1] - 1] if title_cols else None,
        'footer': 'page' if '&P' in str(setup.get('footer') or '') else None,
        'header': 'draft' if setup.get('header') else None,
        'print_width': print_width,
        'excel_picks': fit and int(setup['fit'][0] or 1) > 1,
        'pages': out,
    }


def print_summary(sheet):
    """The tab's printed pages (`pages`), and whether it is near the edge: a printer measuring columns 5% narrower or
    wider would break it elsewhere."""
    shown = pages(sheet)
    if shown is None:
        return None

    def breaks(found):
        return [(tuple(page['rows']), tuple(page['cols'])) for page in found['pages']]

    shown['near_edge'] = any(breaks(pages(sheet, PRINT_WIDTH * factor)) != breaks(shown) for factor in (0.95, 1.05))
    return shown
