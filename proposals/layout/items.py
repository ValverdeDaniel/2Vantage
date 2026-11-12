"""The frames a page is drawn from (plan.md §9.5; J122). Pure constructors of plain, JSON-able dicts.

Every frame is placed in points, y down from the page's top, and both painters draw the same list: the PDF
(`paint/pdf.py`) on a reportlab canvas, the PowerPoint (`paint/pptx/`, slice 31) as shapes, text boxes, a native
table or a native chart. Kinds (old Vantage 891f1b3 `guide.layout` and `proposal_furniture`):

- `rect` (fill, optional stroke, corner radius), `line`, `circle`, `gradient` (top colour to bottom colour);
- `image`: `src` names a picture (`asset:logos/mark.png`, `stock:<key>`, `logo:agency`, `photo:<member id>`); the
  deck's `images` resolve each name to bytes, so a frame never holds a file path (J.5 B12);
- `text`: measured paragraphs (`text.paragraph`), `title` marks the slide's title placeholder;
- `bars`: a clustered column chart, a native chart in the PowerPoint;
- `table`: a fitted table's grid, fills, rules and cell paragraphs (`flowables.Table` records it).
"""

from . import text as words_
from . import tokens


def rect(x, y, w, h, fill=None, stroke=None, lw=0.5, r=0):
    return {'t': 'rect', 'x': x, 'y': y, 'w': w, 'h': h, 'fill': fill, 'stroke': stroke, 'lw': lw, 'r': r}


def line(x1, y1, x2, y2, color, lw=0.5):
    return {'t': 'line', 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'color': color, 'lw': lw}


def circle(cx, cy, r, fill):
    return {'t': 'circle', 'cx': cx, 'cy': cy, 'r': r, 'fill': fill}


def gradient(x, y, w, h, top, bottom):
    return {'t': 'gradient', 'x': x, 'y': y, 'w': w, 'h': h, 'top': top, 'bottom': bottom}


def image(x, y, w, h, src, fit='cover', r=0):
    """A picture: `cover` fills the box and crops the overflow evenly; `contain` fits inside, top-left (a logo)."""
    return {'t': 'image', 'x': x, 'y': y, 'w': w, 'h': h, 'src': src, 'fit': fit, 'r': r}


def words(x, y, w, text, size, color, bold=False, italic=False, align='l', leading=None, title=False):
    """A text box of plain words, its height measured; typed line breaks are their own lines."""
    para = words_.paragraph([words_.run(text, size, color, bold, italic)], w, leading=leading, align=align)
    return {'t': 'text', 'x': x, 'y': y, 'w': w, 'h': para['h'], 'title': title, 'wrap': True, 'paragraphs': [para]}


def one_line(x, y, text, size, color, bold=False, align='l', width=None, title=False):
    """A line that never wraps; `x` is its right edge when `align` is 'r'."""
    measured = words_.width(text, size, bold) * 1.03 + 2
    room = width or measured
    para = words_.paragraph([words_.run(text, size, color, bold)], room + 4, align=align, wrap=False)
    para['h'] = round(size * 1.2, 1)
    left = x - room - 4 if align == 'r' else x
    return {
        't': 'text',
        'x': left,
        'y': y,
        'w': room + 4,
        'h': para['h'],
        'title': title,
        'wrap': False,
        'paragraphs': [para],
    }


def bars(x, y, w, h, categories, series, money=True):
    """A clustered column chart. `series`: [{name, values, color}], with `colors` for one colour per column; a None
    value is no bar. A single series needs no legend."""
    return {
        't': 'bars',
        'x': x,
        'y': y,
        'w': w,
        'h': h,
        'categories': [str(c) for c in categories],
        'series': [dict(entry, values=list(entry['values'])) for entry in series],
        'money': money,
    }


def shifted(item, dx, dy):
    """A copy of `item` moved by (dx, dy), its table cells and their paragraphs with it."""
    item = dict(item)
    if item['t'] == 'line':
        item.update(x1=item['x1'] + dx, x2=item['x2'] + dx, y1=item['y1'] + dy, y2=item['y2'] + dy)
    elif item['t'] == 'circle':
        item.update(cx=item['cx'] + dx, cy=item['cy'] + dy)
    else:
        item.update(x=item['x'] + dx, y=item['y'] + dy)
    if item['t'] == 'table':
        item['cells'] = [shifted(cell, dx, dy) for cell in item['cells']]
        item['rules'] = [shifted(rule, dx, dy) for rule in item['rules']]
    elif item['t'] == 'cell':
        item['text'] = shifted(item['text'], dx, dy)
    return item


def height_of(items):
    """How far down a list of items reaches."""
    return max((item['y'] + item['h'] for item in items if 'h' in item and 'y' in item), default=0)


def is_text(item):
    return item['t'] == 'text'


def plain(item):
    """A text frame's words, its lines joined by spaces (for tests and the fit report)."""
    return ' '.join(' '.join(seg['text'] for seg in line) for para in item['paragraphs'] for line in para['lines'])


INK = tokens.PRESENTATION['ink']
INK2 = tokens.PRESENTATION['ink2']
