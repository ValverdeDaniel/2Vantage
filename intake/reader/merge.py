"""Joining an intake read's answers (plan.md §10.4; B40, D112; slice 51). Pure.

Ported from old Vantage 891f1b3 `_merge_intake` (benefits/ai/claude_readers.py), in reading order (a file's pages in
order, files in upload order):
- an answer's first reading wins; a later reading that differs only flags it (`low`, saying both were printed). Intake
  is keep-first on purpose: the old app's reason, "an intake read covers one document", holds per question;
- coverage: one entry per line, the first carrier, funding and renewal date printed for it, blanks filled by later
  readings;
- contacts: one per person, by email, else by name; blanks filled by later readings.
Merged: {fields: {key: {value, doc, page, cell, low}}, coverage: [{line, carrier, funding, renewal_date, doc, page}],
contacts: [{name, title, email, phone, role, doc}]}.
"""

from .. import form

CONFLICT = 'The file prints two different values for this.'


def _order(part):
    file, piece, _data = part
    pages = getattr(piece, 'pages', None) or ()
    return (file.order, min(pages) if pages else 0)


def _text(value):
    return ' '.join(str(value or '').split())


def _fields(target, rows, file):
    for row in rows or []:
        key, value = row.get('key'), _text(row.get('value'))
        if key not in form.BY_KEY or not value:
            continue
        held = target.get(key)
        if held is None:
            page = row.get('page') if isinstance(row.get('page'), int) and row.get('page') > 0 else None
            target[key] = {
                'value': value,
                'doc': file.id,
                'page': page,
                'cell': _text(row.get('cell')) or None,
                'low': 'Claude was not sure of this value.' if row.get('unsure') else None,
            }
        elif held['value'].lower() != value.lower():
            held['low'] = CONFLICT


def _coverage(target, rows, file):
    for row in rows or []:
        line = row.get('line')
        if not line:
            continue
        held = next((entry for entry in target if entry['line'] == line), None)
        found = {key: _text(row.get(key)) for key in ('carrier', 'funding', 'renewal_date')}
        if held is None:
            page = row.get('page') if isinstance(row.get('page'), int) and row.get('page') > 0 else None
            target.append({'line': line, **found, 'doc': file.id, 'page': page})
            continue
        for key, value in found.items():
            if value and not held[key]:
                held[key] = value


def _person(row):
    email = _text(row.get('email')).lower()
    return f'E{email}' if email else f'N{_text(row.get("name")).lower()}'


def _contacts(target, rows, file):
    for row in rows or []:
        found = {key: _text(row.get(key)) for key in ('name', 'title', 'email', 'phone', 'role')}
        if not (found['name'] or found['email']):
            continue
        held = next((entry for entry in target if _person(entry) == _person(found)), None)
        if held is None:
            target.append({**found, 'doc': file.id})
            continue
        for key, value in found.items():
            if value and not held[key]:
                held[key] = value


def merge(parts, files):
    merged = {'fields': {}, 'coverage': [], 'contacts': []}
    for file, _piece, data in sorted(parts, key=_order):
        data = data or {}
        _fields(merged['fields'], data.get('fields'), file)
        _coverage(merged['coverage'], data.get('coverage'), file)
        _contacts(merged['contacts'], data.get('contacts'), file)
    return merged
