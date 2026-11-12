"""Recorded rectangles, lines, circles, gradients and pictures as PowerPoint shapes (plan.md §9.6; J141). Ported from
old Vantage 891f1b3 `guide/render_pptx.py` (`_rect`, `_line`, `_circle`, `_image`) and `proposal_deck._gradient`.

Each painter takes (slide, frame, pictures) and adds one shape where the frame was recorded. Pictures come by name, as
the PDF's do (`paint/pdf.py`): the bundled assets from `assets/images/`, an upload's bytes from `sources`; a picture
that will not open is left out, never the slide.
"""

import io

from lxml import etree
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.oxml.ns import qn
from pptx.util import Pt

from ...layout import tokens
from .units import emu, no_shadow, rgb


class Pictures:
    """Each named picture read once per file: its bytes and its size in pixels."""

    def __init__(self, sources=None):
        self.sources = sources or {}
        self.found = {}

    def get(self, src):
        if src not in self.found:
            self.found[src] = self._open(src)
        return self.found[src]

    def _bytes(self, src):
        if src.startswith('asset:'):
            return (tokens.ASSETS / src[len('asset:') :]).read_bytes()
        if src.startswith('stock:'):
            return (tokens.ASSETS / 'stock_images' / f'{src[len("stock:") :]}.jpg').read_bytes()
        return self.sources.get(src)

    def _open(self, src):
        from PIL import Image

        try:
            data = self._bytes(src)
            if not data:
                return None
            with Image.open(io.BytesIO(data)) as picture:
                size = picture.size
        except Exception:  # noqa: BLE001 - a broken picture must not lose the document
            return None
        return (data, size) if all(size) else None


def _fill(shape, colour):
    if colour:
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb(colour)
    else:
        shape.fill.background()


def _stroke(shape, colour, lw):
    if colour:
        shape.line.color.rgb = rgb(colour)
        shape.line.width = Pt(lw or 0.5)
    else:
        shape.line.fill.background()


def _rounding(it):
    return min(it.get('r') or 0, it['w'] / 2, it['h'] / 2)


def rect(slide, it, _pictures=None):
    if not (it.get('fill') or it.get('stroke')):
        return None
    radius = _rounding(it)
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, emu(it['x']), emu(it['y']), emu(it['w']), emu(it['h']))
    if radius:
        shape.adjustments[0] = radius / min(it['w'], it['h'])
    _fill(shape, it.get('fill'))
    _stroke(shape, it.get('stroke'), it.get('lw'))
    no_shadow(shape)
    return shape


def line(slide, it, _pictures=None):
    connector = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, emu(it['x1']), emu(it['y1']), emu(it['x2']), emu(it['y2'])
    )
    connector.line.color.rgb = rgb(it['color'])
    connector.line.width = Pt(it['lw'])
    no_shadow(connector)
    return connector


def circle(slide, it, _pictures=None):
    r = it['r']
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, emu(it['cx'] - r), emu(it['cy'] - r), emu(2 * r), emu(2 * r))
    _fill(shape, it.get('fill'))
    _stroke(shape, None, 0)
    no_shadow(shape)
    return shape


def gradient(slide, it, _pictures=None):
    """A rectangle fading from its top colour to its bottom colour."""
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, emu(it['x']), emu(it['y']), emu(it['w']), emu(it['h']))
    fill = shape.fill
    fill.gradient()
    # DrawingML's angle runs clockwise from the left: 90 degrees is top to bottom.
    fill._fill._gradFill.find(qn('a:lin')).set('ang', '5400000')
    stops = fill.gradient_stops
    stops[0].position, stops[1].position = 0.0, 1.0
    stops[0].color.rgb = rgb(it['top'])
    stops[1].color.rgb = rgb(it['bottom'])
    shape.line.fill.background()
    no_shadow(shape)
    return shape


def _round_picture(picture, radius, w, h):
    picture.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
    geometry = picture._element.spPr.find(qn('a:prstGeom'))
    guides = geometry.find(qn('a:avLst'))
    if guides is None:
        guides = etree.SubElement(geometry, qn('a:avLst'))
    for old in list(guides):
        guides.remove(old)
    etree.SubElement(guides, qn('a:gd'), name='adj', fmla=f'val {int(radius / min(w, h) * 100000)}')


def image(slide, it, pictures):
    """`cover` fills the frame, its overflow cropped evenly, rounded as the frame asks; `contain` fits inside,
    top-left (a logo)."""
    found = pictures.get(it['src'])
    if found is None:
        return None
    data, (iw, ih) = found
    x, y, w, h = it['x'], it['y'], it['w'], it['h']
    if it['fit'] == 'contain':
        scale = min(w / iw, h / ih)
        return slide.shapes.add_picture(io.BytesIO(data), emu(x), emu(y), emu(iw * scale), emu(ih * scale))
    picture = slide.shapes.add_picture(io.BytesIO(data), emu(x), emu(y), emu(w), emu(h))
    box, ratio = w / h, iw / ih
    if ratio > box:
        picture.crop_left = picture.crop_right = (1 - box / ratio) / 2
    elif ratio < box:
        picture.crop_top = picture.crop_bottom = (1 - ratio / box) / 2
    radius = _rounding(it)
    if radius:
        _round_picture(picture, radius, w, h)
    return picture
