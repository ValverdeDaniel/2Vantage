"""Which painter replays which recorded frame (plan.md §9.6; J141): every kind `layout/items.py` records, the same
list the PDF draws (`paint/pdf.py`'s DRAW). A kind with no painter is an error here, so a frame can never silently go
missing from the PowerPoint (the old `DeckError`).
"""

from . import chart, shapes, table, text

DRAW = {
    'rect': shapes.rect,
    'line': shapes.line,
    'circle': shapes.circle,
    'gradient': shapes.gradient,
    'image': shapes.image,
    'text': text.text_box,
    'table': table.table,
    'bars': chart.bars,
}


class DeckError(Exception):
    """A recorded frame the PowerPoint has no painter for."""


def paint(slide, it, pictures):
    painter = DRAW.get(it['t'])
    if painter is None:
        raise DeckError(f'The layout recorded a {it["t"]} frame the PowerPoint cannot replay.')
    return painter(slide, it, pictures)
