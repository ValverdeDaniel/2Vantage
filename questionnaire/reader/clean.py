"""A read's answers through the form's own cleaner (plan.md §6.8; G16, G18, G99; slice 52). Pure.

What Claude wrote goes through `cleaning.clean_batch`, the form's one write whitelist, exactly as a typed answer does:
numbers must be numbers, a picker takes only what it offers (a condition only under its own category, row by row), US
dates become ISO, and the SIC code fills its description. Before that, a picker's answer is matched to the option it
names: case and punctuation aside, a printed name to its code (the State, the SIIA coverage letter) and a SIC code to
its leading digits. A value the form will not take is counted, never kept or named (§10.8: it may be medical).
"""

import re

from .. import slots
from ..cleaning import clean_batch
from ..engine.options import resolve_options
from ..engine.spec import field_spec, section_fields
from .merge import empty

LEADING_CODE = re.compile(r'^\s*(\d{4})\b')


def _fold(text):
    return re.sub(r'[^0-9a-z]+', '', str(text).lower())


def matched(form, block, field, raw, row_values):
    """A picker's answer as one of its options when it names one, else as written."""
    text = ' '.join(str(raw).split())
    if field.get('option_mode') == 'code':
        found = LEADING_CODE.match(text)
        return found.group(1) if found else text
    printed = {_fold(shown): option for option, shown in (field.get('display_map') or {}).items()}
    if _fold(text) in printed:
        return printed[_fold(text)]
    offered = {_fold(option): option for option in resolve_options(form, block, row_values, field['key'])}
    return offered.get(_fold(text), text)


def _incoming(form, read):
    """({slot: value} with rows under ids 1..n, {block: [{values, page, low, doc}]})."""
    incoming = {}
    for key, answer in read['answers'].items():
        field = field_spec(form, '', key)
        value = answer['value']
        incoming[key] = matched(form, '', field, value, {}) if field.get('type') == 'choice' else value
    for block, rows in read['rows'].items():
        for number, row in enumerate(rows, start=1):
            done = {}
            fields = [field_spec(form, block, key) for key in row['values']]
            for field in sorted(fields, key=lambda field: bool(field.get('depends_on'))):  # parents first
                value = row['values'][field['key']]
                if field.get('type') == 'choice':
                    value = matched(form, block, field, value, done)
                done[field['key']] = value
                incoming[slots.key(block, number, field['key'])] = value
    return incoming


def clean(form, read):
    """The read as `StagedRead.read` stores it: {answers {key: {value, page, low}}, rows {block: [{values, page,
    low}]}, documents, counts {answers, rows, not_taken, unknown, twice, dropped}}, every value cleaned."""
    read = {**empty(), **read}
    rows = {block: [{'id': n} for n in range(1, len(listed) + 1)] for block, listed in read['rows'].items()}
    view = ({}, {block: [(row['id'], {}) for row in listed] for block, listed in rows.items()})
    cleaned, dropped = clean_batch(form, view, rows, _incoming(form, read))
    answers, out_rows = {}, {}
    for key, answer in read['answers'].items():
        if cleaned.get(key):
            answers[key] = {'value': cleaned[key], 'page': answer['page'], 'low': answer['low']}
    for field in section_fields(form):  # a twin the cleaner filled (the SIC code's description)
        key = field['key']
        partner = field.get('pair_with')
        if key not in answers and cleaned.get(key) and partner in answers:
            answers[key] = {**answers[partner], 'value': cleaned[key]}
    for block, listed in read['rows'].items():
        for number, row in enumerate(listed, start=1):
            prefix = slots.row_prefix(block, number)
            values = {
                slot[len(prefix) :]: value for slot, value in cleaned.items() if slot.startswith(prefix) and value
            }
            if values:
                low = [key for key in row['low'] if key in values]
                out_rows.setdefault(block, []).append({'values': values, 'page': row['page'], 'low': low})
    return {
        'answers': answers,
        'rows': out_rows,
        'documents': list(read['documents']),
        'counts': {
            'answers': len(answers),
            'rows': sum(len(listed) for listed in out_rows.values()),
            'not_taken': len(dropped),
            'unknown': read['unknown'],
            'twice': read['twice'],
            'dropped': sum(read['dropped'].values()),
        },
    }
