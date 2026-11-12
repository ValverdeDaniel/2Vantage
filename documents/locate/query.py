"""What the locator is asked and what it answers (E81, E83; plan.md §3.7 `loc`). Pure.

    FOUND    printed on the recorded page (or cell), or on another one
    DERIVED  not printed as read, but a stated rule of the reader turns a printed figure into it (100 minus a share)
    WEAK     a common figure (20, 80, $25) printed with no plan or label word on its line, or words the reader may
             have reworded
    ABSENT   nowhere in the file: the cheapest sign of a misread ("not in the file")
    NOCHECK  the file cannot say ("check by eye"): an image, a page with no text layer, a text layer that reads as
             nonsense, a value with no printed form

A `Located` names a page, or a sheet and a cell, a count and a reason code, never the file's text: it is stored on the
value as `loc` and may be shown anywhere.
"""

import re
from dataclasses import dataclass

from .fold import as_number, fold

FOUND, DERIVED, WEAK, ABSENT, NOCHECK = 'found', 'derived', 'weak', 'absent', 'nocheck'
STATES = (FOUND, DERIVED, WEAK, ABSENT, NOCHECK)
# Bumped whenever a rule changes what is found: a stored `loc` of an older version is checked again (E84).
VERSION = 1
# A file bigger than this is not searched (NOCHECK 'too_large').
MAX_PAGES = 1500
# Reasons the file itself cannot settle a value ("check by eye"), as against a value with no printed form.
FILE_REASONS = ('image', 'no_text', 'text_layer', 'unreadable', 'too_large', 'format', 'missing')

_PRINTED_NOTE = re.compile(r'\s*·\s*printed ".*$', re.S)


@dataclass
class Located:
    """Where a value is printed: a page, or a sheet and a cell. Never text."""

    state: str
    page: int = None
    sheet: str = None
    cell: str = None
    hits: int = 0
    via: str = ''
    why: str = ''
    # For DERIVED only: what was found instead of the value, so a viewer can box it. A canonical figure ("20") or one
    # of the caller's own wordings ("no charge"), never the file's text.
    printed: str = ''

    def as_dict(self):
        """Sparse: only what is known."""
        out = {'state': self.state}
        for key in ('page', 'sheet', 'cell', 'via', 'why', 'printed'):
            value = getattr(self, key)
            if value not in (None, ''):
                out[key] = value
        if self.hits:
            out['hits'] = self.hits
        return out


@dataclass
class Query:
    """One value to find.

    `alternatives` are (figure, via) pairs a reader rule could have turned into this value ("100 minus" a printed
    share); `anchors` the words that pin a common figure to this plan or this row (the plan's name, the field's
    label); `hint` the plan's carrier and name, which pick the column in a sheet. `strict` False says the reader may
    have reworded the value (a plan type, a network name): not finding it is WEAK, never ABSENT. `tolerance` lets a
    figure match one printed within that much (design dollars recorded whole). `wordings` are (printed words, via) a
    reader rule turns into this figure ("No charge" records 0), found only beside an anchor word. `snippet` is the
    line the reader typed back: printed on the page it cited, it outranks any other page (D-164)."""

    value: str
    page: int = None
    anchors: tuple = ()
    alternatives: tuple = ()
    hint: str = ''
    kind: str = ''  # '' (by the value) or 'code'
    strict: bool = True
    tolerance: float = 0.0
    wordings: tuple = ()
    snippet: str = ''


def reader_line(line):
    """The reader's line without the `· printed "…"` note the reader's normalizer appends: what the file itself
    prints. A line that is only the note leaves nothing (the old pipeline/normalize.reader_line)."""
    text = str(line or '').strip()
    if text.startswith('printed "'):
        return ''
    return _PRINTED_NOTE.sub('', text).strip()


def figures(query):
    """The value's own figure, then each alternative a reader rule allows: [(figure, via)]."""
    return ((as_number(query.value), 'number'), *query.alternatives)


def first_strong(results):
    """The first FOUND or DERIVED answer, else the first WEAK one, else None."""
    weak = None
    for result in results:
        if result is None:
            continue
        if result.state != WEAK:
            return result
        weak = weak or result
    return weak


def missing(query):
    """The answer when nothing was found: ABSENT, or WEAK for words the reader may have reworded."""
    if query.strict:
        return Located(ABSENT)
    return Located(WEAK, why='reworded')


_DATE = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})$')
_ISO_DATE = re.compile(r'^(\d{4})-(\d{1,2})-(\d{1,2})$')


def text_forms(value):
    """A worded value as it may be printed: itself, and a date in each way a carrier prints one (01/01/2026,
    1/1/2026, 1/1/26, 2026-01-01)."""
    text = fold(value)
    forms = [text]
    us, iso = _DATE.match(text), _ISO_DATE.match(text)
    if us or iso:
        if us:
            month, day, year = int(us.group(1)), int(us.group(2)), us.group(3)
        else:
            month, day, year = int(iso.group(2)), int(iso.group(3)), iso.group(1)
        if len(year) == 2:
            year = f'20{year}'
        forms += [f'{month:02d}/{day:02d}/{year}', f'{month}/{day}/{year}', f'{month}/{day}/{year[2:]}']
        forms.append(f'{year}-{month:02d}-{day:02d}')
    return list(dict.fromkeys(forms))
