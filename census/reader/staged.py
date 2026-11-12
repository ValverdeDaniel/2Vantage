"""A census read waiting on its import (plan.md §5.3.2, §10.4; C19, D29, D110; slice 51). Pure.

A PDF roster Claude read waits as a `CensusImport`, like a spreadsheet's (D29: "census → CensusImport on Census"), so
the Census tab shows it in the same dialog, with the same dry run and apply. Its people stay on the import (`read`)
until it is applied or discarded, never on the job (D74, B13):
- `stored(merged)`: the import's `read`: the census columns read, in §4.4's order, are its columns;
- `mapping(keys)`: each read column mapped to its own census column (the dialog lets a person move or drop one);
- `table(read)`: the read as the dialog's table: headers are the columns' labels, and its samples come from it;
- `people(read, mapping, on_file)`: the people under the mapping, as `importer.people.build` gives a file's: values
  cleaned (§5.3.1), masked SSNs restored or blanked, an employee's SSN from the employee SSN when only that is printed;
  each value keeps its file and page, and the values Claude was unsure of are `low`. A dependent keeps the employee
  the read placed it under.
"""

from .. import fields
from ..importer.mapping import entry
from ..importer.read import Table
from ..importer.words import EXACT
from ..values import clean


def stored(merged):
    """The import's `read` for a merged census read (merge.merge)."""
    people = merged.get('people') or []
    keys = [key for key in fields.KEYS if any(key in person['values'] for person in people)]
    return {
        'keys': keys,
        'people': people,
        'duplicates': merged.get('duplicates', 0),
        'guessed': merged.get('guessed', 0),
    }


def mapping(keys):
    return [entry(column, fields.label(key), key, EXACT) for column, key in enumerate(keys)]


def table(read):
    keys = read.get('keys') or []
    rows = [[person['values'].get(key, '') for key in keys] for person in read.get('people') or []]
    return Table('', [fields.label(key) for key in keys], rows, list(range(1, len(rows) + 1)))


def counts(read):
    people = read.get('people') or []
    dependents = sum(1 for person in people if person['kind'] == fields.DEPENDENT)
    return {'people': len(people), 'employees': len(people) - dependents, 'dependents': dependents}


def _person(person, columns, keys, on_file):
    values, pages, low = {}, {}, set()
    for column, (field, column_low) in columns.items():
        key = keys[column] if column < len(keys) else None
        text = clean(field, person['values'].get(key)) if key else ''
        if not text:
            continue
        values[field] = text
        if key in person['pages']:
            pages[field] = person['pages'][key]
        if key in person['low'] or column_low:
            low.add(field)
    if on_file is not None:
        on_file.restore(values)
    values = {key: text for key, text in values.items() if text}
    if person['kind'] == fields.EMPLOYEE and not values.get('ssn') and values.get('subscriber_ssn'):
        values['ssn'] = values['subscriber_ssn']
        if 'subscriber_ssn' in pages:
            pages['ssn'] = pages['subscriber_ssn']
    return values, pages, low


def people(read, mapping_, on_file=None):
    """[{kind, parent, values, cells, low, pages, doc}] for `read` under the confirmed `mapping_`."""
    columns = {item['column']: (item['field'], item['low']) for item in mapping_ if item['field']}
    keys = read.get('keys') or []
    out, placed = [], {}
    for index, person in enumerate(read.get('people') or []):
        values, pages, low = _person(person, columns, keys, on_file)
        if not values:
            continue
        parent = placed.get(person['parent']) if person['kind'] == fields.DEPENDENT else None
        placed[index] = len(out)
        out.append(
            {
                'kind': person['kind'],
                'parent': parent,
                'values': values,
                'cells': {},
                'low': sorted(key for key in low if key in values),
                'pages': {key: page for key, page in pages.items() if key in values},
                'doc': person.get('doc'),
            }
        )
    return out
