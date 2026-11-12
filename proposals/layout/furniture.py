"""The dark pages' furniture (plan.md §9.5; J123, J124, J138): the brand's palette, the dark ground, the firm's logo,
the Draft mark, the cover, the agenda, a section's divider and the thank-you page, each a list of frames. Ported
from old Vantage 891f1b3 `proposal_furniture.py` (the D-178 Presentation format), without the Claude Unleashed
themes (J144, deferred). Pure.
"""

from . import items, tokens
from . import text as words

DRAFT_MARK = 'Draft for review, not for clients'  # proposals.ready.DRAFT_MARK, the old D-175 words


def _hex_or(value, fallback):
    value = str(value or '').strip().lower()
    if len(value) == 7 and value.startswith('#'):
        try:
            int(value[1:], 16)
            return value
        except ValueError:
            pass
    return fallback


def _mix(one, other, amount):
    """`one` moved toward `other` by `amount` (0..1), as #rrggbb."""
    first = [int(one[i : i + 2], 16) for i in (1, 3, 5)]
    second = [int(other[i : i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(a + (b - a) * amount):02x}' for a, b in zip(first, second, strict=True))


def palette(brand=None):
    """The format's colours for a brand: the tool's blues as they are for ours, a darker shade of another firm's."""
    brand = _hex_or(brand, tokens.DEFAULT_BRAND)
    colours = dict(tokens.PRESENTATION, navy=brand)
    if brand != tokens.DEFAULT_BRAND:
        colours['navy_dark'] = _mix(brand, '#000000', 0.32)
    return colours


def dark_ground(colours, mark=True):
    """Every dark page's ground: the lift of the brand's navy, the mark large and quiet on the right. A page with a
    picture goes without the mark, which would stick out from behind it."""
    width, height = tokens.DECK_SIZE
    ghost_w = 470
    ghost_h = ghost_w / tokens.GHOST_RATIO
    ground = [items.gradient(0, 0, width, height, colours['navy_dark'], colours['navy'])]
    if mark:
        ground.append(
            items.image(width - ghost_w - 26, (height - ghost_h) / 2, ghost_w, ghost_h, tokens.MARK_GHOST, 'contain')
        )
    return ground


def logo(x, y, w, src, on_dark=True):
    """The firm's logo: its upload (on a white card over a dark ground, where a dark logo would vanish), else
    Vantage's own."""
    h = w / tokens.LOGO_RATIO
    if src:
        card = [items.rect(x - 10, y - 8, w + 20, h + 16, fill=tokens.WHITE, r=6)] if on_dark else []
        return [*card, items.image(x, y, w, h, src, fit='contain')]
    return [items.image(x, y, w, h, tokens.LOGO_ON_DARK if on_dark else tokens.LOGO_ON_LIGHT, fit='contain')]


def draft_items():
    """The Draft mark, where nobody can miss it, on any ground (D-175; OQ35)."""
    width = words.width(DRAFT_MARK, 11, bold=True) + 24
    x = tokens.PAGE_W - tokens.PAGE_MARGIN - width
    return [
        items.rect(x, 12, width, 22, fill=tokens.PRESENTATION['draft'], r=4),
        items.one_line(x + 12, 17, DRAFT_MARK, 11, tokens.WHITE, bold=True),
    ]


def _beside_picture(left):
    return tokens.PICTURE_BOX[0] - left - 30


def _picture(src):
    return [items.image(*tokens.PICTURE_BOX, src, r=26)] if src else []


def cover_items(cover, colours, logo_src=None, picture=None, draft=False):
    """The cover: the client's name is the hero, what the document is under the rule, then its dates and who
    prepared it. `cover`: {client, kind, lines}."""
    placed = _picture(picture)
    room = _beside_picture(72) if picture else 620
    placed += logo(60, 44, 190, logo_src)
    y, size = 158, 44
    while size > 26 and len(words.lines_of([words.run(cover['client'], size, '#fff', True)], room)) > 3:
        size -= 2
    name = items.words(60, y, room, cover['client'], size, tokens.WHITE, bold=True, leading=round(size * 1.1, 1))
    name['title'] = True
    placed.append(name)
    y += name['h'] + 14
    placed.append(items.rect(60, y, 96, 5, fill=colours['logo_blue']))
    y += 22
    if cover.get('kind'):
        kind = items.words(60, y, room, cover['kind'], 22, tokens.WHITE, bold=True)
        placed.append(kind)
        y += kind['h'] + 10
    for fact in cover.get('lines') or []:
        item = items.words(60, y, room, fact, 13, colours['silver'], leading=18)
        placed.append(item)
        y += item['h']
    return placed + (draft_items() if draft else [])


def agenda_items(entries, colours, draft=False, picture=None, heading='Agenda'):
    """A dark panel naming the page, and the document's sections numbered beside it. `entries`: [{title, sub}]."""
    width, height = tokens.DECK_SIZE
    panel = tokens.AGENDA_PANEL
    placed = [items.rect(panel, 0, width - panel, height, fill=tokens.WHITE)]
    if picture:
        placed.append(items.image(*tokens.AGENDA_PICTURE_BOX, picture))
    head = items.words(48, 62, panel - 80, heading, 38, tokens.WHITE, bold=True, leading=44, title=True)
    placed.append(head)
    placed.append(items.rect(48, 62 + head['h'] + 12, 72, 5, fill=colours['logo_blue']))
    count = max(1, len(entries))
    left, right = panel + 56, width - 56
    row = min(84, (height - 2 * 44) / count)
    y = (height - row * count) / 2
    for number, entry in enumerate(entries, start=1):
        placed.append(items.line(left, y, right, y, colours['hairline'], 1))
        middle = y + row / 2
        placed.append(items.one_line(left + 4, middle - 15, str(number), 24, colours['blue'], bold=True))
        has_sub = bool(entry.get('sub'))
        placed.append(
            items.words(
                left + 56,
                middle - (19 if has_sub else 11),
                right - left - 60,
                entry['title'],
                17,
                colours['ink'],
                bold=True,
                leading=21,
            )
        )
        if has_sub:
            placed.append(
                items.words(left + 56, middle + 4, right - left - 60, entry['sub'], 11.5, colours['ink2'], leading=15)
            )
        y += row
    placed.append(items.line(left, y, right, y, colours['hairline'], 1))
    return placed + (draft_items() if draft else [])


def section_items(number, title, sub, colours, draft=False, picture=None):
    """A section's divider: its number, its title, what it holds."""
    placed = _picture(picture)
    room = _beside_picture(72) if picture else 560
    y = 196
    placed.append(items.one_line(72, y, f'{number:02d}', 18, colours['logo_blue'], bold=True))
    y += 30
    heading = items.words(72, y, room, title, 44, tokens.WHITE, bold=True, leading=50, title=True)
    placed.append(heading)
    y += heading['h'] + 14
    placed.append(items.rect(72, y, 96, 5, fill=colours['logo_blue']))
    y += 20
    if sub:
        placed.append(items.words(72, y, room, sub, 15, colours['silver'], leading=20))
    return placed + (draft_items() if draft else [])


def closing_items(closing, colours, logo_src=None, draft=False, picture=None):
    """The thank-you page. `closing`: {heading, lines, small}; the small print sits at the page's foot."""
    width, height = tokens.DECK_SIZE
    placed = _picture(picture)
    room = _beside_picture(72) if picture else 620
    placed += logo(72, 60, 190, logo_src)
    y = 178
    heading = items.words(72, y, room, closing['heading'], 54, tokens.WHITE, bold=True, leading=60, title=True)
    placed.append(heading)
    y += heading['h'] + 14
    placed.append(items.rect(72, y, 96, 5, fill=colours['logo_blue']))
    y += 24
    for fact in closing.get('lines') or []:
        item = items.words(72, y, room, fact, 15, tokens.WHITE, leading=22)
        placed.append(item)
        y += item['h']
    small = [
        items.words(72, 0, room if picture else width - 144, fact, 9.5, colours['silver'], leading=14)
        for fact in closing.get('small') or []
    ]
    y = height - 36 - sum(item['h'] for item in small)
    for item in small:
        item['y'] = y
        placed.append(item)
        y += item['h']
    return placed + (draft_items() if draft else [])
