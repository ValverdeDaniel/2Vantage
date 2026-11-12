"""The money of priced versions (plan.md §5.4, §5.5; F77, F78, F80; the old concessions.py math). Pure, in Decimal.

- `change_rate(base, op, value)`: one operation on one number: % off or up, $ off or up, or set to.
- `rate_text(key, amount, inputs)`: a worked-out rate as the text a plan stores, half up: a `rate` field to the cent;
  a `rate4` field (unit rates) keeps the decimals its inputs were stated in, two to four (5% off $0.085 stores 0.081,
  never 0.08; the old D-077, D-108).
- `concession(values, ops)` and `bundle(values, rate_keys, pct, flat)`: the version's changed values, {key: text}. A
  relative change on a number the original never stated is skipped; a result below zero raises `BelowZero` ("$200 off
  a $150 rate" must refuse, never write −$50). A bundle's percentage and dollars compose as
  rate × (1 − pct/100) − flat; the dollars never touch the quoted group premium ("$10 off every tier" is not "$10 off
  the group's monthly bill").
- `bundle_totals(parts)`: the one place a bundle's parts are read as numbers (F.5 #2): percentages off add, up
  subtract, and the same for dollars.
- `net_after_credit(...)`: a premium holiday's credit off the version's year (F80, F117): whole dollars, half up; a
  credit in free months is that many months of the version's own premium; no net when the credit is larger than the
  year or the version has no price.
"""

from decimal import Decimal

from .. import fields
from .premium import change
from .rounding import decimal, plain, round_decimal

QUOTED = 'group_premium_monthly'
HUNDRED = Decimal(100)


class BelowZero(ValueError):
    """A change that would store a negative rate: `key` and the amount it would have stored."""

    def __init__(self, key, amount):
        super().__init__(key)
        self.key, self.amount = key, amount


def change_rate(base, op, value):
    """The number after one operation, or None for a relative change on a number never stated."""
    if op == 'set':
        return value
    if base is None:
        return None
    if op == 'pct_off':
        return base * (1 - value / HUNDRED)
    if op == 'pct_up':
        return base * (1 + value / HUNDRED)
    if op == 'flat_off':
        return base - value
    return base + value  # flat_up


def _stated(number):
    """The decimals a number was stated in, trailing zeros aside."""
    exponent = number.normalize().as_tuple().exponent
    return -exponent if isinstance(exponent, int) and exponent < 0 else 0


def _places(key, inputs):
    if fields.BY_KEY.get(key, {}).get('type') != 'rate4':
        return 2
    stated = [max(2, _stated(number)) for number in inputs if number is not None]
    return min(4, max(stated) if stated else 2)


def _text(rounded):
    text = format(rounded, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return '0' if text in ('-0', '') else text


def rate_text(key, amount, inputs=()):
    """The stored text of a worked-out rate; BelowZero when it would be negative."""
    rounded = round_decimal(amount, _places(key, inputs))
    if rounded < 0:
        raise BelowZero(key, plain(rounded))
    return _text(rounded)


def _inputs(op, base, value):
    if op == 'set':
        return (value,)
    return (base, value) if op in ('flat_off', 'flat_up') else (base,)


def concession(values, ops):
    """{key: text} for the keys `ops` ([{key, op, value}], values as Decimals) change."""
    out = {}
    for item in ops:
        key, op, value = item['key'], item['op'], decimal(item['value'])
        base = decimal(values.get(key))
        result = change_rate(base, op, value)
        if result is None:
            continue
        out[key] = rate_text(key, result, _inputs(op, base, value))
    return out


def bundle_totals(parts):
    """(pct, flat) across a bundle's parts [{op, value}], each to 4 places."""
    pct = flat = Decimal(0)
    for part in parts:
        value = decimal(part['value']) or Decimal(0)
        if part['op'] == 'pct_off':
            pct += value
        elif part['op'] == 'pct_up':
            pct -= value
        elif part['op'] == 'flat_off':
            flat += value
        else:
            flat -= value
    return round_decimal(pct, 4), round_decimal(flat, 4)


def bundle(values, rate_keys, pct, flat):
    """{key: text} for a bundle's rates and the quoted group premium."""
    out = {}
    for key in [*rate_keys, QUOTED]:
        amount = decimal(values.get(key))
        if amount is None:
            continue
        result = amount * (1 - pct / HUNDRED)
        if key != QUOTED:
            result -= flat
        out[key] = rate_text(key, result, (amount, flat if flat else None))
    return out


def credit_annual(credit, monthly):
    """The credit a year in whole dollars: {annual} as given, {months} × the version's monthly premium; None when the
    credit is in months and the version has no price."""
    if credit.get('annual') is not None:
        return round_decimal(decimal(credit['annual']))
    months, monthly = decimal(credit.get('months')), decimal(monthly)
    if months is None or monthly is None:
        return None
    return round_decimal(monthly * months)


def net_after_credit(credit, monthly, annual, base_annual):
    """{annual, months, net_annual, change, reason}: the credit, the year after it and the change of that net against
    the comparison base's year (None without a base). `reason`: 'no_price' or 'credit_exceeds_year' when no net."""
    amount = credit_annual(credit, monthly)
    out = {
        'annual': plain(amount),
        'months': plain(decimal(credit.get('months'))) if credit.get('annual') is None else None,
        'net_annual': None,
        'change': None,
        'reason': None,
    }
    if annual is None or amount is None:
        out['reason'] = 'no_price'
        return out
    year = decimal(annual)
    if amount > year:
        out['reason'] = 'credit_exceeds_year'
        return out
    net = year - amount
    out['net_annual'] = plain(net)
    out['change'] = change(net, base_annual) if base_annual is not None else None
    return out
