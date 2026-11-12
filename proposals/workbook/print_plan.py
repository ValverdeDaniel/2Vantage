"""How each tab prints (plan.md §9.4 "Print"; J147, J148, J.6.11; old `presentation_styles` at 891f1b3): letter
landscape, a break before each carrier with the current plans repeated, the Compare tab five slots a page, Composite
Rates one card page a sheet of paper, the rest fitted to the width (and the height when that stays readable).

Excel measures a column for print with the printer's type, so it prints about 10% wider than it draws (PRINT_WIDTH);
every scale here plans with the printed width. Excel ignores manual breaks under Fit To, which is why the tabs with
breaks get a computed scale. The setups write `sheet.print`, which `write.py` applies.
"""

import math

from . import styles as s
from .cells import sheet_height_pt


def _px(width):
    """Pixels a column of this width draws at: truncate(width * 7 + 0.5)."""
    return int(width * 7 + 0.5)


A_IN = _px(s.LABEL_W) / 96  # 322 px: the label column
PAIR_IN = (_px(s.COUNT_W) + _px(s.RATE_W)) / 96  # 42 + 168 = 210 px: one plan's pair
PAGE_W_IN = 10.5  # letter landscape less 0.25 in margins
PAGE_H_IN = 7.0
PRINT_SAFETY = 0.97
PRINT_WIDTH = 1.10
PRINT_SCALE_FLOOR = 40
HEIGHT_FIT_MIN = 60  # fit one page's height only when that keeps the tab at this percent or more
USABLE_W_IN = PAGE_W_IN * PRINT_SAFETY
USABLE_H_IN = PAGE_H_IN * PRINT_SAFETY
MARGINS = (0.25, 0.25, 0.75, 0.75)  # left, right, top, bottom (inches)
TITLE_ROWS = (4, 6)  # Carrier, Plan, Package: on every page
LETTER = 1


def _floor(value):
    """floor() that reads a quotient a hair under a whole number as that whole number."""
    return math.floor(value + 1e-9)


def _clamp(value, lo, hi=100):
    return max(lo, min(hi, value))


def height_fit_scale(height_pt):
    """The scale (percent, floored) that fits `height_pt` points of sheet to one page's usable height."""
    return _floor(100 * USABLE_H_IN / (max(1.0, float(height_pt)) / 72))


def print_plan(lead, titles, groups, *, lo=PRINT_SCALE_FLOOR, height_pt=None):
    """Where a rates tab's column breaks go and its scale. `lead`: plan pairs before the first carrier group (the
    current plans and their priced versions); `titles`: the current plans (their pairs repeat on every page with
    column A); `groups`: the pair count of each carrier group after them. Page 1 holds A, the lead and group 1; each
    later page A, the titles and the next group, so each carrier starts a page beside the current plan; a group too
    wide for a page continues on a page of its own. With `height_pt`, the smaller of the width's and the height's
    scales wins when the height's keeps the tab readable (HEIGHT_FIT_MIN).
    → {'breaks': [last column before each break], 'scale', 'title_cols': (1, last), 'title_rows'}."""
    lead, titles = max(0, int(lead)), max(0, int(titles))
    a_in, pair_in = A_IN * PRINT_WIDTH, PAIR_IN * PRINT_WIDTH
    per_page = max(1, _floor((USABLE_W_IN / (lo / 100) - a_in) / pair_in))
    pages, placed, breaks = [lead], lead, []
    for index, size in enumerate(groups):
        remaining, first = int(size), True
        while remaining > 0:
            if index == 0 and first:
                take = min(max(1, per_page - lead), remaining)
                pages[0] += take
            else:
                take = min(max(1, per_page - titles), remaining)
                breaks.append(1 + 2 * placed)
                pages.append(titles + take)
            placed += take
            remaining -= take
            first = False
    widest = a_in + pair_in * max(pages)
    scale = _clamp(_floor(100 * USABLE_W_IN / widest), lo)
    if height_pt:
        fit = height_fit_scale(height_pt)
        if fit >= HEIGHT_FIT_MIN:
            scale = _clamp(min(scale, fit), lo)
    return {'breaks': breaks, 'scale': int(scale), 'title_cols': (1, 1 + 2 * titles), 'title_rows': TITLE_ROWS}


def columns_print_scale(widths, height_pt, *, lo=PRINT_SCALE_FLOOR):
    """The scale for a sheet whose printed page holds columns of these `widths` across (the Compare tab)."""
    width_in = max(1, sum(_px(width) for width in widths)) / 96 * PRINT_WIDTH
    scale = _clamp(_floor(100 * USABLE_W_IN / width_in), lo)
    fit = height_fit_scale(height_pt)
    if fit >= HEIGHT_FIT_MIN:
        scale = _clamp(min(scale, fit), lo)
    return int(scale)


def card_print_scale(widths, page_height_pt, *, lo=PRINT_SCALE_FLOOR):
    """Composite Rates: every card page is one printed page: the smaller of the width's and the tallest page's fit."""
    width_in = max(1, sum(_px(width) for width in widths)) / 96 * PRINT_WIDTH
    width_fit = _floor(100 * USABLE_W_IN / width_in)
    return int(_clamp(min(width_fit, height_fit_scale(page_height_pt)), lo))


def _page(sheet, last_col, last_row, draft):
    """What every tab's print shares: letter landscape, the margins, centred across, the page number in the footer,
    the print area to the last cell, no gridlines; a draft says so in its header (J102)."""
    sheet.print = {
        'landscape': True,
        'paper': LETTER,
        'margins': MARGINS,
        'center_h': True,
        'footer': '&C&P',
        'header': f'&C{draft}' if draft else '',
        'area': (1, 1, max(1, int(last_row)), max(1, int(last_col))),
        'gridlines': False,
        'fit': None,
        'scale': None,
        'repeat_rows': None,
        'repeat_cols': None,
        'col_breaks': [],
        'row_breaks': [],
    }
    return sheet.print


def fitted(sheet, last_col, last_row, *, draft='', fit_wide=1, title_cols=None, title_rows=None, best_fit=False):
    """The Cover, Markets Checked, a generic tab, All Plans: fit `fit_wide` pages across and as many down as needed;
    with `best_fit` (one page across) also one page tall when that keeps the tab readable."""
    setup = _page(sheet, last_col, last_row, draft)
    tall = 0
    if best_fit and int(fit_wide) <= 1 and height_fit_scale(sheet_height_pt(sheet, last_row)) >= HEIGHT_FIT_MIN:
        tall = 1
    setup['fit'] = (max(1, int(fit_wide)), tall)
    setup['repeat_cols'] = title_cols
    setup['repeat_rows'] = title_rows


def with_breaks(sheet, last_col, last_row, plan, *, draft=''):
    """A rates tab or the Compare tab, from `print_plan`: the computed scale, a manual break before each carrier (or
    every five slots), the title columns and rows repeated."""
    setup = _page(sheet, last_col, last_row, draft)
    setup['scale'] = int(plan['scale'])
    setup['repeat_rows'] = plan['title_rows']
    setup['repeat_cols'] = plan['title_cols']
    setup['col_breaks'] = sorted(plan['breaks'])


def card_pages(sheet, last_col, last_row, breaks, scale, *, draft=''):
    """Composite Rates: pages stacked down the sheet, a manual row break after each, at a computed scale."""
    setup = _page(sheet, last_col, last_row, draft)
    setup['scale'] = int(scale)
    setup['row_breaks'] = sorted(breaks)
