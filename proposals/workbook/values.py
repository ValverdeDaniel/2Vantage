"""How one plan value is written into the client spreadsheet (plan.md §9.4; old `value_format` and
`presentation_workbook.design_cell` at 891f1b3, D-077).

Rates keep the decimals they were stored with (at least two, at most four): $797.05, $0.085. Design amounts and every
total are whole dollars, half up (quotes' `round_money`). A value is written by what it IS (its field), never by what
it looks like. Text prints as `proposals.formatting.value` prints it on every client document. The SBC link is a link,
never a benefit row: `sbc_link` is the one rule for which addresses may print.
"""

from decimal import Decimal, InvalidOperation

from quotes import fields
from quotes import math as m

from .. import formatting
from . import styles as s
from .cells import clean

# Every money key that is a RATE (old CENTS_KEYS): the tier rates, the employer contributions beside them, the unit
# rate, the stop-loss premium parts and factor, and the TPA fee. Group totals and design amounts are whole dollars.
CENTS_KEYS = frozenset(
    {
        *fields.TIER_RATE_KEYS,
        *fields.CONTRIB_KEYS,
        'unit_rate',
        'sl_spec_rate',
        'sl_agg_rate',
        'sl_other_load',
        'sl_agg_factor',
        'tpa_admin_fee',
    }
)
MONEY_TYPES = ('amount', 'rate', 'rate4')
MIN_PLACES, MAX_PLACES = 2, 4
SBC_KEY = 'sbc_url'
SBC_URL_MAX = 255
_HUGE = Decimal('1e15')


def number(raw):
    """A stored value as a usable Decimal, or None (blank, carrier text such as "TBD", or absurdly large)."""
    found = m.decimal(raw)
    if found is None or not found.is_finite() or abs(found) >= _HUGE:
        return None
    return found


def _stored_places(raw):
    found = number(raw)
    if found is None:
        return 0
    try:
        exponent = found.normalize().as_tuple().exponent
    except InvalidOperation:
        return 0
    return -exponent if isinstance(exponent, int) and exponent < 0 else 0


def money_places(raw, key):
    """Decimal places a money value prints with: 0 outside CENTS_KEYS; a rate's stored places, within 2..4."""
    if key not in CENTS_KEYS:
        return 0
    return min(MAX_PLACES, max(MIN_PLACES, _stored_places(raw)))


def rate_format(raw, key):
    return s.rate_format(money_places(raw, key))


def text(key, raw):
    """A value as text, as every client document prints it ('' for blank)."""
    if raw in (None, ''):
        return ''
    return clean(formatting.value(key, raw)).strip()


def design_cell(key, raw):
    """How one design value is written: (kind, value, number format).
    - blank: ('empty', None, None), never a dash; a stored '0' is a value;
    - money that reads as a number: a rate keeps its stored decimals, any other amount is whole dollars, half up;
    - a percentage that reads as a number: the fraction (stored 20 is 0.2) with the stored decimals, at most two;
    - anything else: text, as `text` prints it."""
    if not str(raw if raw is not None else '').strip():
        return ('empty', None, None)
    kind = fields.BY_KEY[key]['type'] if key in fields.BY_KEY else 'text'
    found = number(raw)
    if found is not None and kind in MONEY_TYPES:
        if key in CENTS_KEYS:
            return ('number', found, rate_format(raw, key))
        return ('number', m.round_decimal(found), s.MONEY_WHOLE)
    if found is not None and kind == 'percent':
        return ('number', found / 100, s.pct_format(_stored_places(raw)))
    return ('text', text(key, raw), s.TEXT)


def sbc_link(value):
    """The SBC link a plan's cell may put on a client document, or '': an http(s) address, one token with no space or
    quote, at most SBC_URL_MAX characters. Anything else is left out rather than mended."""
    found = clean(value).strip()
    if (
        not found
        or len(found) > SBC_URL_MAX
        or any(ch.isspace() for ch in found)
        or '"' in found
        or not found.lower().startswith(('https://', 'http://'))
    ):
        return ''
    return found
