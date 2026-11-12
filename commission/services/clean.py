"""Cleaning what a person types into a booked record (plan.md §7.10; H54, H55, H58): one function per kind of value,
each returning the stored form or a sentence. The services raise 400 with every error at once, keyed by field."""

from datetime import date
from decimal import Decimal, InvalidOperation

from rest_framework.exceptions import ValidationError

from deals import comp as comps

from .. import vocab

MAX_ID = 2**63 - 1
TEXT_LIMITS = {'carrier': 200, 'plan_label': 300, 'policy_number': 100}
BAD_MONEY = 'Enter an amount in dollars, or leave it blank.'
BAD_COUNT = 'Enter a whole number of people, or leave it blank.'
BAD_DATE = 'Enter a date (YYYY-MM-DD), or leave it blank.'
BAD_PCT = 'Enter a percentage from 0 to 100.'
BAD_STATUS = 'Pick a status.'
FIELDS = (
    'premium_annual',
    'rate',
    'employees',
    'plan_label',
    'policy_number',
    'carrier',
    'effective_date',
    'term_end',
    'status',
    'notes',
)


def money(raw):
    """(text at cents, error): "$12,345.6" → "12345.60"; blank → ''."""
    text = str(raw if raw is not None else '').replace('$', '').replace(',', '').strip()
    if not text:
        return '', None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None, BAD_MONEY
    if not value.is_finite() or value < 0 or value >= Decimal('1e12'):
        return None, BAD_MONEY
    return format(value.quantize(Decimal('0.01')), 'f'), None


def count(raw):
    if raw in (None, ''):
        return '', None
    if isinstance(raw, bool):
        return None, BAD_COUNT
    try:
        value = int(str(raw).strip())
    except ValueError:
        return None, BAD_COUNT
    return (value, None) if 0 <= value <= 1_000_000 else (None, BAD_COUNT)


def day(raw):
    """A date from ISO text, or None."""
    try:
        return date.fromisoformat(str(raw)) if raw else None
    except ValueError:
        return None


def iso_day(raw):
    if raw in (None, ''):
        return '', None
    found = day(raw)
    return (found.isoformat(), None) if found and 1900 < found.year < 2200 else (None, BAD_DATE)


def percent(raw):
    """(Decimal, error) for a share typed as a percentage, 0–100, at most 4 decimals."""
    try:
        value = Decimal(str(raw).replace('%', '').strip())
    except (InvalidOperation, ValueError):
        return None, BAD_PCT
    if not value.is_finite() or value < 0 or value > 100 or value != value.quantize(Decimal('0.0001')):
        return None, BAD_PCT
    return value, None


def record_id(raw, field):
    if isinstance(raw, int) and not isinstance(raw, bool) and 0 < raw <= MAX_ID:
        return raw
    if isinstance(raw, str) and raw.isdigit() and 0 < int(raw) <= MAX_ID:
        return int(raw)
    raise ValidationError({field: ['Not a valid id.']})


def _text(key, raw, errors):
    text = ' '.join(str(raw or '').split())
    if len(text) > TEXT_LIMITS[key]:
        errors[key] = [f'Keep it under {TEXT_LIMITS[key]} characters.']
    return text


def record_changes(changes):
    """({fact: stored value | '' to clear}, notes text | None) from a PATCH body; 400 with every error at once."""
    if not isinstance(changes, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    errors, facts, notes = {}, {}, None
    for key in set(changes) - set(FIELDS):
        errors[key] = ['Not a field of a booked record.']
    for key in ('premium_annual',):
        if key in changes:
            facts[key], error = money(changes[key])
            if error:
                errors[key] = [error]
    if 'employees' in changes:
        facts['employees'], error = count(changes['employees'])
        if error:
            errors['employees'] = [error]
    if 'rate' in changes:
        found, error = comps.parse_comp(changes['rate'], allow_blank=True)
        if error:
            errors['rate'] = [error]
        facts['rate'] = found or ''
    for key in TEXT_LIMITS:
        if key in changes:
            facts[key] = _text(key, changes[key], errors)
    for key in ('effective_date', 'term_end'):
        if key in changes:
            facts[key], error = iso_day(changes[key])
            if error:
                errors[key] = [error]
    if 'status' in changes:
        if changes['status'] not in vocab.STATUS_KEYS:
            errors['status'] = [BAD_STATUS]
        facts['status'] = changes['status']
    if 'notes' in changes:
        notes = str(changes['notes'] or '').strip()
        if len(notes) > vocab.LIMITS['notes']:
            errors['notes'] = [f'Keep it under {vocab.LIMITS["notes"]} characters.']
    if errors:
        raise ValidationError(errors)
    return facts, notes
