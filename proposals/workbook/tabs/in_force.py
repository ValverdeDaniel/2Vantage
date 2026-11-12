"""A line kept as is: its current-coverage tab (plan.md §9.4 "in force"; J151, J47; old
`presentation_workbook._InForceSheet` at 891f1b3): a title band, the one sentence that says the line was not
marketed, and its stated in-force facts as label and value rows. Text only: nothing here is a formula or a number a
client could mistake for a quote.
"""

from .. import cells
from .. import print_plan as pp
from .. import styles as s
from .common import long_date

WIDTHS = (40, 70)
NOTE = 'This line is presented as currently in force; it was not sent to market this cycle.'
DATES = (
    ('effective_date', 'Effective'),
    ('renewal_date', 'Renews'),
    ('rate_guarantee_through', 'Rate guaranteed through'),
)


def facts(card):
    """[(label, text)]: the carrier, the funding and the three dates, in the old order."""
    found = []
    for key, label in (('carrier', 'Carrier'), ('funding', 'Funding')):
        text = str(card.get(key) or '').strip()
        if text:
            found.append((label, text))
    for key, label in DATES:
        value = card.get(key)
        text = long_date(value) or str(value or '').strip()
        if text:
            found.append((label, text))
    return found


def write(sheet, ctx, line):
    for col, width in enumerate(WIDTHS, 1):
        sheet.widths[col] = width
    cells.band(sheet, 1, 2, f'{line.label} — Current Coverage', size=s.TITLE_SIZE, height=24)
    cells.spacer(sheet, 2)
    cells.text(sheet, 3, 1, NOTE, font=s.ITALIC, align=s.LEFT)
    cells.merge_pair(sheet, 3, 1, 2)
    sheet.heights[3] = cells.row_height([(NOTE, 100)])
    last_row = 3
    found = facts(line.kept or {})
    if found:
        cells.spacer(sheet, 4)
        for row, (name, value) in enumerate(found, 5):
            cells.text(sheet, row, 1, name, font=s.BOLD, fill=s.FILL_WHITE, border=s.THIN, align=s.label_align(1))
            cells.text(sheet, row, 2, value, fill=s.FILL_WHITE, border=s.THIN, align=s.LEFT)
            sheet.heights[row] = cells.row_height([(name, 34), (value, 62)])
            last_row = row
    sheet.zoom = s.ZOOM
    pp.fitted(sheet, len(WIDTHS), last_row, draft=ctx.draft, best_fit=True)
