"""The stop-loss workbook's look and geometry (plan.md §9.13; J166; the old pipeline/workbooks.py `_sl_*` helpers at
891f1b3): its own sheet style, not the client spreadsheet's (Calibri 11, a navy title, light section bands, tinted
inputs, #,##0 money), and the row numbers of its two analysis tabs as functions of one integer, the laser rows.

Formulas need fixed addresses; the laser block grows, so each tab's rows are worked out from its size (`snapshot_rows`,
`option_rows`). Every formula goes through the closed grammar with this file's own tab titles (`TITLES`); its stored
result is quotes' exact figure (rule 5), so a viewer that does not calculate shows the app's numbers.
"""

from .. import grammar
from ..model import BLANK, FORMULA, NUMBER, TEXT, Cell, column_letter

SNAPSHOT = 'In-Force Snapshot'
OPTIONS = 'Option Comparison'
NOTES = 'Binding Notes'
GLOSSARY = 'Glossary'
FIE = 'FIE Rates'
TITLES = frozenset((SNAPSHOT, OPTIONS, NOTES, GLOSSARY, FIE))

NAVY = '#173A63'
LIGHT = '#EEF2F7'
INPUT_FILL = '#FFF8E1'
NOTE_GREY = '#9AA3B0'
MONEY = '#,##0'
CENTS = '#,##0.00'
ZOOM = 100

BOLD = {'bold': True}
NAVY_BOLD = {'bold': True, 'font_color': NAVY}
TITLE = {'bold': True, 'font_size': 13, 'font_color': NAVY}
NOTE = {'font_size': 9, 'font_color': NOTE_GREY}
WRAP = {'text_wrap': True}
NOTE_COL = 8

ROUNDTRIP_NOTE = (
    'This sheet is a live model: the tinted cells are inputs and every total is a formula. Edits here do NOT flow back '
    'into the deal — change the numbers in the app and download again to share them.'
)


def ref(cell):
    """A reference into the snapshot, quoted: its title has a space and a hyphen."""
    return f'{grammar.sheet_ref(SNAPSHOT)}{cell}'


def _fill(color):
    return {'pattern': 1, 'bg_color': color}


def put(sheet, row, col, value, style=None):
    """A plain cell as the old sheet wrote one: text or a number, no number format of its own."""
    if value is None or value == '':
        return None
    if isinstance(value, str):
        return sheet.put(row, col, Cell(TEXT, value, style=dict(style or {})))
    return sheet.put(row, col, Cell(NUMBER, value, style=dict(style or {})))


def text(sheet, row, col, value):
    """A typed value nothing references: the value, or an em dash when blank, kept text after an edit in Excel."""
    shown = value if value not in (None, '') else '—'
    return sheet.put(row, col, Cell(TEXT, str(shown), style={'quote_prefix': True}))


def number(value):
    """An input as the sheet stores it: the figure to the cent, or None for a blank cell."""
    if value is None:
        return None
    rounded = round(float(value), 2)
    return int(rounded) if rounded == int(rounded) else rounded


def input_cell(sheet, row, col, amount, cents=False, note=None):
    """A typed carrier value, or an EMPTY tinted cell (never a dash: text breaks every formula that reads it); the
    reason a cell is blank goes to the notes column."""
    style = {'num_format': CENTS if cents else MONEY, **_fill(INPUT_FILL)}
    figure = number(amount)
    sheet.put(row, col, Cell(BLANK, style=style) if figure is None else Cell(NUMBER, figure, style=style))
    if note:
        put(sheet, row, NOTE_COL, note, NOTE)


def formula(sheet, row, col, template, value, cents=False, bold=False, num=True):
    """A formula of ours with its stored result: a number, '' (the formula's own blank) or a text."""
    grammar.check(template, TITLES)
    style = {'num_format': CENTS if cents else MONEY} if num else {}
    if bold:
        style.update(BOLD)
    sheet.put(row, col, Cell(FORMULA, template, _result(value), style=style))


def link(sheet, row, col, template, value):
    """A bare formula link (=$C$13), General, as the old sheet wrote one."""
    formula(sheet, row, col, template, value, num=False)


def _result(value):
    if value is None or value == '':
        return ''
    if isinstance(value, str):
        return value
    figure = float(value)
    return int(figure) if figure == int(figure) else figure


def title(sheet, words):
    put(sheet, 1, 2, words, TITLE)


def section(sheet, row, words, span=6):
    """A light band from column B, its words navy bold."""
    for col in range(2, 2 + span):
        sheet.put(row, col, Cell(BLANK, style=_fill(LIGHT)))
    sheet.put(row, 2, Cell(TEXT, words, style={**NAVY_BOLD, **_fill(LIGHT)}))


def headings(sheet, row, words, start=2):
    for offset, word in enumerate(words):
        put(sheet, row, start + offset, word, BOLD)


def widths(sheet, pairs):
    for letter, width in pairs:
        sheet.widths[_column(letter)] = width


def _column(letter):
    out = 0
    for ch in letter:
        out = out * 26 + ord(ch) - 64
    return out


def letter(col):
    return column_letter(col)


def snapshot_rows(laser_rows):
    """The In-Force Snapshot's rows (the old `_sl_snapshot_map`)."""
    first = 33
    last = first + laser_rows - 1
    total = last + 1
    band_d = total + 2
    admin = band_d + 2
    return {
        'CARRIER': 3, 'PLAN': 4, 'TPA': 5, 'TPA_GUAR': 6, 'BASIS': 7, 'RUNIN': 8, 'RUNIN_LIM': 9, 'RUNOUT': 10,
        'TLO': 11, 'COLLATERAL': 12, 'HC': 13, 'MO': 14,
        'BAND_A': 16, 'HEAD_A': 17, 'SPEC': 18, 'AGG': 19, 'LOAD': 20, 'PREM': 21,
        'BAND_B': 23, 'SPEC_DED': 24, 'FACTOR': 25, 'CORRIDOR': 26, 'ATT_PEPM': 27, 'FLOOR': 28, 'ATT_FINAL': 29,
        'BAND_C': 31, 'HEAD_C': 32, 'LASER_FIRST': first, 'LASER_LAST': last, 'LASER_TOT': total,
        'BAND_D': band_d, 'HEAD_D': band_d + 1, 'ADMIN': admin, 'FIXED': admin + 1, 'EXPECTED': admin + 2,
        'PROJECTED': admin + 3, 'ATTACH': admin + 4, 'LASERS': admin + 5, 'MAL': admin + 6, 'NOTE': admin + 8,
    }  # fmt: skip


def option_rows(laser_rows):
    """Option Comparison's rows (the old `_sl_comparison_map`)."""
    first = 37
    last = first + laser_rows - 1
    liability = last + 1
    band_cost = liability + 3
    return {
        'CENSUS': 4, 'HEAD': 6, 'CARRIER': 7, 'TPA': 8, 'BASIS': 9, 'RUNIN': 10, 'RUNIN_LIM': 11, 'RUNOUT': 12,
        'TLO': 13, 'SPEC_DED': 14, 'BAND_PREM': 16, 'SPEC_RATE': 17, 'AGG_RATE': 18, 'LOAD': 19, 'PREM_PEPM': 20,
        'PREM_ANN': 21, 'BAND_AGG': 23, 'FACTOR': 24, 'CORRIDOR': 25, 'FLOOR': 26, 'ATT_PEPM': 27, 'ATT_ANN': 28,
        'BAND_ADMIN': 30, 'ADMIN': 31, 'ADMIN_ANN': 32, 'BAND_LASER': 34, 'LASER_NOTE': 35, 'HEAD_LASER': 36,
        'LASER_FIRST': first, 'LASER_LAST': last, 'LASER_LIAB': liability, 'LASER_CNT': liability + 1,
        'BAND_COST': band_cost, 'PROJECTED': band_cost + 1, 'MAL': band_cost + 2, 'VS_MAL': band_cost + 3,
        'VS_PREM': band_cost + 4, 'VS_LASER': band_cost + 5, 'NOTE': band_cost + 6, 'PREFERRED': band_cost + 8,
        'WHY': band_cost + 9,
    }  # fmt: skip


def laser_label(n):
    """A laser row's name: its position, never a claimant (OQ104)."""
    return f'Laser {n}'
