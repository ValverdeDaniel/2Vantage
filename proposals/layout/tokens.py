"""The client deck's look, in one place (plan.md §9.5; J139, J140, J142; old Vantage 891f1b3 `proposal_tokens.py`,
the Presentation format's values, and `proposal_furniture`'s inks). Data module.

Change a value here and the PDF and the PowerPoint follow: both are drawn from the frames `layout` records on this
page (16:9, 960 × 540 pt). Points throughout; y runs down from the page's top, as every recorded frame does.
"""

from pathlib import Path

# --- The page -------------------------------------------------------------------------------------------------------
DECK_SIZE = (960.0, 540.0)
PAGE_W, PAGE_H = DECK_SIZE
PAGE_MARGIN = 36.0
TITLE_TOP = 16.0
TITLE_HEIGHT = 38.0
TITLE_RULE_TOP = 56.0
BODY_TOP = 70.0
FOOTER_BAR = 26.0
# Room held back at a slide's foot: PowerPoint can wrap a cell onto a line the layout did not count, and a grown row
# must not reach the footer.
BODY_BOTTOM_SLACK = 12.0
BODY_X = PAGE_MARGIN
BODY_W = PAGE_W - 2 * PAGE_MARGIN
BODY_H = PAGE_H - BODY_TOP - FOOTER_BAR - 8 - BODY_BOTTOM_SLACK

# --- Type -----------------------------------------------------------------------------------------------------------
# Helvetica in the PDF, Arial in the PowerPoint: the same metrics, so PowerPoint wraps where the layout did (J142).
FONTS = {'regular': 'Helvetica', 'bold': 'Helvetica-Bold', 'italic': 'Helvetica-Oblique', 'family': 'Arial'}
# A line's baseline sits this many sizes below its top: the furniture's, as the old canvas drew it. A paragraph's
# text (a Text flowable, a table cell) sits one size below, as reportlab's Paragraph placed its first line in the old
# files (`height - fontSize` at 891f1b3); its frames carry `drop`.
BASELINE_DROP = 0.96
PARAGRAPH_DROP = 1.0
# A content page's title steps down from the largest to the smallest until it fits one line (J139).
TITLE_TYPE = (26, 16)
# One table per plan set on one page: it shrinks to the floor before it runs on (Daniel, 2026-11-02; J140).
TABLE_TYPE = {'cell': 12.0, 'compact': 11.0, 'floor': 8.0}
TYPE_STEP = 0.5
# A table's cell padding, above and below only (so it never changes a line count): roomiest first.
PADS = (3.5, 2.0, 1.2)
TIGHTEST_PAD = 0.8
# A benefit row is two lines of type at most, ideally one (Stephanie, the 2026-11-05 call).
MAX_ROW_LINES = 2
# A benefit cell longer than this moves to a numbered note under its table. Characters.
LONG_VALUE = 80
# Everything else's type: (size, leading).
TEXT = {
    'cover_title': (42, 48),
    'title': (28, 32),
    'sub': (11, 14),
    'intro': (14, 20),
    'section': (20, 24),
    'caption': (13, 16),
    'rec_name': (24, 29),
    'rationale': (13, 19),
    'note': (8, 10),
}
HEAD_NOTE = 10

# --- A plan table's columns -----------------------------------------------------------------------------------------
LABEL_W = 2.3 * 72
# A plan column never grows past this, so two plans do not stretch across the page.
MAX_COL = 3.6 * 72
COLUMNS = 6

# --- Colours --------------------------------------------------------------------------------------------------------
# The Vantage tool's own blues, which both files wear. `navy` follows the agency's brand colour at runtime; another
# brand gets `navy_dark` by darkening it (`furniture.palette`).
PRESENTATION = {
    'navy': '#173a63',
    'navy_dark': '#0f2d4f',
    'blue': '#2e6fc7',
    'logo_blue': '#3b82d6',
    'blue_bg': '#e8f0fb',
    'silver': '#c3c8d1',
    'zebra': '#f6f7f9',
    'footer': '#eef0f3',
    'current': '#f1f3f5',
    'draft': '#c1352e',
    'ink': '#1c2430',
    'ink2': '#5b6573',
    'hairline': '#e6e8ec',
}
WHITE = '#ffffff'
DEFAULT_BRAND = PRESENTATION['navy']

# --- Words every file carries ---------------------------------------------------------------------------------------
DISCLAIMER = 'Rates as quoted by each carrier and subject to final underwriting.'
# The standing paragraphs of "Important information", as a file that cannot recalculate states them (old
# `disclaimers.DOCUMENT`).
DOCUMENT_DISCLAIMERS = (
    'This comparison is an overview of the plans and rates the carriers quoted for this group, based on the '
    'information they were given. It is not a contract or a guarantee of coverage.',
    "Final rates and benefits depend on the final census, enrollment and participation, and on each carrier's "
    'underwriting approval. They may change before the plan year begins.',
    "Plan designs are summarized. Each carrier's Summary of Benefits and Coverage and policy documents describe the "
    'full benefits, and they govern where anything here differs.',
    'Rates are monthly. Totals are estimates from the enrollment shown.',
)

# --- Pictures and marks ---------------------------------------------------------------------------------------------
ASSETS = Path(__file__).resolve().parents[2] / 'assets' / 'images'
LOGO_ON_DARK = 'asset:logos/logo-on-dark.png'
LOGO_ON_LIGHT = 'asset:logos/logo-on-light.png'
MARK = 'asset:logos/mark.png'
MARK_GHOST = 'asset:logos/mark-ghost.png'
LOGO_RATIO = 900 / 220
GHOST_RATIO = 900 / 708
# Where a dark page's picture stands (x, y, w, h): a rounded frame on the right, the words on the ground beside it.
PICTURE_BOX = (PAGE_W - 384, 44.0, 348.0, PAGE_H - 88)
AGENDA_PANEL = 340.0
# The agenda's picture: the dark panel under its one-line heading and rule, to the page's edges.
AGENDA_PICTURE_TOP = 151.0
AGENDA_PICTURE_BOX = (0.0, AGENDA_PICTURE_TOP, AGENDA_PANEL, PAGE_H - AGENDA_PICTURE_TOP)
