"""A commission: `{type, value}` (plan.md §4.6, §5.6; H1). One parser for the deal's agreed rates, intake's in-force
commission (`CurrentCoverage.commission`) and the agency default; one label.

Ported from old Vantage 891f1b3 `benefits/market/validation.py` (`parse_comp`, `comp_label`), with one change the plan
makes: the value is kept as the exact decimal the person typed, never `%g`, so `1000000` and `12345.67` stay exact.
Nothing here rounds (rule 5): a label shows the stored digits, padded to cents when it has one decimal place.
"""

from decimal import Decimal, InvalidOperation

PCT, FLAT, PEPM = 'pct', 'flat', 'pepm'
TYPES = [(PCT, 'Percentage of premium'), (FLAT, 'Flat dollars per year'), (PEPM, 'Dollars per employee per month')]
TYPE_KEYS = tuple(key for key, _ in TYPES)
# The old CompInput's type buttons and the unit after the box (891f1b3 `commissions/CompInput.jsx`), and its hints.
SHORT = {PCT: '%', FLAT: '$', PEPM: 'PEPM'}
UNIT = {PCT: '', FLAT: '/yr', PEPM: '/EE/mo'}
EXAMPLE = {PCT: '5', FLAT: '5000', PEPM: '32'}

UNKNOWN_TYPE = 'Type must be percentage, flat, or PEPM'
NOT_A_NUMBER = 'Must be a number'
NEGATIVE = 'Must not be negative'
OVER_100 = 'Must be between 0 and 100'
REQUIRED = 'Required'


def _plain(number):
    """The decimal as plain text, without an exponent or trailing zeros: Decimal('5.50') → '5.5'."""
    text = format(number, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text or '0'


def parse_comp(raw, allow_blank=True):
    """(comp, error). A bare number or text (`5`, `"5%"`) is a percentage; a dict `{type, value}` names its type.
    `$`, `%` and `,` are ignored. A blank is `(None, None)` when allowed, else `(None, 'Required')`."""
    if raw is None or raw == '' or raw == {}:
        return (None, None) if allow_blank else (None, REQUIRED)
    if isinstance(raw, dict):
        comp_type = str(raw.get('type') or PCT).strip().lower()
        value = raw.get('value')
    elif isinstance(raw, (str, int, float, Decimal)) and not isinstance(raw, bool):
        comp_type, value = PCT, raw
    else:
        return None, NOT_A_NUMBER
    if comp_type not in TYPE_KEYS:
        return None, UNKNOWN_TYPE
    text = str(value if value is not None else '').replace('%', '').replace('$', '').replace(',', '').strip()
    if not text:
        return (None, None) if allow_blank else (None, REQUIRED)
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None, NOT_A_NUMBER
    if not number.is_finite():
        return None, NOT_A_NUMBER
    if number < 0:
        return None, NEGATIVE
    if comp_type == PCT and number > 100:
        return None, OVER_100
    return {'type': comp_type, 'value': _plain(number)}, None


def _dollars(number):
    whole, _, cents = _plain(number).partition('.')
    grouped = f'{int(whole):,}'
    if not cents:
        return f'${grouped}'
    return f'${grouped}.{cents.ljust(2, "0")}'


def comp_label(comp):
    """'5%', '$5,000/yr', '$32 PEPM' ('$32.50 PEPM' when not whole); '' for none or a value that is not a number."""
    if not comp or not isinstance(comp, dict):
        return ''
    try:
        number = Decimal(str(comp.get('value') or '').replace(',', '') or '0')
    except InvalidOperation:
        return ''
    comp_type = comp.get('type') or PCT
    if comp_type == PCT:
        return f'{_plain(number)}%'
    if comp_type == PEPM:
        return f'{_dollars(number)} PEPM'
    return f'{_dollars(number)}/yr'


def meta():
    return [
        {'key': key, 'label': label, 'short': SHORT[key], 'unit': UNIT[key], 'example': EXAMPLE[key]}
        for key, label in TYPES
    ]
