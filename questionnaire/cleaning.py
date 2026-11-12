"""The write whitelist (plan.md §6.8; G16, G18). Pure: `clean_batch` turns a batch of typed answers into the values to
store, and reports every one it drops.

- an unknown slot, block, row or field, an auto field (a row number) or a list is dropped as `unknown`;
- a number, money or percent answer that is not one number is dropped as `not_number`;
- a choice (or Yes/No) the form does not offer now is dropped as `not_offered`, with the options it does offer: the
  option tables live on the server, so a condition the cascade never offered cannot be saved;
- a text over `TEXT_LIMIT` characters is dropped as `too_long`;
- plain fields apply before dependent ones, so a category and its condition in one batch validate together;
- a US date ("3/14/1980") becomes ISO; anything else typed in a date box stays as typed (it is still their answer);
- a picker with `pair_with` sets its twin (SIC code and description), unless the batch sets the twin itself.
`None` or '' clears a slot. An unchanged value is left to `deals.values.apply`, which writes nothing for it.
"""

import re
from datetime import date

from . import slots
from .engine.conditions import number
from .engine.options import paired_value, resolve_options
from .engine.spec import field_spec, get_block

NUMERIC = ('number', 'money', 'percent')
TEXT_LIMIT = 2000
US_DAY = re.compile(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4}|\d{2})$')
YES = {'yes', 'y', 'true'}
NO = {'no', 'n', 'false'}


def iso_day(text, today=None):
    """ "3/14/1980" → "1980-03-14"; a two-digit year pivots on next year (old Vantage's D-208 rule)."""
    found = US_DAY.match(text)
    if not found:
        return text
    month, day, year = (int(part) for part in found.groups())
    if year < 100:
        pivot = (today or date.today()).year % 100 + 1
        year += 2000 if year <= pivot else 1900
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return text


def _clean_one(form, block, field, raw, row_values):
    """(value, None) or (None, (reason, options))."""
    text = ' '.join(str(raw).split()) if field.get('type') != 'text' else str(raw).strip()
    if not text:
        return '', None
    kind = field.get('type')
    if kind == 'text' and len(text) > TEXT_LIMIT:
        return None, ('too_long', None)
    if kind in NUMERIC:
        return (text, None) if number(text) is not None else (None, ('not_number', None))
    if kind == 'date':
        return iso_day(text), None
    if kind == 'yesno':
        word = text.lower()
        if word in YES:
            return 'Yes', None
        if word in NO:
            return 'No', None
        return None, ('not_offered', ['Yes', 'No'])
    if kind == 'choice':
        offered = resolve_options(form, block, row_values, field['key'])
        match = next((option for option in offered if option == text), None)
        if match is None:
            match = next((option for option in offered if str(option).lower() == text.lower()), None)
        if match is None:
            return None, ('not_offered', list(offered)[:40])
        return match, None
    return text, None


def _parsed(form, incoming, row_ids, dropped):
    out = []
    for slot, raw in incoming.items():
        found = slots.parse(slot)
        block, row_id, field_key = found if found else ('', 0, '')
        if found is None or (block and get_block(form, block) is None):
            dropped.append({'slot': str(slot)[:120], 'reason': 'unknown'})
            continue
        if block and row_id not in row_ids.get(block, ()):
            dropped.append({'slot': slot, 'reason': 'unknown_row'})
            continue
        field = field_spec(form, block, field_key)
        if field is None or field.get('auto') or isinstance(raw, (list, dict)):
            dropped.append({'slot': slot, 'reason': 'unknown'})
            continue
        out.append((slot, block, row_id, field, '' if raw is None else raw))
    out.sort(key=lambda item: bool(item[3].get('depends_on')))  # plain fields first
    return out


def clean_batch(form, view, rows, incoming):
    """(cleaned {slot: value | ''}, dropped [{slot, reason, options?}]).

    `view` is the engine's view of the effective values now (`values.shown`), `rows` the form's rows ({block: [{id,
    …}]}). Each answer is checked against its row as this batch leaves it."""
    scalars, by_block = view
    working = {'': dict(scalars)}
    for block, block_rows in by_block.items():
        for row_id, values in block_rows:
            working[(block, row_id)] = dict(values)
    row_ids = {block: {row['id'] for row in block_rows} for block, block_rows in rows.items()}
    dropped, cleaned = [], {}
    parsed = _parsed(form, incoming, row_ids, dropped)
    explicit = {slot for slot, *_ in parsed}
    for slot, block, row_id, field, raw in parsed:
        row_values = working.setdefault((block, row_id) if block else '', {})
        value, refusal = _clean_one(form, block, field, raw, row_values)
        if refusal:
            reason, offered = refusal
            dropped.append({'slot': slot, 'reason': reason, **({'options': offered} if offered is not None else {})})
            continue
        cleaned[slot] = value
        row_values[field['key']] = value
        partner = field.get('pair_with')
        partner_slot = slots.key(block, row_id, partner) if partner else ''
        if partner and partner_slot not in explicit:
            twin = paired_value(form, block, field['key'], value)
            if twin is not None:
                cleaned[partner_slot] = twin
                row_values[partner] = twin
    return cleaned, dropped
