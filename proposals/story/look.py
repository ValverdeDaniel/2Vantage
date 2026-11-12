"""The story's type, words and tables in the deck's look (plan.md §9.5; old Vantage 891f1b3 `proposal_pdf._styles`,
`_table`, `_heads`, `_money`, `_signed`, `_long_date` under the Presentation format). Pure.

Every page module builds its flowables through these, so a size or a colour is decided once: the intro and the
rationale read across a room (14 and 13 pt), a note sits at the table floor (8 pt), a table's cells start at 12 pt.
Figures are formatted by `proposals.formatting`, the one formatter of client documents; a blank prints "—".
"""

import datetime

from reportlab.platypus import Spacer

from .. import formatting
from ..layout import flowables, furniture, table, tokens
from ..layout import text as words

CELL = tokens.TABLE_TYPE['cell']


def colours_of(facts):
    return furniture.palette(facts['agency']['brand'])


# --- Words ----------------------------------------------------------------------------------------------------------
def money(number):
    return formatting.money(number) if number is not None else '—'


def signed(number):
    return formatting.signed_money(number) if number is not None else '—'


def pct(number):
    return formatting.pct(number) if number is not None else '—'


def long_date(value):
    """'January 2, 2027', or '' for anything that is not a date."""
    try:
        return f'{value:%B} {value.day}, {value.year}'
    except (AttributeError, TypeError, ValueError):
        return ''


def iso_date(text):
    try:
        return datetime.date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


# --- Flowables ------------------------------------------------------------------------------------------------------
def title(text, line=None, fit=None):
    return flowables.Title(text, line=line, fit=fit)


def note(text):
    return flowables.Note(text)


def para(text, kind, colours, bold=False, align='l', space_before=None, space_after=None):
    """A paragraph in one of the story's text styles (`tokens.TEXT`): intro, rationale, caption, sub, note, value. Its
    space above and below is the style's own (`tokens.TEXT_SPACE`) unless given."""
    size, leading = tokens.TEXT[kind]
    ink = colours['ink2'] if kind in ('note', 'sub') else colours['navy'] if kind == 'caption' else colours['ink']
    runs = [words.run(text, size, ink, bold or kind == 'caption')]
    before, after = _space(kind, space_before, space_after)
    return flowables.Text(runs, leading=leading, align=align, space_before=before, space_after=after)


def lead_para(lead, text, kind, colours, space_before=None):
    """A paragraph opening with a bold lead ("Why we recommend it. …")."""
    size, leading = tokens.TEXT[kind]
    runs = [words.run(f'{lead} ', size, colours['ink'], True), words.run(text, size, colours['ink'])]
    before, after = _space(kind, space_before, None)
    return flowables.Text(runs, leading=leading, space_before=before, space_after=after)


def _space(kind, before, after):
    found = tokens.TEXT_SPACE[kind]
    return (found[0] if before is None else before), (found[1] if after is None else after)


def gap(height):
    return Spacer(1, height)


def block(placed, height=None):
    return flowables.Block(placed, height)


# --- Tables ---------------------------------------------------------------------------------------------------------
def heads(labels, colours, size=None, center_from=1):
    """A header row: white bold labels, centred from column `center_from`. At the table's own type (12 pt, its 1.2
    leading) unless the page sets a size, which leads at 1.25 × (old `_heads`)."""
    leading = round(size * tokens.HEAD_LEADING, 2) if size else None
    size = size or CELL
    cells = [
        table.cell(label, size, '#ffffff', bold=True, align='c' if number >= center_from else 'l', leading=leading)
        for number, label in enumerate(labels)
    ]
    return {'kind': 'head', 'cells': cells}


def row(texts, colours, size=CELL, center_from=1, bold_first=True, kind='plain', bold=False, leading=None):
    """A body row of plain texts: the first cell bold (the row's name), the figures centred."""
    cells = []
    for number, text in enumerate(texts):
        first = number == 0
        ink = colours['ink']
        strong = (first and bold_first) or bold
        align = 'c' if number >= center_from else 'l'
        cells.append(table.cell(text, size, ink, bold=strong, align=align, leading=leading))
    return {'kind': kind, 'cells': cells}


def grid(rows, widths, colours, pad=3.5, current=(), picked=(), h_align='LEFT', zebra=True):
    return table.Table(rows, widths, colours, pad=pad, current=current, picked=picked, h_align=h_align, zebra=zebra)


def shares(parts, room=tokens.BODY_W):
    """Column widths from shares of the body's width, scaled to fill it."""
    total = sum(parts)
    return [room * part / total for part in parts]
