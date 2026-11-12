"""What every content page wears (plan.md §9.5; J139): its title, 26 down to 16 pt until it fits one line; the rule
under it; the footer bar with the firm's logo (or the mark), the stamp ("<client> · Prepared <date> · Version <n>")
and the rates note; the firm's name; the page number, no "of M"; Draft until the proposal is issued (OQ35). Ported
from old Vantage 891f1b3 `proposal_furniture.title_item`, `chrome_items` and `_PresentationCanvas`. Pure.

The PowerPoint holds the same frames on its slide master (slice 31); the title is its title placeholder.
"""

from . import items, tokens
from . import text as words
from .furniture import draft_items


def title_item(text, colours):
    room = tokens.PAGE_W - 2 * tokens.PAGE_MARGIN
    largest, smallest = tokens.TITLE_TYPE
    size = largest
    while size > smallest and words.width(text, size, bold=True) > room:
        size -= 1
    top = tokens.TITLE_TOP + (tokens.TITLE_HEIGHT - size * 1.2) / 2
    return items.one_line(tokens.PAGE_MARGIN, top, text, size, colours['navy'], bold=True, title=True)


def chrome_items(title, number, chrome):
    """A content page's chrome. `chrome`: {stamp, note, firm, logo (an image src or None), draft, colours}."""
    colours = chrome['colours']
    width, height = tokens.DECK_SIZE
    top = height - tokens.FOOTER_BAR
    placed = []
    if title:
        placed.append(title_item(title, colours))
    placed += [
        items.rect(tokens.PAGE_MARGIN, tokens.TITLE_RULE_TOP, 72, 3, fill=colours['logo_blue']),
        items.rect(0, top, width, tokens.FOOTER_BAR, fill=colours['footer']),
    ]
    if chrome.get('logo'):
        placed.append(items.image(14, top + 5, 60, 16, chrome['logo'], fit='contain'))
        text_x = 84
    else:
        placed.append(items.image(14, top + 5, 20, 16, tokens.MARK, fit='contain'))
        text_x = 42
    ink2 = colours['ink2']
    if chrome.get('stamp'):
        placed.append(items.one_line(text_x, top + 4, chrome['stamp'], 7.5, ink2))
    if chrome.get('note'):
        placed.append(items.one_line(text_x, top + 14, chrome['note'], 6.5, ink2))
    if chrome.get('firm'):
        placed.append(items.one_line(width - 62, top + 8, chrome['firm'].upper(), 7.5, ink2, align='r'))
    if chrome.get('draft'):
        placed += draft_items()
    # The number sits in the footer bar's right end, bold, as the PowerPoint's slide-number field reads.
    placed.append(
        items.one_line(width - tokens.PAGE_MARGIN, height - tokens.FOOTER_BAR + 8, str(number), 8, ink2, True, 'r')
    )
    return placed
