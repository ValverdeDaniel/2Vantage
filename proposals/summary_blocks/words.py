"""How the summary's figures read (old Vantage 891f1b3 `exec_summary._money`, `_pct`, `_signed_money`, `_dir`). Pure.

Formatting happens here, once, so every renderer quotes the same dollar; the rounding is quotes' (`round_decimal`,
half up like Excel, rule 5). The sign goes outside the currency symbol ("-$286") and follows the rounded value, so
-0.4 prints $0, never -$0.
"""

from quotes import math as m


def money(value, places=0):
    rounded = m.round_decimal(m.decimal(value), places)
    if rounded is None:
        return ''
    sign = '-' if rounded < 0 else ''
    return f'{sign}${abs(rounded):,.{places}f}'


def signed_money(value):
    """A change with its sign both ways: -$11,172, +$9,972, $0."""
    text = money(value)
    return f'+{text}' if text and not text.startswith('-') and text != '$0' else text


def pct(value, places=1):
    """Signed and half up: 4.25 prints +4.3%."""
    rounded = m.round_decimal(m.decimal(value), places)
    if rounded is None:
        return ''
    return f'{rounded:+.{places}f}%'


def per_month(value):
    return f'{money(value)}/mo'


def per_year(value):
    return f'{money(value)}/yr'


def direction(delta):
    """Down is good for every figure here (a lower cost, deductible, rate or liability)."""
    found = m.decimal(delta)
    if found is None:
        return ''
    if found < 0:
        return 'good'
    return 'bad' if found > 0 else 'flat'


def plural(count, one, many=None):
    return one if count == 1 else (many or f'{one}s')


def saved_or_more(annual):
    """ "$1,234 saved" or "$1,234 more"."""
    found = m.decimal(annual)
    return money(abs(found)) + (' saved' if found < 0 else ' more')


def monthly_delta(change):
    """{delta, pct} a month as "-$508/mo (-2.8%)"; '' without one."""
    if not change:
        return ''
    return f'{money(change["delta"])}/mo ({pct(change["pct"])})'
