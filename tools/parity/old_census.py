"""A golden deal's census roster into old Vantage (891f1b3), for old_loader.py (slice 41; plan.md §12.7, Q.5).

The people are made by the same code 2Vantage's seed uses, `golden/census_roster.py` (mounted read-only beside this
file), from the spec's census groups, so both apps hold the same roster. They are written as the old import writes a
spreadsheet's rows (`census_reader.import_people`, then `census_upsert.upsert_roster` with origin `import`): each
value as the old reader turns a cell into text (`_cell_text`: a date MM/DD/YYYY, a whole number without its .0), a
tier through the old `normalize_tier`, each dependent under the employee before it. No file and no version is made,
as the old seeders write a roster. `check` reads every person back. Synthetic people only.
"""

import datetime
import os
import runpy
from pathlib import Path

from benefits.market.census_reader import _cell_text
from benefits.market.census_upsert import upsert_roster
from benefits.market.validation import normalize_tier
from benefits.models import BenefitFieldDef

ROSTER = Path(os.environ.get('PARITY_CENSUS_ROSTER', Path(__file__).with_name('census_roster.py')))
DATES = ('dob', 'hire_date', 'effective_date')


def _text(key, value, tiers):
    """One value as the old reader stores the spreadsheet cell 2Vantage's seed writes for it."""
    if key in DATES and value:
        value = datetime.date.fromisoformat(value)
    text = _cell_text(value)
    return (normalize_tier(text) or text) if key in tiers and text else text


def people(spec):
    """The spec's people as the old import's rows: [{dependent, parent, values}], in the file's order."""
    defs = {field.key: field for field in BenefitFieldDef.objects.filter(domain='census')}
    tiers = {key for key, field in defs.items() if field.data_type == 'tier'}
    made = runpy.run_path(str(ROSTER))['people'](spec)
    unknown = sorted({key for person in made for key in person} - set(defs) - {'kind'})
    if unknown:
        raise ValueError(f'{spec["key"]}: the old app has no census column {", ".join(unknown)}')
    rows, employee = [], None
    for person in made:
        dependent = person['kind'] == 'dependent'
        if not dependent:
            employee = len(rows)
        values = {key: text for key, raw in person.items() if key != 'kind' and (text := _text(key, raw, tiers))}
        rows.append({'dependent': dependent, 'parent': employee if dependent else None, 'values': values})
    return rows


def load(spec, case):
    """Write the spec's roster onto the old case; returns what was written, for `check`."""
    rows = people(spec)
    upsert_roster(case, rows, origin='import')
    return rows


def check(case, rows):
    """The differences between the old roster and `rows`, in words (row numbers and keys, never values)."""
    found = list(case.census_rows.prefetch_related('cells__field_def').order_by('sort_order', 'id'))
    if len(found) != len(rows):
        return [f'census: {len(found)} people on the old roster, {len(rows)} in the spec']
    wrong = []
    for number, (row, person) in enumerate(zip(found, rows, strict=True), start=1):
        kind = 'dependent' if person['dependent'] else 'employee'
        stored = {cell.field_def.key: cell.effective_value for cell in row.cells.all() if cell.effective_value}
        if row.row_type != kind:
            wrong.append(f'census person {number}: a {row.row_type}, not a {kind}')
        if kind == 'dependent' and found.index(row.parent) != person['parent']:
            wrong.append(f'census person {number}: under the wrong employee')
        if stored != person['values']:
            keys = set(stored) | set(person['values'])
            differ = sorted(key for key in keys if stored.get(key) != person['values'].get(key))
            wrong.append(f'census person {number}: {", ".join(differ)} differ')
    return wrong
