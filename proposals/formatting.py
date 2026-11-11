"""How values print on client documents (plan.md §9.4). Pure functions."""

from quotes import fields
from quotes import values as cleaning


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
    """A stored value as the client sees it: amounts as $#,##0, percentages as 20%, text as the carrier wrote it."""
    if raw in (None, ''):
        return ''
    field = fields.BY_KEY[key]
    number = cleaning.as_float(raw)
    kind = field['type']
    if kind == 'amount' and number is not None:
        return money(number)
    if kind == 'percent' and number is not None:
        return f'{number:g}%'
    if kind == 'rate' and number is not None:
        return rate(number)
    if kind == 'rate4' and number is not None:
        return f'${raw}'
    if kind == 'choice':
        return next((c['label'] for c in field['choices'] if c['key'] == raw), raw)
    if kind == 'url':
        return 'View SBC'
    return str(raw)


def joined(values, separator):
    shown = [v for v in values if v]
    return separator.join(v or '—' for v in values) if shown else ''
