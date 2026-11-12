"""The firm's own pages (plan.md §9.5; J125, J138's bios; old Vantage 891f1b3 `proposal_presentation._about_page`,
`_team_pages`, `_bio_pages`). Pure.

About the firm: its own words on a navy card, its figures on tiles beside it (at most six). Your team: up to four
cards a row and eight a page, each with the person's photo (or their initials), name, title, phone and email under
the group they work in. A bio page for each person with a bio, in the appendix. Every page stays out until the firm
writes it (OQ41): nothing here is ever filled in for the firm.
"""

from ..layout import cards, items, tokens
from ..layout import text as words
from . import look

MAX_TEAM_CARDS = 4  # a row; two rows a page
BODY_W = tokens.BODY_W


def about(facts):
    text = facts['firm']['about']
    if not text:
        return []
    colours = look.colours_of(facts)
    stats = facts['firm']['stats']
    card_w = 400 if stats else BODY_W
    size, leading = 15, 21
    inner = card_w - 56
    while size > 11 and len(words.lines_of([words.run(text, size, '#fff')], inner)) * leading > 340:
        size -= 1
        leading -= 1
    height = 410
    placed = [
        items.rect(0, 0, card_w, height, fill=colours['navy'], r=14),
        items.words(28, 30, inner, text, size, tokens.WHITE, leading=leading),
    ]
    if stats:
        left = card_w + 28
        cols = 2 if len(stats) <= 4 else 3
        rows = -(-len(stats) // cols)
        gap = 14
        width = (BODY_W - left - gap * (cols - 1)) / cols
        tall = (height - gap * (rows - 1)) / rows
        for number, stat in enumerate(stats):
            placed += cards.tile(
                left + (number % cols) * (width + gap),
                (number // cols) * (tall + gap),
                width,
                tall,
                str(stat.get('value') or ''),
                str(stat.get('label') or ''),
                colours,
                sub=str(stat.get('note') or ''),
                size=30,
            )
    name = facts['agency']['name'] or 'us'
    return [[look.title(f'About {name}'), look.block(placed, height + 4)]]


def _card(member, x, y, width, card_h, side, colours):
    placed, top = [], y
    group = member.get('group')
    if group:
        placed.append(items.rect(x, top, width, 24, fill=colours['blue'], r=3))
        placed.append(
            items.words(x + 6, top + 6, width - 12, group, 11, tokens.WHITE, bold=True, align='c', leading=13)
        )
        top += 32
    placed += cards.photo(member, x + (width - side) / 2, top, side, colours)
    top += side + 10
    soft = colours['ink2']
    for text, size, ink, bold in (
        (member.get('name'), 14, colours['navy'], True),
        (member.get('title'), 11.5, soft, False),
        (member.get('phone'), 11, soft, False),
        (member.get('email'), 11, soft, False),
    ):
        if not text:
            continue
        item = items.words(x + 2, top, width - 4, text, size, ink, bold=bold, align='c')
        placed.append(item)
        top += item['h'] + 1
    return placed


def team(facts):
    people = facts['team']
    if not people:
        return []
    colours = look.colours_of(facts)
    pages = []
    for start in range(0, len(people), MAX_TEAM_CARDS * 2):
        members = people[start : start + MAX_TEAM_CARDS * 2]
        cols = min(MAX_TEAM_CARDS, len(members))
        rows = -(-len(members) // cols)
        gap = 18
        width = min((BODY_W - gap * (cols - 1)) / cols, 280)
        card_h = (410 - gap * (rows - 1)) / rows
        side = min(width - 40, card_h - 112, 180)
        left = (BODY_W - cols * width - gap * (cols - 1)) / 2  # a small team sits centred
        placed = []
        for number, member in enumerate(members):
            x = left + (number % cols) * (width + gap)
            y = (number // cols) * (card_h + gap)
            placed += _card(member, x, y, width, card_h, side, colours)
        pages.append([look.title('Your team'), look.block(placed, 414)])
    return pages


def bios(facts):
    colours = look.colours_of(facts)
    pages = []
    for member in facts['team']:
        bio = (member.get('bio') or '').strip()
        if not bio:
            continue
        side = 210
        placed = cards.photo(member, 0, 6, side, colours, r=18)
        name = items.words(0, side + 18, side, member.get('name') or '', 15, colours['navy'], bold=True, align='c')
        placed.append(name)
        if member.get('title'):
            placed.append(
                items.words(0, side + 18 + name['h'] + 3, side, member['title'], 11.5, colours['ink2'], align='c')
            )
        placed.append(items.words(side + 36, 6, BODY_W - side - 36, bio, 14, colours['ink'], leading=20))
        pages.append([look.title(member.get('name') or 'Your team'), look.block(placed, 360)])
    return pages
