"""Cards placed in a page's body (plan.md §9.5; J125, J126, J128): a figure on a tile, a person's photo or monogram,
and the bars chart's frame. Ported from old Vantage 891f1b3 `proposal_furniture.tile`, `monogram`, `bars` and
`proposal_presentation._photo_box`. Pure: frames, y down from the block's top.
"""

from . import items, tokens
from . import text as words


def tile(x, y, w, h, value, label, colours, sub='', dark=False, size=26, ground=None):
    """A figure on a card; dark for the one that matters most. The figure's type steps down until it fits."""
    ink, soft = (tokens.WHITE, colours['silver']) if dark else (colours['navy'], colours['ink2'])
    fill = ground or (colours['navy'] if dark else colours['blue_bg'])
    placed = [items.rect(x, y, w, h, fill=fill, r=8)]
    while size > 13 and words.width(value, size, bold=True) > w - 24:
        size -= 1
    room = (h - size * 1.2 - 13 * (1 + bool(sub))) / 3
    top = y + max(6, room)
    figure = items.words(x + 6, top, w - 12, value, size, ink, bold=True, align='c')
    placed.append(figure)
    top += figure['h'] + 3
    caption = items.words(x + 10, top, w - 20, label, 10.5, soft, align='c', leading=13)
    placed.append(caption)
    if sub:
        placed.append(items.words(x + 10, top + caption['h'] + 1, w - 20, sub, 9.5, soft, align='c', leading=12))
    return placed


def tiles(entries, colours, width, height, size, gap=12, most=300):
    """A row of tiles across `width`: [(label, value, sub, dark)]. A lone figure stays a tile (at most `most` wide)."""
    count = len(entries)
    each = min((width - gap * (count - 1)) / count, most)
    placed = []
    for number, (label, value, sub, dark) in enumerate(entries):
        placed += tile(number * (each + gap), 0, each, height, value, label, colours, sub=sub, dark=dark, size=size)
    return placed


def monogram(cx, cy, r, name, colours):
    """Initials on a circle, for a person with no photo on file."""
    letters = ''.join(part[0] for part in str(name or '').split()[:2]).upper()
    return [
        items.circle(cx, cy, r, fill=colours['blue_bg']),
        items.one_line(cx - r, cy - r * 0.45, letters, r * 0.75, colours['navy'], bold=True, align='c', width=2 * r),
    ]


def photo(member, x, y, side, colours, r=14):
    """A person's photo, or their initials on a tinted square."""
    if member.get('photo'):
        return [items.image(x, y, side, side, member['photo'], r=r)]
    return [items.rect(x, y, side, side, fill=colours['blue_bg'], r=r)] + monogram(
        x + side / 2, y + side / 2, side * 0.3, member.get('name'), colours
    )


def bars(x, y, w, h, categories, series, money=True):
    """A clustered column chart's frame (a native chart in the PowerPoint, drawn columns in the PDF)."""
    return items.bars(x, y, w, h, categories, series, money)
