"""The client spreadsheet's look, as data (plan.md §9.4; J145–J152; old `presentation_styles.py` at 891f1b3): colours,
type, number formats, heights and widths, and the cell styles every tab composes. A data module: nothing here
computes a figure.

A style is a dict of XlsxWriter format properties; `style(...)` merges the pieces a cell wears (a font, a fill, a
border, an alignment, a number format) into one, which the writer turns into a format once per distinct dict.
"""

# --- Colours (hex, no alpha) ---------------------------------------------------------------------------------------
NAVY = '#002060'
SUBHEAD = '#8EB2D7'
SOLD_GREEN = '#00B050'
INPUT_BLUE = '#0000FF'
INPUT_FILL = '#FFF8E1'
WHITE = '#FFFFFF'
# The Compare tab's Bryke palette: light-blue labels and inputs, alternating grey rows, green rates and totals, and
# the two base highlights.
LABEL_BLUE = '#DDEBF7'
ROW_GREY = '#F2F2F2'
RATE_GREEN = '#E2EFDA'
CURRENT_GREEN = '#C6EFCE'
RENEWAL_AMBER = '#FFEB9C'
LINK_BLUE = '#0563C1'

# --- Type -----------------------------------------------------------------------------------------------------------
FONT_NAME = 'Arial'
FONT_SIZE = 11
TITLE_SIZE = 14
COVER_NAME_SIZE = 20
COVER_TITLE_SIZE = 26
# The Compare and Composite Rates tabs' density (Bryke's): 9 pt type on 15 pt rows.
COMPACT_SIZE, COMPACT_TITLE = 9, 12
COMPACT_ROW_H, COMPACT_LINE_PT = 15, 12

# --- Number formats -------------------------------------------------------------------------------------------------
MONEY_WHOLE = '"$"#,##0_);[Red]("$"#,##0)'
MONEY_CENTS = '"$"#,##0.00_);[Red]("$"#,##0.00)'
RATE_3DP = '"$"#,##0.000_);[Red]("$"#,##0.000)'
RATE_4DP = '"$"#,##0.0000_);[Red]("$"#,##0.0000)'
# A rate looked up from whichever plan a drop-down names: two to four decimals, as the plan stored them.
RATE_FLEX = '"$"#,##0.00##_);[Red]("$"#,##0.00##)'
PCT = '0%'
PCT_1DP = '0.0%'
PCT_2DP = '0.00%'
CHANGE = '[Red]+0.0%;[Color10]-0.0%;0.0%'
# The Compare tab's two halves of a % row, the words inside the cell as Bryke prints them (no formula holds a string).
CHANGE_EE_ONLY = '[Red]"EE Only: "+0.0%;[Color10]"EE Only: "-0.0%;"EE Only: "0.0%'
CHANGE_TOTAL = '[Red]"Total: "+0.0%;[Color10]"Total: "-0.0%;"Total: "0.0%'
CHANGE_MONEY = '[Red]+"$"#,##0;[Color10]-"$"#,##0;"$"0'
COUNT = '0'
TEXT = '@'
GENERAL = 'General'
NUMBER_FORMATS = frozenset(
    {
        MONEY_WHOLE,
        MONEY_CENTS,
        RATE_3DP,
        RATE_4DP,
        RATE_FLEX,
        PCT,
        PCT_1DP,
        PCT_2DP,
        CHANGE,
        CHANGE_EE_ONLY,
        CHANGE_TOTAL,
        CHANGE_MONEY,
        COUNT,
        TEXT,
        GENERAL,
    }
)

# --- Heights (points) and widths (characters) -----------------------------------------------------------------------
ROW_H = 20
SPACER_H = 9.75
MAX_ROW_H = 409  # Excel's limit is 409.5
LINE_PT = 15  # one wrapped line of Arial 11
DEFAULT_ROW_PT = 15  # a row with no explicit height
LABEL_W = 46
COUNT_W = 6
RATE_W = 24
GENERIC_W = 30
ZOOM = 130
COMPARE_ZOOM = 110


# --- Pieces ---------------------------------------------------------------------------------------------------------
def font(size=FONT_SIZE, *, bold=False, italic=False, color=None, underline=False):
    """An Arial font: every cell with a value or a fill uses this family."""
    out = {'font_name': FONT_NAME, 'font_size': size}
    if bold:
        out['bold'] = True
    if italic:
        out['italic'] = True
    if color:
        out['font_color'] = color
    if underline:
        out['underline'] = 1
    return out


def fill(color):
    return {'pattern': 1, 'bg_color': color}


def label_align(indent=1):
    """A row label: left, wrapped, indented (1 by default, 2 for an Rx tier)."""
    out = {'align': 'left', 'valign': 'vcenter', 'text_wrap': True}
    if indent:
        out['indent'] = indent
    return out


BODY = font()
BOLD = font(bold=True)
ITALIC = font(italic=True)
BOLD_ITALIC = font(bold=True, italic=True)
WHITE_BOLD = font(bold=True, color=WHITE)
INPUT = font(color=INPUT_BLUE)
SOLD = font(bold=True, color=SOLD_GREEN)
RECOMMENDED = font(bold=True, color=NAVY)
COVER_NAME = font(COVER_NAME_SIZE, bold=True)
COVER_AGENCY = font(COVER_NAME_SIZE, bold=True, color=NAVY)
COVER_TITLE = font(COVER_TITLE_SIZE)
COMPACT = {
    'body': font(COMPACT_SIZE),
    'bold': font(COMPACT_SIZE, bold=True),
    'italic': font(COMPACT_SIZE, italic=True),
    'bold_italic': font(COMPACT_SIZE, bold=True, italic=True),
    'white': font(COMPACT_SIZE, bold=True, color=WHITE),
    'navy': font(COMPACT_SIZE, bold=True, color=NAVY),
    'input': font(COMPACT_SIZE, color=INPUT_BLUE),
    'pick': font(COMPACT_SIZE, bold=True, color=INPUT_BLUE),
    'title': font(COMPACT_TITLE, bold=True),
    'link': font(COMPACT_SIZE, color=LINK_BLUE, underline=True),
}

FILL_WHITE = fill(WHITE)
FILL_NAVY = fill(NAVY)
FILL_SUBHEAD = fill(SUBHEAD)
FILL_INPUT = fill(INPUT_FILL)
FILL_LABEL = fill(LABEL_BLUE)
FILL_GREY = fill(ROW_GREY)
FILL_GREEN = fill(RATE_GREEN)
# A conditional format's fill: its background colour.
HIGHLIGHT_CURRENT = {'bg_color': CURRENT_GREEN}
HIGHLIGHT_RENEWAL = {'bg_color': RENEWAL_AMBER}

THIN = {'border': 1}
TOTAL = {'left': 1, 'right': 1, 'top': 2, 'bottom': 2}

CENTER = {'align': 'center', 'valign': 'vcenter', 'text_wrap': True}
LEFT = {'align': 'left', 'valign': 'vcenter', 'text_wrap': True}
LEFT_TOP = {'align': 'left', 'valign': 'top', 'text_wrap': True}
PLAIN_LEFT = {'align': 'left', 'valign': 'vcenter'}  # no wrap: a header line runs on across the columns

UNLOCKED = {'locked': False}


def style(*, font=None, fill=None, border=None, align=None, num=None, extra=None):
    """One cell's format properties: the pieces merged, the font Arial 11 by default."""
    out = dict(BODY if font is None else font)
    for piece in (fill, border, align, extra):
        if piece:
            out.update(piece)
    if num is not None:
        out['num_format'] = num
    return out


def rate_format(places):
    """The number format for a rate with this many stored decimals: two or fewer is cents, three and four their own."""
    if places >= 4:
        return RATE_4DP
    return RATE_3DP if places == 3 else MONEY_CENTS


def pct_format(places):
    """The number format for a stored percentage shown with this many decimals (at most two)."""
    return (PCT, PCT_1DP, PCT_2DP)[max(0, min(2, places))]
