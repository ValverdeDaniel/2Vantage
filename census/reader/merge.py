"""Joining a census read's answers into one roster (plan.md §10.4; C19, D110; slice 51). Pure.

Ported from old Vantage 891f1b3 `census_people` (benefits/ai/claude_readers.py, D-152):
- ranges go in reading order (a file's pages in order, files in upload order), whatever order their calls ended in;
- a person read twice is recorded once: the same SSN, else the same last name, first name and birth date, in the same
  role (an employee or a dependent), within one file;
- a dependent goes under the employee the page prints it under (`employee`), else under the last employee read before
  it in its file; with none before it, it stays a dependent with no employee, and validation says so (`dep_orphan`).
  The old app made such a person an employee; 2V keeps what the page says.
Values stay as printed here (the staged import shows them so); they are cleaned when the people are built (§5.3.1).
A merged person: {kind, parent (its employee's index, or None), doc, values {key: text}, pages {key: page},
low [keys Claude was unsure of]}.
"""

from .. import fields
from ..values import clean, digits


def _order(part):
    file, piece, _data = part
    pages = getattr(piece, 'pages', None) or ()
    return (file.order, min(pages) if pages else 0)


def _values(person):
    """({key: text as printed}, {key: page}, {keys unsure}): the first printing of a key wins."""
    values, pages, low = {}, {}, set()
    for entry in person.get('values') or []:
        key = entry.get('key')
        text = ' '.join(str(entry.get('value') or '').split())
        if key not in fields.BY_KEY or not text or key in values:
            continue
        values[key] = text
        if isinstance(entry.get('page'), int) and entry['page'] > 0:
            pages[key] = entry['page']
        if entry.get('unsure'):
            low.add(key)
    return values, pages, low


def identity(values):
    """Who a read person is, for the duplicate check: their SSN, else name and birth date; '' when neither."""
    ssn = digits(values.get('ssn'))
    if len(ssn) >= 4:
        return f'S{ssn}'
    parts = [' '.join(str(values.get(key) or '').lower().split()) for key in ('last_name', 'first_name')]
    parts.append(clean('dob', values.get('dob')))
    return f'N{"|".join(parts)}' if any(parts) else ''


def _name(text):
    return ' '.join(str(text or '').lower().split())


def merge(parts, files):
    """{'people': [...], 'duplicates': n, 'guessed': n}: every person of every range, in reading order."""
    people, duplicates, guessed = [], 0, 0
    seen, by_name, last_employee, file_of = {}, {}, None, None
    for file, _piece, data in sorted(parts, key=_order):
        if file.id != file_of:  # a dependent never goes under an employee of another file
            file_of, last_employee, by_name, seen = file.id, None, {}, {}
        for person in (data or {}).get('people') or []:
            values, pages, low = _values(person)
            if not values:
                continue
            dependent = bool(person.get('dependent'))
            key = identity(values)
            if key and (dependent, key) in seen:
                duplicates += 1
                continue
            parent = None
            if dependent:
                parent = by_name.get(_name(person.get('employee')))
                if parent is None:
                    parent = last_employee
                    guessed += 1
            position = len(people)
            if key:
                seen[(dependent, key)] = position
            if not dependent:
                last_employee = position
                name = _name(f'{values.get("first_name", "")} {values.get("last_name", "")}')
                if name:
                    by_name.setdefault(name, position)
            people.append(
                {
                    'kind': fields.DEPENDENT if dependent else fields.EMPLOYEE,
                    'parent': parent,
                    'doc': file.id,
                    'values': values,
                    'pages': pages,
                    'low': sorted(low & set(values)),
                }
            )
    return {'people': people, 'duplicates': duplicates, 'guessed': guessed}
