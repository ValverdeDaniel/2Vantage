"""What intake shows a client through a link, and how it cleans what comes back (plan.md §5.2, §5.8; L83–L86, L108;
B43; OQ84). Reads only; the writes are `services/client.py`.

The three blocks a link can ask besides the questions wait as one pending entry each (OQ84): `block:contacts` (the
client's contacts as they would have them), `block:coverage` (what they have in force today) and `block:lines` (the
lines they tick to shop, Ch. 6: "please shop"; unticking never takes a line off). Their stored value is what the deal
holds now, in the same shape, so an answer equal to it changes nothing. Commission, `on_proposal` and the Keep / Leave
off decisions are never shown or taken (L108): a coverage row carries its line, carrier, funding and renewal date only.
"""

from rest_framework.exceptions import ValidationError

from deals import contacts as contact_rules
from deals import lines
from deals.models import Contact

from . import client_entries as entries_rule
from . import form, values
from .models import CurrentCoverage
from .services.coverage import clean as clean_coverage_fields

CONTACTS, COVERAGE, LINES = 'block:contacts', 'block:coverage', 'block:lines'
BLOCK_SLOTS = (CONTACTS, COVERAGE, LINES)
ROW_LIMIT = 20  # contacts or coverage rows one answer may hold
CONTACT_FIELDS = ('role', 'name', 'title', 'email', 'phone')
COVERAGE_FIELDS = ('line', 'carrier', 'funding', 'renewal_date')
NOT_ROWS = 'Send a list.'
TOO_MANY = f'Send at most {ROW_LIMIT} rows.'


def contact_rows(client_id):
    rows = Contact.objects.filter(client_id=client_id, role__in=contact_rules.CLIENT_SIDE).order_by('sort_order', 'id')
    return [{'id': row.id, **{key: getattr(row, key) for key in CONTACT_FIELDS}} for row in rows]


def coverage_rows(deal_id):
    rows = CurrentCoverage.objects.filter(deal_id=deal_id, in_force=True).order_by('sort_order', 'id')
    return [
        {
            'id': row.id,
            'line': row.line,
            'carrier': row.carrier,
            'funding': row.funding,
            'renewal_date': row.renewal_date.isoformat() if row.renewal_date else '',
        }
        for row in rows
    ]


def stored_blocks(deal):
    """{slot: the value the deal holds now}, in the shape a client's answer takes."""
    return {
        CONTACTS: contact_rows(deal.client_id),
        COVERAGE: coverage_rows(deal.id),
        LINES: [key for key in lines.LINE_KEYS if key in (deal.requested_lines or [])],
    }


def stored(deal, intake):
    """{slot: stored value} for every question and block."""
    from .selectors import answers_of

    return {**answers_of(deal, intake), **stored_blocks(deal)}


def views(deal, intake, link_id, *, blank=False):
    """{slot: (shown value, base, by a colleague)} for every slot, as one link's page sees it now (L83–L85, L96)."""
    held = stored(deal, intake)
    client = (intake.client if intake else None) or {}
    sources = (intake.sources if intake else None) or {}
    out = {}
    for slot in (*form.KEYS, *BLOCK_SLOTS):
        entry = client.get(slot)
        source = sources.get(slot) if slot in form.KEYS else None
        value = held.get(slot, '' if slot in form.KEYS else [])
        out[slot] = (
            entries_rule.shown(value, entry, link_id, blank=blank),
            entries_rule.base(source, entry, link_id, blank=blank),
            entries_rule.by_colleague(entry, link_id),
        )
    return out


def _rows(raw):
    if not isinstance(raw, list) or not all(isinstance(row, dict) for row in raw):
        raise ValueError(NOT_ROWS)
    if len(raw) > ROW_LIMIT:
        raise ValueError(TOO_MANY)
    return raw


def _known_id(row, known):
    value = row.get('id')
    return value if isinstance(value, int) and not isinstance(value, bool) and value in known else None


def _contact(row, known):
    from deals.services.contacts import clean as clean_contact

    data = {key: row.get(key) for key in CONTACT_FIELDS if key in row}
    if data.get('role') not in contact_rules.CLIENT_SIDE:
        data['role'] = contact_rules.HR_ADMIN
    cleaned = clean_contact(data, partial=False)
    texts = [cleaned.get(key, '') for key in CONTACT_FIELDS if key != 'role']
    if not any(texts):
        return None
    return {'id': _known_id(row, known), 'role': cleaned['role'], **{k: cleaned.get(k, '') for k in CONTACT_FIELDS[1:]}}


def _coverage(row, known):
    data = {key: row.get(key) for key in COVERAGE_FIELDS if key in row}
    cleaned = clean_coverage_fields(data)
    if not cleaned.get('line'):
        return None
    renewal = cleaned.get('renewal_date')
    return {
        'id': _known_id(row, known),
        'line': cleaned['line'],
        'carrier': cleaned.get('carrier', ''),
        'funding': cleaned.get('funding', ''),
        'renewal_date': renewal.isoformat() if renewal else '',
    }


def _sentence(error):
    detail = error.detail if isinstance(error, ValidationError) else str(error)
    if isinstance(detail, dict):
        first = next(iter(detail.values()))
        return str(first[0] if isinstance(first, list) else first)
    return str(detail[0] if isinstance(detail, list) else detail)


def clean_block(slot, raw, known):
    """(cleaned value, None) or (None, a sentence). `known` holds the ids a row may name (the client's contacts, the
    deal's coverage rows); any other id is a new row."""
    try:
        if slot == LINES:
            if not isinstance(raw, list) or not all(isinstance(key, str) for key in raw):
                raise ValueError('Send the lines as a list.')
            if bad := [key for key in raw if key not in lines.BY_KEY]:
                raise ValueError(f'Not a line of coverage: {", ".join(bad[:3])}.')
            return [key for key in lines.LINE_KEYS if key in raw], None
        clean_row = _contact if slot == CONTACTS else _coverage
        out = []
        for number, row in enumerate(_rows(raw), start=1):
            try:
                cleaned = clean_row(row, known)
            except ValidationError as error:
                raise ValueError(f'Row {number}: {_sentence(error)}') from error
            if cleaned is not None:
                out.append(cleaned)
        return out, None
    except ValueError as error:
        return None, str(error)


def clean_answer(key, raw):
    """(cleaned, None) or (None, the sentence) for one question, by the one cleaner (§5.2)."""
    if isinstance(raw, dict) or (isinstance(raw, list) and form.BY_KEY[key]['type'] != 'multi'):
        return None, values.NOT_TEXT
    return values.clean_value(key, raw)
