"""The Markets Checked tab (plan.md §9.4; J146, J63; old `presentation_workbook._MarketsSheet` at 891f1b3): who was
asked and what came back, line by line, as Carrier, Status and Notes, when the proposal shows it. The rows are the
client's: a carrier hidden on Markets checked never reaches them (J154), and each status names the line's tab.
"""

from .. import cells
from .. import print_plan as pp
from .. import styles as s

WIDTHS = (33, 45, 67)
CURRENT = 'Current carrier'
ILLUSTRATED = 'Benefit & Premium Illustration'
NOT_PRESENTED = 'Quoted — not presented'
DECLINED = 'Declined to Quote'


def status(entry, tab):
    """(status, notes) of one carrier row, in the firm's words: the incumbent, a quote on the proposal (pointing at
    the line's tab), a quote left off it, or a decline with its note in brackets."""
    note = str(entry.get('note') or '').strip()
    if entry.get('current'):
        return CURRENT, note
    if entry.get('quoted') is True:
        if entry.get('presented'):
            return (f'{ILLUSTRATED} — see {tab}' if tab else ILLUSTRATED), note
        return NOT_PRESENTED, note
    if entry.get('quoted') is False:
        return (f'{DECLINED} ({note})' if note else DECLINED), ''
    return '', note


def write(sheet, ctx):
    tabs = {**ctx.layout.compare, **ctx.layout.line_tab}
    for col, width in enumerate(WIDTHS, 1):
        sheet.widths[col] = width
    cells.band(sheet, 1, 3, 'Markets Checked', size=s.TITLE_SIZE, height=24)
    cells.spacer(sheet, 2)
    row, last_row = 3, 1
    for line in ctx.facts.markets['lines']:
        cells.band(sheet, row, 3, line['label'])
        for col, word in enumerate(('Carrier', 'Status', 'Notes'), 1):
            cells.text(sheet, row + 1, col, word, font=s.BOLD, fill=s.FILL_SUBHEAD, border=s.THIN, align=s.CENTER)
        sheet.heights[row + 1] = s.ROW_H
        row += 2
        for entry in line['rows']:
            carrier = str(entry.get('carrier') or '').strip()
            said, note = status(entry, tabs.get(line['key']))
            for col, text, align in ((1, carrier, s.label_align(1)), (2, said, s.LEFT), (3, note, s.LEFT)):
                cells.text(sheet, row, col, text, fill=s.FILL_WHITE, border=s.THIN, align=align)
            sheet.heights[row] = cells.row_height([(carrier, 30), (said, 40), (note, 60)])
            last_row = row
            row += 1
        cells.spacer(sheet, row)
        row += 1
    sheet.zoom = s.ZOOM
    pp.fitted(sheet, len(WIDTHS), last_row, draft=ctx.draft, best_fit=True)
