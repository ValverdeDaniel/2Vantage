"""Reshaping one row per benefit into one row per person (plan.md §5.3.2 step 3; C13). Pure.

Ported from old Vantage 891f1b3 `market/census_pivot.py` (`pivot_rows`). Deterministic, so it can promise that nobody
goes missing between the client's file and the carrier: every row is consumed, a duplicate, or unknown. It refuses
rather than guesses: more than 40% of rows with no person key, more than 20% naming an unknown benefit, identity
conflicts for more than 10% of people, or no employee. Of two rows for one person and benefit, the first is kept.
Each family keeps its order: the employee, then its dependents.
"""

from ..importer.words import EMPLOYEE_RELATIONSHIPS
from .shape import (
    IDENTITY_HINTS,
    LINE_OUTPUT_COLUMNS,
    cell,
    column_role,
    digits,
    label_to_line,
    person_columns,
    person_key,
    squash,
)

MAX_EMPTY_KEY_RATIO = 0.40
MAX_UNKNOWN_LINE_RATIO = 0.20
MAX_CONFLICT_RATIO = 0.10


def refused(reason):
    return {'applied': False, 'reason': reason}


def _person(row, cols, key):
    family = cell(row, cols['emp_id']) or digits(cell(row, cols['ssn'])) or key
    relationship = squash(cell(row, cols['relationship']))
    return {
        'family': family,
        'dependent': bool(relationship) and relationship not in EMPLOYEE_RELATIONSHIPS,
        'person': {},
        'lines': {},
    }


def _read(headers, rows, line_col, label_map):
    """People by key in first-seen order, plus the counts and notes the checks below need."""
    words = [squash(header) for header in headers]
    cols = person_columns(headers)
    roles = {i: column_role(header) for i, header in enumerate(words)}
    person_cols = [i for i in range(len(headers)) if i != line_col and not roles[i]]
    identity_cols = {i for i in person_cols if any(hint in words[i] for hint in IDENTITY_HINTS)}
    out = {'people': {}, 'order': [], 'families': [], 'lines': [], 'consumed': 0, 'duplicates': 0, 'unknown': 0}
    out.update(person_cols=person_cols, roles=roles, conflicts=[], notes=[], empty_keys=0)
    for row in rows:
        key = person_key(row, cols)
        out['empty_keys'] += not key
        line = label_map.get(cell(row, line_col)) or label_to_line(cell(row, line_col))
        if not key or not line:
            out['unknown'] += 1
            continue
        person = out['people'].get(key)
        if person is None:
            person = out['people'][key] = _person(row, cols, key)
            out['order'].append(key)
            if person['family'] not in out['families']:
                out['families'].append(person['family'])
        for col in person_cols:
            value = cell(row, col)
            existing = person['person'].get(col)
            if value and existing is None:
                person['person'][col] = value
            elif value and existing != value and col in identity_cols:
                who = cell(row, cols['last']) or key
                out['conflicts'].append(f"{headers[col]}: '{existing}' and '{value}' both appear for {who}")
        blocks = {role: cell(row, i) for i, role in roles.items() if role}
        if line in person['lines']:
            out['duplicates'] += 1
            kept = person['lines'][line]
            if kept.get('plan') and blocks.get('plan') and kept['plan'] != blocks['plan']:
                name = f'{cell(row, cols["first"])} {cell(row, cols["last"])}'.strip()
                out['notes'].append(
                    f'{name} has two {line} rows ({kept["plan"]} / {blocks["plan"]}) — kept {kept["plan"]}'
                )
            continue
        person['lines'][line] = blocks
        if line not in out['lines']:
            out['lines'].append(line)
        out['consumed'] += 1
    return out


def _refusal(read, total, labels):
    people = read['people']
    if total and read['empty_keys'] / total > MAX_EMPTY_KEY_RATIO:
        return (
            f'Could not tell who {read["empty_keys"]} of {total} rows belong to — the file needs a name or SSN on '
            'every row.'
        )
    if read['consumed'] + read['duplicates'] + read['unknown'] != total:
        return 'Reformat did not account for every row — leaving the census as uploaded.'
    if total and read['unknown'] / total > MAX_UNKNOWN_LINE_RATIO:
        named = f' ({", ".join(labels[:4])})' if labels else ''
        return f"{read['unknown']} of {total} rows name a benefit we don't recognize{named}."
    if not people:
        return 'No people could be read out of the file.'
    if len(read['conflicts']) / max(1, len(people)) > MAX_CONFLICT_RATIO:
        found = len(read['conflicts'])
        return f'Conflicting details for {found} of {len(people)} people — the rows may not be the same person.'
    if not any(not person['dependent'] for person in people.values()):
        return 'Every row looks like a dependent — no employees found.'
    return ''


def reshape(headers, rows, detection):
    """{applied, reason, headers, rows, source_rows, employee_rows, dependent_rows, lines, conflicts} for the grid
    under `detection` (shape.detect's line column and labels)."""
    line_col = detection.get('line_column')
    if line_col is None:
        return refused('No column identifies which benefit each row is for.')
    read = _read(headers, rows, line_col, detection.get('label_map') or {})
    reason = _refusal(read, len(rows), detection.get('unknown_labels') or [])
    if reason:
        return {**refused(reason), 'conflicts': read['conflicts']}
    people, order = read['people'], read['order']
    out_headers = [headers[i] for i in read['person_cols']]
    slots = []
    for line in read['lines']:
        for role, label in LINE_OUTPUT_COLUMNS.get(line, []):
            slots.append((line, role, len(out_headers)))
            out_headers.append(label)
    ordered = []
    for family in read['families']:
        members = [key for key in order if people[key]['family'] == family]
        ordered += [key for key in members if not people[key]['dependent']]
        ordered += [key for key in members if people[key]['dependent']]
    ordered += [key for key in order if key not in ordered]
    out_rows = []
    for key in ordered:
        person = people[key]
        row = [person['person'].get(col, '') for col in read['person_cols']] + [''] * len(slots)
        for line, role, index in slots:
            row[index] = person['lines'].get(line, {}).get(role, '')
        out_rows.append(row)
    dependents = sum(1 for key in ordered if people[key]['dependent'])
    return {
        'applied': True,
        'reason': '',
        'headers': out_headers,
        'rows': out_rows,
        'source_rows': len(rows),
        'employee_rows': len(ordered) - dependents,
        'dependent_rows': dependents,
        'lines': read['lines'],
        'conflicts': read['conflicts'] + read['notes'],
    }
