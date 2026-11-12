"""The client PDF: the recorded frames drawn with reportlab 4.2.5 (plan.md §9.7; J122, J142; old Vantage 891f1b3
`proposal_furniture.paint_items`, `guide.render_pdf`, `_paint_bars`).

`draw(pages, title, sources)` → the PDF's bytes, one 960 × 540 page a recorded page: a content page's chrome under its
frames, a full page's frames alone. Text is drawn as measured segments with `drawString`, never as markup, so nothing
typed is interpreted; Helvetica is one of the PDF's standard fonts, so nothing is embedded. Pictures come by name
(`items.image`'s `src`): the bundled assets from `assets/images/`, an upload's bytes from `sources`; a picture that will
not open is left out, never the page. No layout happens here: what the PowerPoint replays is what this draws.
"""

import io

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as pdf_canvas

from ..layout import tokens
from ..layout.text import line_width

PAGE_H = tokens.PAGE_H


def _fy(y):
    return PAGE_H - y


class _Pictures:
    """Each named picture opened once per file."""

    def __init__(self, sources):
        self.sources = sources or {}
        self.found = {}

    def get(self, src):
        if src not in self.found:
            self.found[src] = self._open(src)
        return self.found[src]

    def _open(self, src):
        try:
            if src.startswith('asset:'):
                return ImageReader(str(tokens.ASSETS / src[len('asset:') :]))
            if src.startswith('stock:'):
                return ImageReader(str(tokens.ASSETS / 'stock_images' / f'{src[len("stock:") :]}.jpg'))
            data = self.sources.get(src)
            return ImageReader(io.BytesIO(data)) if data else None
        except Exception:  # noqa: BLE001 - a broken picture must not lose the document
            return None


def _path(c, it):
    top = _fy(it['y'])
    path = c.beginPath()
    radius = min(it.get('r') or 0, it['w'] / 2, it['h'] / 2)
    if radius:
        path.roundRect(it['x'], top - it['h'], it['w'], it['h'], radius)
    else:
        path.rect(it['x'], top - it['h'], it['w'], it['h'])
    return path


def _rect(c, it, _pictures):
    if not (it.get('fill') or it.get('stroke')):
        return
    if it.get('fill'):
        c.setFillColor(HexColor(it['fill']))
    if it.get('stroke'):
        c.setStrokeColor(HexColor(it['stroke']))
        c.setLineWidth(it.get('lw') or 0.5)
    c.drawPath(_path(c, it), stroke=bool(it.get('stroke')), fill=bool(it.get('fill')))


def _line(c, it, _pictures):
    c.saveState()
    c.setStrokeColor(HexColor(it['color']))
    c.setLineWidth(it['lw'])
    c.line(it['x1'], _fy(it['y1']), it['x2'], _fy(it['y2']))
    c.restoreState()


def _circle(c, it, _pictures):
    c.setFillColor(HexColor(it['fill']))
    c.circle(it['cx'], _fy(it['cy']), it['r'], stroke=0, fill=1)


def _gradient(c, it, _pictures):
    top = _fy(it['y'])
    path = c.beginPath()
    path.rect(it['x'], top - it['h'], it['w'], it['h'])
    c.saveState()
    c.clipPath(path, stroke=0, fill=0)
    c.linearGradient(it['x'], top, it['x'], top - it['h'], (HexColor(it['top']), HexColor(it['bottom'])), extend=False)
    c.restoreState()


def _image(c, it, pictures):
    """`cover` scales to fill and is clipped to the frame (rounded as it asks); `contain` fits inside, top-left."""
    picture = pictures.get(it['src'])
    if picture is None:
        return
    iw, ih = picture.getSize()
    if not (iw and ih):
        return
    x, y, w, h = it['x'], it['y'], it['w'], it['h']
    if it['fit'] == 'contain':
        scale = min(w / iw, h / ih)
        c.drawImage(picture, x, _fy(y) - ih * scale, iw * scale, ih * scale, mask='auto')
        return
    scale = max(w / iw, h / ih)
    dw, dh = iw * scale, ih * scale
    c.saveState()
    c.clipPath(_path(c, it), stroke=0, fill=0)
    c.drawImage(picture, x + (w - dw) / 2, _fy(y + (h - dh) / 2) - dh, dw, dh, mask='auto')
    c.restoreState()


def _text(c, it, _pictures):
    top = _fy(it['y'])
    used = 0.0
    for para in it['paragraphs']:
        leading = para['leading']
        for number, segments in enumerate(para['lines']):
            if not segments:
                continue
            size = max(seg['size'] for seg in segments)
            baseline = top - used - number * leading - it.get('drop', tokens.BASELINE_DROP) * size
            room, wide = it['w'], line_width(segments)
            x = it['x'] + {'c': (room - wide) / 2, 'r': room - wide}.get(para['align'], 0)
            for seg in segments:
                c.setFont(seg['font'], seg['size'])
                c.setFillColor(HexColor(seg['color']))
                c.drawString(x, baseline, seg['text'])
                if seg.get('link'):
                    c.linkURL(seg['link'], (x, baseline - 2, x + seg['w'], baseline + seg['size']), relative=0)
                x += seg['w']
        used += max(1, len(para['lines'])) * leading


def _table(c, it, pictures):
    for cell in it['cells']:
        if cell.get('fill'):
            _rect(c, {'x': cell['x'], 'y': cell['y'], 'w': cell['w'], 'h': cell['h'], 'fill': cell['fill']}, pictures)
    for rule in it['rules']:
        _line(c, rule, pictures)
    for cell in it['cells']:
        _text(c, cell['text'], pictures)


def _bar_label(value, money):
    if value is None:
        return ''
    return f'${value:,.0f}' if money else f'{value:+.1f}%'


def _bars(c, it, _pictures):
    """The chart's columns, as the PowerPoint's native chart draws them: a group per category, a figure over each
    column, the legend under the plot when there are two or more series."""
    x, top, w, h = it['x'], _fy(it['y']), it['w'], it['h']
    values = [v for entry in it['series'] for v in entry['values'] if v is not None]
    if not values:
        return
    ink, ink2, font = tokens.PRESENTATION['ink'], tokens.PRESENTATION['ink2'], tokens.FONTS['regular']
    high, low = max(max(values), 0), min(min(values), 0)
    span = (high - low) or 1
    with_legend = len(it['series']) > 1
    legend, labels, head = (18 if with_legend else 0), 26, 18
    plot = h - legend - labels - head
    base = top - h + legend + labels + plot * (-low / span)
    count = max(1, len(it['categories']))
    group = w / count
    series = len(it['series'])
    bar = min(group * 0.72 / max(1, series), 64)
    c.saveState()
    c.setStrokeColor(HexColor(tokens.PRESENTATION['hairline']))
    c.setLineWidth(0.75)
    c.line(x, base, x + w, base)
    for number, category in enumerate(it['categories']):
        left = x + group * number + (group - bar * series) / 2
        for order, entry in enumerate(it['series']):
            value = entry['values'][number]
            if value is None:
                continue
            tall = plot * (abs(value) / span)
            bottom = base if value >= 0 else base - tall
            colour = (entry.get('colors') or [None] * count)[number] or entry['color']
            c.setFillColor(HexColor(colour))
            c.rect(left + order * bar + 1, bottom, bar - 2, tall, stroke=0, fill=1)
            c.setFillColor(HexColor(ink))
            c.setFont(font, 9.5)
            label_y = bottom + tall + 4 if value >= 0 else bottom - 12
            c.drawCentredString(left + order * bar + bar / 2, label_y, _bar_label(value, it['money']))
        c.setFillColor(HexColor(ink2))
        c.setFont(font, 10.5)
        for row, piece in enumerate(simpleSplit(category, font, 10.5, group - 8)[:2]):
            c.drawCentredString(x + group * number + group / 2, top - h + legend + labels - 13 - row * 12, piece)
    if with_legend:
        cursor = x + w / 2 - sum(stringWidth(e['name'], font, 10.5) + 34 for e in it['series']) / 2
        for entry in it['series']:
            c.setFillColor(HexColor(entry['color']))
            c.rect(cursor, top - h + 3, 10, 10, stroke=0, fill=1)
            c.setFillColor(HexColor(ink2))
            c.setFont(font, 10.5)
            c.drawString(cursor + 14, top - h + 4, entry['name'])
            cursor += stringWidth(entry['name'], font, 10.5) + 34
    c.restoreState()


DRAW = {
    'rect': _rect,
    'line': _line,
    'circle': _circle,
    'gradient': _gradient,
    'image': _image,
    'text': _text,
    'table': _table,
    'bars': _bars,
}


def draw(pages, title='', sources=None):
    """The PDF's bytes. `sources`: {image src: bytes} for the pictures not bundled (the firm's logo, photos)."""
    buffer = io.BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=tokens.DECK_SIZE, pageCompression=1)
    c.setTitle(title)
    c.setAuthor('')
    c.setCreator('2Vantage')
    pictures = _Pictures(sources)
    for page in pages:
        for item in page.get('chrome') or []:
            DRAW[item['t']](c, item, pictures)
        for item in page['frames']:
            DRAW[item['t']](c, item, pictures)
        c.showPage()
    c.save()
    return buffer.getvalue()
