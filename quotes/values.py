"""Cleaning a typed plan value by its field type (plan.md §5.4). Pure functions.

`clean(field, raw) -> (value, error)`: value is the stored text ('' = cleared); error is the message or None.
"""

import re

from . import fields

_NUMBER = re.compile(r'^-?\d+(\.\d+)?$')
_BLANK_RATE = {'', 'n/a', 'na', '-'}
_YES = {'yes', 'y', 'true', '1'}
_NO = {'no', 'n', 'false', '0'}


def _number_text(raw):
    text = str(raw).replace('$', '').replace(',', '').replace('%', '').strip()
    return text if _NUMBER.match(text) else None


def _format_number(text):
    """'1500.00' -> '1500', '7.50' -> '7.5', '0.185' -> '0.185'."""
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return '0' if text in ('-0', '') else text


def _decimals(text):
    return len(text.split('.', 1)[1]) if '.' in text else 0


def clean(field, raw):
    if isinstance(field, str):
        field = fields.BY_KEY[field]
    label, kind = field['label'], field['type']
    text = '' if raw is None else str(raw).strip()

    if kind == 'text':
        return text, None
    if kind in ('amount', 'percent'):
        number = _number_text(text)
        return (_format_number(number) if number is not None else text), None
    if kind in ('rate', 'rate4'):
        if text.lower() in _BLANK_RATE:
            return '', None
        number = _number_text(text)
        if number is None:
            return text, f'{label} takes a number, not "{text}"'
        places = 2 if kind == 'rate' else 4
        if _decimals(number) > places and _decimals(_format_number(number)) > places:
            unit = 'dollars and cents' if kind == 'rate' else 'a number with up to 4 decimals'
            return text, f'{label} takes {unit}, not "{text}"'
        return _format_number(number), None
    if kind == 'number':
        if not text:
            return '', None
        number = _number_text(text)
        if number is None:
            return text, f'{label} takes a number, not "{text}"'
        return _format_number(number), None
    if kind == 'yesno':
        if not text:
            return '', None
        if text.lower() in _YES:
            return 'Yes', None
        if text.lower() in _NO:
            return 'No', None
        return text, f'{label} takes Yes or No, not "{text}"'
    if kind == 'choice':
        if not text:
            return '', None
        for choice in field['choices']:
            if text.lower() in (choice['key'].lower(), choice['label'].lower()):
                return choice['key'], None
        labels = ', '.join(choice['label'] for choice in field['choices'])
        return text, f'{label} takes one of: {labels}'
    if kind == 'url':
        if not text:
            return '', None
        if text.lower().startswith(('http://', 'https://')):
            return text, None
        return text, f'{label} takes a web address starting with http:// or https://'
    return text, None


def as_float(value):
    """A stored value as a number, or None (carrier text such as "20% after deductible" is not a number)."""
    if value in (None, ''):
        return None
    text = _number_text(value)
    return float(text) if text is not None else None
