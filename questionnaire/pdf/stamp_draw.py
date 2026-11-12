"""Florida Blue's own form, filled: the answers stamped into the bundled flat blank (G57).

A reportlab canvas draws only the answers, placed by `fl_blue_51_layout` as `stamp_place.placement` decided, and pypdf
merges that overlay onto a copy of the blank, so the carrier's pages — logo, bands and all — go out. A box holding a
default the carrier baked into the print ("Florida", "Comparing Benefits & Rates") is repainted in its own CMYK grey
first, so nothing double-prints; the cancer-count pair is repainted away when a category swaps it for other lines.
What the pages cannot hold prints on the attachment after them (`attachment.stamp_pages`). DRAFT on every page until
the officer signs, then the e-signature caption (G53). Ported from old Vantage 891f1b3 (`questionnaire_stamp.py`).
"""

from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as pdfcanvas

from .. import forms
from . import attachment, fonts, stamp_place
from .printed import text


class StampError(Exception):
    """The form cannot be stamped (no blank, no layout)."""


def box(canvas, layout, rect, value, cover=True):
    """One value inside a printed input box, shrunk to fit, the box repainted first unless it is white."""
    _page, x, y, w, h = rect
    if cover:
        canvas.saveState()
        canvas.setFillColorCMYK(*layout.BOX_CMYK)
        canvas.rect(x, y, w, h, stroke=0, fill=1)
        canvas.restoreState()
    fitted, size = stamp_place.fit(value, w - 5, layout.FONT_SIZE, layout.MIN_FONT_SIZE, layout.FONT_NAME)
    canvas.setFont(layout.FONT_NAME, size)
    canvas.setFillColor(colors.black)
    canvas.drawString(x + 2.5, y + (h - size) / 2 + 1.2, fitted)


def inline(canvas, layout, rect, value, caption_top=False):
    """A box the carrier's dynamic form inserts beside another: the caption is drawn too, left or above."""
    page, x, y, w, h, caption = rect
    canvas.setFillColor(colors.black)
    canvas.setFont(layout.FONT_NAME, layout.FONT_SIZE)
    if caption_top:
        canvas.drawString(x, y + h + 3.5, caption)
    else:
        width = stringWidth(caption, layout.FONT_NAME, layout.FONT_SIZE)
        canvas.drawString(x - width - 5, y + (h - layout.FONT_SIZE) / 2 + 1.2, caption)
    box(canvas, layout, (page, x, y, w, h), value)


def tick(canvas, layout, rect):
    _page, x, y, w, h = rect
    canvas.setFillColor(colors.black)
    canvas.setFont(layout.FONT_NAME, layout.FONT_SIZE)
    canvas.drawCentredString(x + w / 2, y + h / 2 - 3.4, 'X')


def lines(canvas, layout, area, wrapped, top=None):
    _page, x, first, _width, _drop = area
    canvas.setFont(layout.FONT_NAME, layout.FONT_SIZE)
    canvas.setFillColor(colors.black)
    y = first if top is None else top
    for entry in wrapped:
        canvas.drawString(x, y, entry)
        y -= layout.LEADING


def effects(canvas, layout, found_lines):
    """Repaint the printed cancer-count pair and draw the lines the row's category shows instead."""
    page, x, y, w, h = layout.EFFECT_AREA
    canvas.saveState()
    canvas.setFillColor(colors.white)
    canvas.rect(x, y, w, h, stroke=0, fill=1)
    canvas.restoreState()
    geometry = layout.EFFECT_LINE_GEOMETRY
    for index, (caption, value) in enumerate(found_lines):
        top = geometry['top_y'] - index * geometry['line_h']
        if top < y:
            break  # the paper is full; the attachment carries the rest
        canvas.setFillColor(colors.black)
        canvas.setFont(layout.FONT_NAME, layout.FONT_SIZE)
        canvas.drawString(geometry['caption_x'], top + 3.5, caption)
        box(canvas, layout, (page, geometry['box_x'], top, geometry['box_w'], geometry['box_h']), value)


def _scalars(canvas, form, layout, found, place, page):
    for key, rect in layout.FIELD_BOXES.items():
        if rect[0] != page:
            continue
        if key in place['hosts']:
            value = place['hosts'][key]
        elif key in place['overflow']:
            value = stamp_place.SEE_ATTACHMENT
        else:
            value = stamp_place.boxed(form, '', key, found.scalars)
        if value:
            box(canvas, layout, rect, value, cover=key not in layout.NO_COVER)
    for key, pair in layout.CHECKBOXES.items():
        answer = text(found.scalars, key).lower()
        for choice, rect in pair.items():
            if rect[0] == page and answer == choice.lower():
                tick(canvas, layout, rect)
    for key, rect in layout.INLINE_BOXES.items():
        value = stamp_place.boxed(form, '', key, found.scalars)
        if rect[0] == page and value:
            inline(canvas, layout, rect, value)


def _rows(canvas, form, layout, found, place, page):
    for block, boxes in layout.BLOCK_BOXES.items():
        _number, vals = stamp_place.first_row(found, block)
        for key, rect in boxes.items():
            value = stamp_place.boxed(form, block, key, vals)
            if rect[0] != page or not value:
                continue
            if block in place['row_overflow'] and stamp_place.too_long(form, layout, block, key, vals, rect):
                value = stamp_place.SEE_ATTACHMENT
            box(canvas, layout, rect, value, cover=key not in layout.NO_COVER)
    for block, boxes in layout.INLINE_BLOCK_BOXES.items():
        _number, vals = stamp_place.first_row(found, block)
        for key, rect in boxes.items():
            value = stamp_place.boxed(form, block, key, vals)
            if rect[0] == page and value:
                inline(canvas, layout, rect, value, caption_top=True)
    repaint = False
    block = stamp_place.effect_block(form, layout)
    number, vals = stamp_place.first_row(found, block)
    if number is not None and layout.EFFECT_AREA[0] == page:
        repaint, found_lines = stamp_place.effect_lines(form, layout, vals)
        if repaint:
            effects(canvas, layout, found_lines)
    narrative = place['narrative']
    if narrative and layout.NARRATIVE_AREA[0] == page:
        if repaint:  # the narrative shows only while the counts do, so the cascade makes this impossible
            raise StampError('The illness detail and the replaced follow-up lines claim the same paper.')
        area = layout.NARRATIVE_AREA
        lines(canvas, layout, area, narrative['heading'])
        lines(canvas, layout, area, narrative['lines'], top=area[2] - len(narrative['heading']) * layout.LEADING)
    for key, area in layout.TEXT_AREAS.items():
        if area[0] == page:
            lines(canvas, layout, area, place['comments'].get(key) or [])


def _signatures(canvas, layout, found, page):
    marks = {
        'officer_sign': found.officer and found.officer['name'],
        'officer_date': found.officer and found.officer['date'],
        'agent_sign': found.agent and found.agent['name'],
        'agent_date': found.agent and found.agent['date'],
    }
    for key, rect in layout.SIGNATURE_BOXES.items():
        if rect[0] == page and marks.get(key):
            box(canvas, layout, rect, marks[key])


def overlay(form, layout, found, place):
    """One reportlab canvas holding just the answers, page for page with the blank."""
    buffer = BytesIO()
    canvas = pdfcanvas.Canvas(buffer, pagesize=layout.PAGE_SIZE)
    for page in range(layout.PAGE_COUNT):
        _scalars(canvas, form, layout, found, place, page)
        _rows(canvas, form, layout, found, place, page)
        _signatures(canvas, layout, found, page)
        fonts.draw_notes(canvas, found)
        canvas.showPage()
    canvas.save()
    buffer.seek(0)
    return buffer


def stamp(form, layout, found):
    """The carrier's form, filled, as bytes."""
    blank = forms.asset_path(layout.BLANK_FILE)
    if blank is None:
        raise StampError(f'No stampable blank for "{form["key"]}".')
    stamp_place.face(layout)
    place = stamp_place.placement(form, layout, found)
    stamped = PdfReader(overlay(form, layout, found, place))
    writer = PdfWriter()
    for index, page in enumerate(PdfReader(str(blank)).pages):
        if index < len(stamped.pages):
            page.merge_page(stamped.pages[index])
        writer.add_page(page)
    if stamp_place.needs_attachment(layout, found, place):
        extra = attachment.stamp_pages(form, layout, found, place, stamp_place.chunks(form, layout, found, place))
        if extra is not None:
            for page in PdfReader(extra).pages:
                writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()
