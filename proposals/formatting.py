"""How values print on client documents (plan.md §9.4; old `value_format` at 891f1b3, D-077). Pure functions.

A value is formatted by what it IS (its field), never by what it looks like. Rates (CENTS_KEYS) print the decimals
they were stored with, at least two and at most four, half up beyond four: $797.05, $4.50, $0.085. Every other money
value, design amounts and totals alike, prints whole dollars, half up (quotes' rounding, rule 5).
"""

from decimal import InvalidOperation

from quotes import fields
from quotes import math as m
from quotes import values as cleaning

# Every money key that is a RATE: the tier rates, the employer contributions beside them, the unit rate, the
# stop-loss premium parts and factor, and the TPA fee. Group totals and design amounts print whole dollars.
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


def stored_places(raw):
    """The decimals a stored number was typed with, trailing zeros dropped ('0.150' reads as 0.15)."""
    found = m.decimal(raw)
    if found is None or not found.is_finite():
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
    return min(MAX_PLACES, max(MIN_PLACES, stored_places(raw)))


def money(number):
    if number is None:
        return ''
    sign = '-' if number < 0 else ''
    return f'{sign}${abs(number):,.0f}'


def signed_money(number):
    if number is None:
        return ''
    return ('+' if number > 0 else '') + money(number)


def rate(number, places=2):
    return '' if number is None else f'${number:,.{places}f}'


def pct(number):
    return '' if number is None else f'{"+" if number > 0 else ""}{number:.1f}%'


def value(key, raw):
    """A stored value as the client sees it: money as the module says, percentages as 20%, text as typed."""
    if raw in (None, ''):
        return ''
    field = fields.BY_KEY[key]
    number = cleaning.as_float(raw)
    kind = field['type']
    if kind in MONEY_TYPES and number is not None:
        places = money_places(raw, key)
        amount = m.round_decimal(m.decimal(raw), places)
        return f'{"-" if amount < 0 else ""}${abs(amount):,.{places}f}'
    if kind == 'percent' and number is not None:
        return f'{number:g}%'
    if kind == 'choice':
        return next((c['label'] for c in field['choices'] if c['key'] == raw), raw)
    if kind == 'url':
        return 'View SBC'
    return str(raw)


def joined(values, separator):
    shown = [v for v in values if v]
    return separator.join(v or '—' for v in values) if shown else ''
