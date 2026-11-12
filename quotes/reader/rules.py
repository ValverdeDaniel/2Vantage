"""What a read may do with each value it found (plan.md §10.5, §5.4; D58, D60, D61, D118, E93). Pure.

- **House formats** (D58): every value goes through the Advisor's own cleaning (`quotes.values.clean`), as if typed. A
  value the field cannot take ("$512.34*" as a rate) is a finding, never a failed landing, and is left out.
- **The line's fields only**: a value for a field the plan's line does not have is left out (counted).
- **Who wins** (D61): a read fills a blank and replaces a value Claude read before that no person approved. A value a
  person typed, imported, a client gave or someone approved is "Left alone": shown, unticked. An equal value writes
  nothing and is not shown (D60). A sold plan is frozen: none of its values is touched (D59).
- **Doubt**: a value Claude was unsure of arrives unticked (D31); `low` says why, as a reason (O.3.1).
- **Member data** (E93): a printed label that looks like a person's details is never kept as the value's `line`.
"""

from documents import screening
from documents.review_rules import is_approved

from .. import fields, values

UNSURE = 'Claude was unsure of this value.'
LEFT_ALONE = {
    'typed': 'Typed by a person',
    'relay': 'Typed by a person',
    'import': 'Imported from a template',
    'client': 'Given by the client',
    'prefill': 'Prefilled',
    'sale': 'Set by the sale',
    'in_force': 'In force',
    'agency': "The agency's",
    'approved': 'Approved by a person',
}


def keys_of(line):
    return set(fields.keys_for(line))


def clean(key, raw):
    """(value, None) or (None, why) for one printed value, through the field's own cleaning."""
    field = fields.BY_KEY.get(key)
    if field is None:
        return None, 'unknown'
    value, error = values.clean(field, raw)
    if error or value in (None, ''):
        return None, error or 'blank'
    return value, None


def printed_line(label):
    """The printed label kept with a value (its `line`), unless it looks like a person's details (E93)."""
    text = str(label or '').strip()
    return '' if not text or screening.phi_flags(text) else text


def decide(old_value, old_source, new_value, *, frozen=False):
    """How a read treats one value against what the plan holds: 'same' (nothing), 'fill', 'replace', or
    ('left', why) — shown, unticked."""
    if frozen:
        return ('left', 'Sold: left as sold')
    if old_value in (None, ''):
        return 'fill'
    if str(old_value) == str(new_value):
        return 'same'
    source = old_source if isinstance(old_source, dict) else {}
    origin = source.get('origin') or 'typed'
    if is_approved(source):
        return ('left', LEFT_ALONE['approved'])
    if origin == 'ai':
        return 'replace'
    return ('left', LEFT_ALONE.get(origin, 'Typed by a person'))


def staged_value(key, entry, *, old_value=None, old_source=None, frozen=False):
    """The change set's entry for one merged value against the plan's (or None when it writes nothing), plus a
    finding text when the printed value cannot be taken."""
    value, why = clean(key, entry['value'])
    if value is None:
        label = fields.BY_KEY.get(key, {}).get('label', key)
        if why in ('blank', 'unknown'):
            return None, None
        page = f', page {entry["page"]}' if entry.get('page') else ''
        return None, f'"{entry["value"]}" is not a value for {label}{page}, so it was left out.'
    verdict = decide(old_value, old_source, value, frozen=frozen)
    if verdict == 'same':
        return None, None
    left = verdict if isinstance(verdict, tuple) else None
    unsure = bool(entry.get('unsure'))
    return {
        'key': key,
        'new': value,
        'old': old_value if old_value not in (None, '') else '',
        'doc': entry.get('doc'),
        'page': entry.get('page'),
        'cell': entry.get('cell') or '',
        'line': printed_line(entry.get('label')),
        'low': UNSURE if unsure else None,
        'why': left[1] if left else '',
        'tick': not left and not unsure,
    }, None
