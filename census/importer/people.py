"""Building people from a mapped table (plan.md §5.3.2 step 6; C16). Pure.

Ported from old Vantage 891f1b3 `market/census_reader.py` (`import_people`) and `market/census_request.py`
(`SsnOnFile`):
- a row with nothing in any mapped column is no one (Warner's template numbers its empty rows);
- a masked SSN ('***-**-1234') stands for the SSN on file for that person when the last four agree, else it is blank;
  it never matches a person or links a dependent;
- a row is an employee when its relationship is blank or an employee word, else a dependent;
- an employee with no SSN but an employee SSN gets the SSN copied from it;
- a dependent belongs to the employee above it whose SSN (or employee SSN) is its employee SSN, else whose Emp ID is
  its Emp ID, else to the last employee above it; with none above, it stays unlinked;
- values are cleaned (§5.3.1); each remembers its sheet cell, unless the file was reformatted (no one cell holds it).
A person: {kind, parent (index of its employee, or None), values {key: text}, cells {key: 'Sheet!D12'}, low [keys]}.
"""

from .. import fields
from ..values import clean, digits, masked_last4
from . import read
from .words import is_employee_relationship


def identities(values, with_ssn=True):
    """Every identity a person carries, strongest first: the employer's id, the SSN, last name + first name + birth
    date (§5.3.2 step 7). Only the row's own SSN counts; a dependent's employee SSN is its employee's."""
    out = []
    ext = ' '.join(str(values.get('ext_emp_id') or '').lower().split())
    if ext:
        out.append(f'E{ext}')
    ssn = digits(values.get('ssn'))
    if with_ssn and len(ssn) >= 4:
        out.append(f'S{ssn}')
    name = '|'.join(' '.join(str(values.get(key) or '').lower().split()) for key in ('last_name', 'first_name', 'dob'))
    if name.strip('|'):
        out.append(f'N{name}')
    return out


class SsnOnFile:
    """The roster's SSNs, found by everything except the SSN. `restore(values)` swaps a masked SSN for the number on
    file when its last four agree, and blanks it otherwise; an identity two stored people share identifies nobody."""

    def __init__(self, roster):
        stored = {person['id']: person for person in roster}
        self.index = {}
        for person in roster:
            values = person['values']
            entry = {'ssn': values.get('ssn', ''), 'subscriber_ssn': values.get('subscriber_ssn', '')}
            parent = stored.get(person.get('employee_id'))
            if not entry['subscriber_ssn'] and parent:
                entry['subscriber_ssn'] = parent['values'].get('ssn', '')  # a dependent's employee SSN is theirs
            for identity in identities(values, with_ssn=False):
                if identity in self.index and self.index[identity] is not entry:
                    self.index[identity] = None
                else:
                    self.index.setdefault(identity, entry)
        self.restored = self.unmatched = 0

    def restore(self, values):
        masks = {key: masked_last4(values.get(key)) for key in fields.SSN_KEYS}
        if not any(masks.values()):
            return values
        found = next(
            (self.index[i] for i in identities(values, with_ssn=False) if self.index.get(i) is not None),
            None,
        )
        for key, last4 in masks.items():
            if not last4:
                continue
            on_file = (found or {}).get(key, '')
            if on_file and digits(on_file)[-4:] == last4:
                values[key] = on_file
                self.restored += 1
            else:
                values[key] = ''
                self.unmatched += 1
        return values

    def summary(self):
        return {'restored': self.restored, 'unmatched': self.unmatched}


def _mapped(table, mapping):
    return {item['column']: (item['field'], item['low']) for item in mapping if item['field']}


def build(table, mapping, on_file=None, cells=True):
    """The people of `table` under the confirmed `mapping`. `on_file` (SsnOnFile) restores masked SSNs; `cells` False
    for a reformatted file."""
    columns = _mapped(table, mapping)
    column_of = {field: column for column, (field, _low) in sorted(columns.items())}
    people, last_employee, by_ext, by_ssn = [], None, {}, {}
    for index, row in enumerate(table.rows):
        values = {field: clean(field, row[column]) for column, (field, _low) in columns.items() if row[column]}
        if not any(values.values()):
            continue
        if on_file is not None:
            on_file.restore(values)
        values = {key: text for key, text in values.items() if text}
        if not values:
            continue
        low = {field for column, (field, flag) in columns.items() if flag and field in values}
        source = dict(column_of)
        employee = is_employee_relationship(values.get('relationship'))
        if employee and not values.get('ssn') and values.get('subscriber_ssn'):
            values['ssn'] = values['subscriber_ssn']
            source['ssn'] = column_of['subscriber_ssn']
            if 'subscriber_ssn' in low:
                low.add('ssn')
        position = len(people)
        subscriber = digits(values.get('subscriber_ssn'))
        ext = values.get('ext_emp_id', '')
        parent = None
        if employee:
            last_employee = position
            if ext:
                by_ext[ext] = position
            own = digits(values.get('ssn'))
            if own:
                by_ssn[own] = position
            if subscriber:
                by_ssn.setdefault(subscriber, position)
        else:
            parent = by_ssn.get(subscriber) if subscriber else None
            if parent is None and ext:
                parent = by_ext.get(ext)
            if parent is None:
                parent = last_employee
        people.append(
            {
                'kind': fields.EMPLOYEE if employee else fields.DEPENDENT,
                'parent': parent,
                'values': values,
                'cells': {key: read.cell(table, source[key], index) for key in values} if cells else {},
                'low': sorted(key for key in low if key in values),
            }
        )
    return people


def label(values):
    """A person's name for the dry run and the kept list (a screen, never Activity or a log)."""
    name = ' '.join(part for part in (values.get('first_name'), values.get('last_name')) if part)
    return name or values.get('ext_emp_id') or 'A person with no name'
