"""Points to a PowerPoint's units, colours and the defaults every shape switches off (plan.md §9.6; J141). Ported from
old Vantage 891f1b3 `guide/render_pptx.py` (`_emu`, `_rgb`, `_no_shadow`, `_frame`). Pure helpers.
"""

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.oxml.ns import qn
from pptx.util import Emu

from ...layout import tokens

# Helvetica in the PDF prints as Arial here: the same metrics, so PowerPoint wraps where the layout did (J142).
FAMILY = tokens.FONTS['family']
EMU_PER_POINT = 12700
# Room a wrapping text box or table cell gets beyond its recorded width, on the side its words never reach: a line the
# layout filled to within a hair must not wrap on a renderer's rounding (LibreOffice wrapped "Next renewal", 67.86 pt
# in 67.92). Far less than a word, so it does not pull one up a line (old Vantage added 3% to a box, which did).
TEXT_SLACK = 1.0


def emu(points):
    return Emu(int(round(points * EMU_PER_POINT)))


def rgb(hex_colour):
    return RGBColor.from_string(hex_colour.lstrip('#').upper())


def hex_value(hex_colour):
    """`#173a63` as DrawingML writes it: `173A63`."""
    return hex_colour.lstrip('#').upper()


def slack_sides(paragraphs):
    """(left, right): where a box's slack goes so its words stay where they were recorded: after left-aligned words,
    before right-aligned ones, half on each side of centred ones."""
    aligns = {para['align'] for para in paragraphs}
    if aligns <= {'l'}:
        return 0.0, TEXT_SLACK
    if aligns == {'r'}:
        return TEXT_SLACK, 0.0
    return TEXT_SLACK / 2, TEXT_SLACK / 2


def no_shadow(shape):
    """Autoshapes inherit the theme's effect style (a soft shadow); switch it off, in the shape's own properties and in
    its style reference, which LibreOffice reads even when the shape's own list is empty."""
    sp_pr = shape._element.spPr
    if sp_pr.find(qn('a:effectLst')) is None:
        etree.SubElement(sp_pr, qn('a:effectLst'))
    for reference in shape._element.iter(qn('a:effectRef')):
        reference.set('idx', '0')


def unkerned(r_pr):
    """No pair kerning on a run: the layout measured each word unkerned (Helvetica's widths, as the PDF draws them),
    and a kerned line is narrower, so PowerPoint would pull a word up a line the PDF broke before (J142)."""
    r_pr.set('kern', '0')


def bare(text_frame, anchor=MSO_ANCHOR.TOP):
    """A text frame with no insets and no autofit, so its words sit where the recorded frame put them."""
    text_frame.word_wrap = True
    text_frame.auto_size = MSO_AUTO_SIZE.NONE
    text_frame.vertical_anchor = anchor
    text_frame.margin_left = text_frame.margin_right = text_frame.margin_top = text_frame.margin_bottom = 0
