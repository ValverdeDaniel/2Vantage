"""Where each answer goes on Florida Blue's own printed form (G125). A data module, exempt from the 300-line rule.

Hand-derived, not generated (old Vantage's docstring called it generated, and no generator ever existed: P13). The
rectangles were measured from the bundled flat blank, `assets/questionnaires/fl_blue_51_blank_v9.pdf`, by walking its
content streams: every gray input box is a filled rectangle, every yes/no is a 10x10 square, and the labels carry
absolute text matrices. `BLANK_SHA256` is the hash of the blank these numbers were measured on; the start-up check
(`questionnaire/checks.py`) compares it with the bundled file, so a re-bundled carrier revision fails loudly instead of
stamping into empty space. The stamping itself is slice 43's (G57). Ported from old Vantage 891f1b3
(`benefits/questionnaires/fl_blue_51_layout.py`).

Coordinates are PDF points from the bottom-left of a 612x792 page, in the `(page_index, x, y, w, h)` shape reportlab
and pypdf both speak. Field keys are the carrier's own XFA names, the same ones `fl_blue_51.py` uses.
"""

BLANK_FILE = 'fl_blue_51_blank_v9.pdf'
BLANK_SHA256 = 'cdf087badfcb90873c6256938e1825acb21689431a6bc8595c380f66bb6a3286'

PAGE_COUNT = 2
PAGE_SIZE = (612.0, 792.0)

# The exact CMYK the form fills its input boxes with (`.10855 .083223
# .083223 0 k`). Redrawing a box in this colour before stamping erases the
# default the carrier baked into the print — "Florida", "Comparing Benefits
# & Rates" — without leaving a visible patch.
BOX_CMYK = (0.10855, 0.083223, 0.083223, 0.0)

# The carrier draws every caption and every baked-in value in embedded
# ArialMT at 9.5pt (its XFA template declares `<font typeface="Arial"
# size="9.5pt"/>` on all 73 value fields, and `QuestionnaireStampTests`
# re-reads that declaration and pins FONT_SIZE to it). We stamp in the same
# size and in a metric-compatible embedded face, so a stamped value is
# typographically indistinguishable from the caption printed beside it.
#
# Why not the carrier's own font: its embedded ArialMT is a SUBSET missing
# `$ % J K X` and the em dash (Arial-Bold carries only 23 glyphs), so drawing
# through it would silently blank every premium and percentage. Arial itself
# is Monotype-licensed and cannot ship in this repo. Arimo is Google's
# Arial-metric face (SIL OFL, bundled beside the carrier PDFs with its
# licence): identical advance widths, so the carrier's own spacing is
# preserved exactly, and reportlab embeds a subset just as the carrier's file
# does.
FONT_FILE = 'Arimo.ttf'
FONT_NAME = 'FLBlueSans'
FONT_SIZE = 9.5
MIN_FONT_SIZE = 6.0
# 1.2 x the type size — the line spacing the carrier's own wrapped captions
# use, and what every wrapped block on the page is measured against.
LEADING = 11.4

# Scalar fields that own a printed input box.
FIELD_BOXES = {
    # Section I — General Information
    'txtCoName': (0, 126.5, 660.5, 293.6, 12.3),
    'dteAnnivDate': (0, 527.7, 660.5, 63.5, 12.3),
    'txtBusAdd': (0, 125.0, 642.5, 178.2, 12.4),
    'txtAdd2': (0, 428.9, 642.5, 162.3, 12.4),
    'City': (0, 60.3, 624.5, 242.8, 12.4),
    'State': (0, 345.3, 624.5, 119.9, 12.4),
    'ZipCode': (0, 530.1, 624.5, 61.1, 12.4),
    'drpSIC': (0, 82.6, 585.0, 61.4, 18.0),
    'drpSICDesc': (0, 225.1, 587.8, 186.1, 12.4),
    'TextField2': (0, 455.8, 587.8, 135.4, 12.3),
    # Section II — Health Coverage History
    'numTAP': (0, 483.8, 550.4, 107.3, 12.3),
    'numCurrentCarrierEligCount': (0, 244.4, 532.4, 85.8, 12.3),
    'drpNumCarr': (0, 447.3, 496.4, 143.8, 12.3),
    'txtRsnBid': (0, 179.7, 478.4, 411.4, 12.3),
    # Section III — Current Health Carrier Information
    'txtCurrentCarrier': (0, 131.8, 411.2, 189.3, 16.5),
    'drpEEContMethod': (0, 172.9, 389.1, 148.3, 16.5),
    # Section V — Applicant Signatures (page 2)
    'txtgrprepname': (1, 20.8, 415.2, 237.3, 14.4),
    'txtTitleOfficer': (1, 20.8, 379.4, 237.3, 15.0),
    'txtagentname': (1, 20.8, 346.5, 237.3, 15.0),
    'txtAgencyName': (1, 20.8, 310.6, 237.3, 14.9),
}

# Yes/No pairs. The carrier draws each as two 10x10 squares.
CHECKBOXES = {
    'chkFBPrior': {'Yes': (0, 56.6, 515.5, 10.0, 10.0),
                   'No': (0, 109.0, 515.5, 10.0, 10.0)},
    'chkVirgin': {'Yes': (0, 57.2, 438.3, 10.0, 10.0),
                  'No': (0, 109.0, 438.3, 10.0, 10.0)},
    'chkMedCon': {'Yes': (0, 55.0, 160.3, 10.0, 10.0),
                  'No': (0, 109.0, 160.3, 10.0, 10.0)},
}

# Repeating blocks: how many rows the printed form actually shows, and where
# row 1's fields sit. Everything past this goes to the attachment.
PRINTED_ROWS = {'plans': 1, 'conditions': 1}

BLOCK_BOXES = {
    'conditions': {
        'drpMedCat': (1, 47.2, 723.9, 148.0, 16.9),
        'numNumEEMedCon': (1, 299.9, 701.3, 58.6, 19.8),
        'numCancerDetailyes': (1, 299.9, 675.6, 57.3, 21.4),
        'num_CancerDetailsno': (1, 299.9, 648.5, 57.3, 21.4),
    },
    # Section III's plan grid. These aren't rectangles in the stream — the
    # form draws each as a beveled border built from two L-shaped paths
    # (`q 1 0 0 1 x y cm 0 0 m w 0 l … 0 -h l f Q`), so the corner comes from
    # the translate and the size from the path. Anchoring to the labels
    # instead put every value 25-50pt left of its box.
    'plans': {
        'txtCurrPlanName': (0, 225.5, 338.4, 158.6, 16.5),
        'dteCurrCarrEffDt': (0, 516.8, 338.4, 65.4, 16.5),
        'numCurrRatePrem': (0, 249.7, 311.4, 71.5, 16.5),
        'numRenPrem': (0, 518.3, 311.4, 63.9, 16.5),
    },
}

# Boxes the form draws white rather than gray. They hold no baked-in default,
# so nothing needs covering — and repainting them gray would be visible.
NO_COVER = frozenset({
    'txtCurrPlanName', 'dteCurrCarrEffDt', 'numCurrRatePrem', 'numRenPrem',
})

# Free-text answers that wrap inside an open area rather than a box.
# Shape: (page, x, FIRST BASELINE y, width, drop) — `drop` is the room below
# that first baseline, so the number of lines is 1 + drop // LEADING.
# The comments box is a real (white) rect: 19.4 560.6 573.2 46.4, i.e. it
# spans y 560.6-607.0; the first baseline sits one line-height under its top
# and the last has to keep its descenders inside.
TEXT_AREAS = {
    'txtMcComments': (1, 23.0, 596.0, 566.0, 34.0),
}

# The narrative the carrier reveals under a cancer row's counts. `txtMedIll`
# is gated on `numCancerDetailyes > 0`, so it can only appear while the
# `cancer_counts` effect is on — which is exactly when EFFECT_AREA is NOT
# repainted. The bare paper right of the count boxes (they end at x 358.6) is
# therefore always free when this is needed: no run of the carrier's own text
# reaches past x 292 between y 640 and 725, and the row's inline dropdowns sit
# at y 723.9. Same (first baseline, drop) shape as TEXT_AREAS.
NARRATIVE_AREA = (1, 362.0, 714.0, 227.0, 68.0)

# Combining an answer with its follow-up into one printed box (question 12's
# reason plus its explanation) may shrink, but not past legibility: below this
# the attachment carries the text rather than the page printing a line nobody
# can read.
MIN_COMBINED_FONT_SIZE = 7.0

# Signature marks and dates — response metadata, not questionnaire fields.
SIGNATURE_BOXES = {
    'officer_sign': (1, 263.8, 415.0, 237.3, 15.4),
    'officer_date': (1, 506.8, 415.4, 75.3, 15.0),
    'agent_sign': (1, 263.8, 347.9, 237.3, 13.5),
    'agent_date': (1, 506.8, 347.4, 75.3, 14.0),
}

# Inputs the carrier's dynamic form materialises NEXT TO an existing box when
# a dropdown reveals them. The template is flowed (`Main` and `subMedCat` are
# lr-tb), and the widths add up: "Employee %"/"Dependent %" (or "$") sit on
# the same line to the right of the contribution-method box; a row's
# "Medical Condition" and "Medical Condition Detail" sit to the right of the
# Medical Category box. The blank has empty paper there, so the stamper draws
# caption + gray box + value itself. Not rectangles in the blank, hence a
# separate dict — the drift guard checks FIELD_BOXES/BLOCK_BOXES only, and a
# companion test asserts these stay inside the page and clear of them.
# Shape: (page_index, x, y, w, h, caption).
# x positions leave room for each caption at FONT_SIZE, measured against the
# neighbour on its left: the method box ends at 321.2, the Employee box at 452.
INLINE_BOXES = {
    'numERConPercent': (0, 392.0, 389.1, 60.0, 16.5, 'Employee %'),
    'numDepConPercent': (0, 524.0, 389.1, 58.0, 16.5, 'Dependent %'),
    'numERConDefined': (0, 392.0, 389.1, 60.0, 16.5, 'Employee $'),
    'numDepConDefined': (0, 524.0, 389.1, 58.0, 16.5, 'Dependent $'),
}

# Captions for these sit ABOVE the box, like the carrier's own
# "Medical Category" caption at (84.2, 745.2).
INLINE_BLOCK_BOXES = {
    'conditions': {
        'drpMedCondition': (1, 203.0, 723.9, 152.0, 16.9, 'Medical Condition'),
        'drpMedConDetail': (1, 365.0, 723.9, 140.0, 16.9, 'Medical Condition Detail'),
    },
}

# The blank prints row 1 in the carrier's *initial* state: the two
# cancer-count lines. In Acrobat a category swaps those for its own effect
# lines (three surgery counts, three transplant counts, or nothing at all).
# The stamper repaints this area white and draws whichever lines row 1
# actually shows. Rect covers both printed captions and their boxes.
# Its top stops below the "How many total individuals" box (y 701.3) so the
# question above is never covered or written over.
EFFECT_AREA = (1, 19.0, 645.5, 545.0, 53.5)
# Where the replacement lines go. `top_y` is the FIRST box's bottom edge;
# each later line drops by `line_h`, and all three stay inside EFFECT_AREA.
EFFECT_LINE_GEOMETRY = {'caption_x': 20.8, 'box_x': 299.9, 'box_w': 57.3,
                        'box_h': 15.0, 'line_h': 17.8, 'top_y': 683.0}
EFFECT_LINES = {
    'surgery': ('txtSurgPlanned', 'txtSurgUnplanned', 'txtSurgUnknown'),
    'transplant': ('txtTransplantPlanned', 'txtTransplantUnplanned',
                   'txtTransplantUnknown'),
}
# The effect the printed area already shows — nothing to repaint for it.
PRINTED_EFFECT = 'cancer_counts'

# Fields with no printed box of their own: Acrobat inserts a whole line for
# them and reflows everything below, which a flat page cannot do. They are not
# automatically exiled, though — `questionnaire_stamp._placement` finds each
# one a home on the page when the text fits (question 12's explanation rides
# its reason box; the narrative wraps into NARRATIVE_AREA) and sends only what
# genuinely does not fit to the attachment.
OFF_FORM_FIELDS = (
    'txtRsnBidComments',
)

OFF_FORM_BLOCK_FIELDS = {
    'conditions': (
        'txtMedIll',
    ),
}
