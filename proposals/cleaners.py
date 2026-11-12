"""What each proposal setting may hold (plan.md §6.11; J.6.2): one cleaner per kind of value. Pure.

`config.clean` picks the cleaner for a path; each answers the cleaned value or raises `Invalid` with the sentence the
400 shows. Ported from old Vantage 891f1b3 `pipeline/composition.py` (`clean_composition`, `clean_output`,
`clean_table_note`, `clean_exec_summary`, `clean_markets`, `clean_experience`): an unknown key in a list is dropped as
the old cleaner did, and text is trimmed to its limit rather than refused.
"""

import re

from deals import lines
from quotes import math as m

from . import catalog
from .summary_blocks import catalog as blocks

DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
IDENTITY = re.compile(r'[a-z0-9_:]{1,64}')


class Invalid(ValueError):
    """A value or path refused; the message is shown as is (400)."""

    def __init__(self, path, message):
        self.path, self.message = path, message
        super().__init__(message)


def line(path, key):
    if key not in lines.BY_KEY:
        raise Invalid(path, f'"{key}" is not a line of coverage.')
    return key


def text(path, value, limit):
    if value is None:
        return ''
    if not isinstance(value, str):
        raise Invalid(path, 'Send text.')
    return value.strip()[:limit]


def switch(path, value):
    if not isinstance(value, bool):
        raise Invalid(path, 'Send true or false.')
    return value


def table_note(value):
    """Spaces collapsed within each line, blank lines dropped, ≤4 lines and ≤600 characters ('' is no note)."""
    rows = [' '.join(part.split()) for part in value.replace('\r\n', '\n').split('\n')]
    rows = [row for row in rows if row][: catalog.TABLE_NOTE_LINES]
    return '\n'.join(rows)[: catalog.TABLE_NOTE_MAX].strip()


def field_keys(path, value, limit, allowed):
    """A de-duplicated list of the line's field keys (an unknown one is dropped, as the old cleaner did), or None."""
    if value is None:
        return None
    if not isinstance(value, list):
        raise Invalid(path, 'Send a list of field keys, or null.')
    out = []
    for item in value:
        key = str(item or '').strip()
        if key in allowed and key not in out:
            out.append(key)
    return out[:limit]


def order(path, value):
    if value is None:
        return []
    if not isinstance(value, list):
        raise Invalid(path, 'Send the lines in order.')
    out = []
    for key in value:
        if line(path, str(key)) not in out:
            out.append(str(key))
    return out


def _date(path, value):
    when = str(value or '').strip()
    if when and not DATE.fullmatch(when):
        raise Invalid(path, f'"{when}" is not a date (YYYY-MM-DD).')
    return when


def _rows(path, value, limit, what):
    if value is None:
        return []
    if not isinstance(value, list):
        raise Invalid(path, f'Send the {what} as a list.')
    for item in value:
        if not isinstance(item, dict):
            raise Invalid(path, f'Each of the {what} is an object.')
    return value[:limit]


def next_steps(path, value):
    """≤8 rows of {date, text}; a row with no text is dropped (J67; the old NextStepsCard)."""
    steps = []
    for item in _rows(path, value, catalog.MAX_NEXT_STEPS, 'next steps'):
        words = str(item.get('text') or '').strip()[: catalog.MAX_STEP_TEXT]
        when = _date(path, item.get('date'))
        if words:
            steps.append({'date': when, 'text': words})
    return steps


def _amount(path, raw):
    """A typed dollar figure ("$1,234,000") as a number, or None when blank."""
    if raw in (None, ''):
        return None
    found = m.decimal(raw)
    if found is None:
        raise Invalid(path, f'Could not read "{raw}" as an amount.')
    return m.plain(found)


def experience_rows(path, value):
    """≤6 periods of {period, premium, claims}; a row with no period is dropped (J45; the old PresentationPagesCard).
    Totals only: the producer's own words and two figures, never a person (Daniel, 2026-11-02)."""
    out = []
    for item in _rows(path, value, catalog.MAX_EXPERIENCE_ROWS, 'periods'):
        period = str(item.get('period') or '').strip()[: catalog.MAX_PERIOD]
        if period:
            out.append(
                {
                    'period': period,
                    'premium': _amount(path, item.get('premium')),
                    'claims': _amount(path, item.get('claims')),
                }
            )
    return out


def summary_blocks(path, value):
    """[{key, line?}], ≤24, known keys only; a line-only block takes no pin (J64). [] is the standard set again."""
    out = []
    for item in _rows(path, value, blocks.MAX_BLOCKS, 'summary blocks'):
        key = str(item.get('key') or '')
        if key not in blocks.BLOCKS:
            continue
        pin = str(item.get('line') or '')
        if pin and (blocks.scope(key) != blocks.LINE or key in blocks.LINE_ONLY):
            pin = ''
        spec = {'key': key, 'line': line(path, pin)} if pin else {'key': key}
        if spec not in out:
            out.append(spec)
    return out


def market_switch(path, value):
    """Show Markets checked: true, false, or null for automatic (shown once a send is recorded and a quote is back)."""
    if value is not None and not isinstance(value, bool):
        raise Invalid(path, 'Send true, false, or null for automatic.')
    return value


def carrier_id(path, value):
    """A carrier's identity as Markets checked names it (`deals.carriers.identity`)."""
    found = str(value or '')
    if not IDENTITY.fullmatch(found):
        raise Invalid(path, f'"{found}" is not a carrier on Markets checked.')
    return found


def hidden_carriers(path, value):
    if value is None:
        return []
    if not isinstance(value, list):
        raise Invalid(path, 'Send the hidden carriers as a list.')
    out = []
    for item in value[: catalog.MAX_HIDDEN]:
        found = carrier_id(path, item)
        if found not in out:
            out.append(found)
    return sorted(out)


def compare_slots(path, value):
    if value not in catalog.COMPARE_SLOTS or isinstance(value, bool):
        raise Invalid(path, f'Compare holds {", ".join(str(n) for n in catalog.COMPARE_SLOTS)} columns.')
    return value


def cover_image(path, value):
    """The cover's upload: a CoverImage id, or None for the stock picture. Whether it still exists is asked when a
    file is built (a deleted upload falls back), never here (old `composition.clean_output`)."""
    if value is None or value == '':
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise Invalid(path, "Send the cover image's id, or null.")
    return value


def picture(path, place, value):
    """A dark page's picture: a stock key, "upload:<id>" (any place but the cover, whose upload is
    `output.cover.image`), or None for no picture (J35; old `stock_images.clean_pictures`)."""
    if value is None or value in catalog.STOCK_KEYS:
        return value
    if place != 'cover' and catalog.upload_id(value):
        return f'{catalog.UPLOAD_PREFIX}{catalog.upload_id(value)}'
    raise Invalid(path, 'Pick one of the pictures, an upload, or none.')


def team(path, value):
    """The people on this client's team, in order: member ids (≤40), or None for everyone on by default (J43). An id
    no longer on the firm's team is left out when the files are built."""
    if value is None:
        return None
    if not isinstance(value, list):
        raise Invalid(path, "Send the team as a list of people's ids, or null.")
    out = []
    for item in value[: catalog.MAX_TEAM]:
        if isinstance(item, bool) or not isinstance(item, int) or item <= 0:
            raise Invalid(path, "Send the team as a list of people's ids, or null.")
        if item not in out:
            out.append(item)
    return out
