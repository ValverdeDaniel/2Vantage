"""Slot keys (plan.md §6.8): a scalar answer is `field`, a row's answer `block.<row id>.field`. Row numbers are never
stored (G43): a row keeps its id however rows around it come and go, so `answers` and `sources` stay flat and
`deals.values.apply` serves them. Pure."""

import re

_ROW = re.compile(r'^([a-z_]+)\.(\d{1,6})\.([A-Za-z0-9_]+)$')
_SCALAR = re.compile(r'^[A-Za-z0-9_]+$')


def key(block, row_id, field):
    return f'{block}.{row_id}.{field}' if block else field


def parse(slot):
    """(block, row id, field) for a well-formed slot key, ('', 0, field) for a scalar, else None."""
    text = str(slot or '')
    found = _ROW.match(text)
    if found:
        return found.group(1), int(found.group(2)), found.group(3)
    if _SCALAR.match(text):
        return '', 0, text
    return None


def row_prefix(block, row_id):
    return f'{block}.{row_id}.'
