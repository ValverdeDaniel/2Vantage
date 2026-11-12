"""One carrier format's rows from the census (plan.md §9.8 "Rows" and "Cells"; K92, K97). Pure over the people
`census.facts.people` answers, so the lens, the download and the packet build from one function and the preview is
what the carrier receives. Ported from old Vantage 891f1b3 `plan_math.census_rows_for_template`.

- Rows: each employee followed by its dependents (family order: `census.selectors.page.family_groups`), dependents not
  linked to an employee last. One row per member (K38).
- Cells, in order: a `line` column is blank unless the deal quotes that line (a deal quoting nothing gets every
  column); an `employee_only` column is blank on a dependent; `row:member_type` is the relationship token,
  `row:enroll:<key>` is `ENROLL` when the key holds a value, `derive:age` the age at the effective date,
  `derive:county` the typed county else the ZIP crosswalk, `derive:out_of_area` `IN_AREA` for a lower-48 ZIP; a
  `field` is the member's value, or the employee's when blank and the column `inherits`; then the token is spelled
  through the `value_map`, or the value shaped by its transform.
- `missing`: required cells left blank (`translate.column_required`), never a dependent's medical tier.
- Notes and warnings are count-only (D-143): a token the format has no code for, a terminated employee going out as
  Active, a dependent going out as a child, a tier we cannot read; members outside the lower 48; employees with no tier
  on a quoted line, once per employee and column (K74, old bug 17); the cap, saying how many people did not fit (K97,
  OQ61). `notes[*].row_ids` are for our own screens, which name the people; files never do.
"""

from collections import namedtuple

from census import fields
from census.rollup import age_at
from census.selectors.page import family_groups
from deals import lines

from . import county, translate

Built = namedtuple('Built', 'headers rows people missing notes warnings')
NO_TIER_ON_DEPENDENTS = ('medical_tier', 'effective_date')


def family_order(people):
    """The people as the carrier files list them: each employee, then its dependents; unlinked dependents last."""
    return [person for family in family_groups(people) for person in family]


def applies(column, kind, quoted):
    """Does the format expect a value in this column on this person's row? (A blank the builder leaves on purpose —
    a line not quoted, an employee-only column on a dependent, a dependent's medical tier — is never a gap.)"""
    line = column.get('line') or ''
    if line and quoted and line not in quoted:
        return False
    if column.get('employee_only') and kind != fields.EMPLOYEE:
        return False
    return not (kind == fields.DEPENDENT and (column.get('field') or '') in NO_TIER_ON_DEPENDENTS)


class _Family:
    """A person's values, falling back to their employee's when their own is blank (the ONE inherit rule, so a
    derivation that reads the ZIP never disagrees with the ZIP column beside it)."""

    def __init__(self, people):
        self.by_id = {person['id']: person for person in people}

    def value(self, person, key):
        text = str(person['values'].get(key) or '').strip()
        if not text and person['kind'] == fields.DEPENDENT and person.get('employee_id'):
            employee = self.by_id.get(person['employee_id'])
            text = str(employee['values'].get(key) or '').strip() if employee else ''
        return text


class _Notes:
    def __init__(self):
        self.found = {}  # (code, header, token) -> [person id]
        self.territories = {}
        self.blank_tiers = {}  # column index -> employees

    def add(self, code, header, token, person):
        self.found.setdefault((code, header, token), []).append(person['id'])


def _source_value(column, person, family, as_of, notes):
    """(raw value or token, value_map applies) for a column with a `source`."""
    source = column['source']
    if source == 'row:member_type':
        text = person['values'].get('relationship') or ''
        if translate.relationship_is_default(person['kind'], text):
            notes.add('relationship_default', column.get('header') or '', '', person)
        return translate.relationship(person['kind'], text), True
    if source.startswith('row:enroll:'):
        return ('ENROLL' if str(person['values'].get(source.split(':', 2)[2]) or '').strip() else ''), True
    what = source.removeprefix('derive:')
    if what == 'age':
        years = age_at(family.value(person, 'dob'), as_of)
        return ('' if years is None else str(years)), True
    if what == 'county':
        return (family.value(person, 'county') or county.county_for(family.value(person, 'zip'))), True
    if what == 'out_of_area':
        zip_text = family.value(person, 'zip')
        token = county.in_area(zip_text)
        where = county.territory_of(zip_text)
        if not token and where:
            notes.territories[where] = notes.territories.get(where, 0) + 1
        return token, True
    return '', True


def _cell(column, index, person, family, quoted, as_of, notes):
    """(shown value, required and blank) for one cell."""
    header = column.get('header') or ''
    line = column.get('line') or ''
    line_active = not line or not quoted or line in quoted
    skip = not line_active or (column.get('employee_only') and person['kind'] != fields.EMPLOYEE)
    before = ''
    if skip or not (column.get('source') or column.get('field')):  # a column we do not store goes out blank
        raw, mapped = '', False
    elif column.get('source'):
        raw, mapped = _source_value(column, person, family, as_of, notes)
    else:
        key = column['field']
        raw = family.value(person, key) if column.get('inherits') else str(person['values'].get(key) or '').strip()
        before = raw
        raw, mapped = translate.canonical(column, raw)
        transform = column.get('transform') or ''
        if transform == 'status' and 'TERM' in before.upper():
            notes.add('terminated_active', header, '', person)
        if transform == 'tier' and before and not raw:
            notes.add('unparsed', header, '', person)
    value_map = column.get('value_map') or {}
    if mapped and value_map:
        value = value_map.get(raw, '') if raw else ''
        if raw and raw not in value_map and not skip:
            notes.add('no_carrier_code', header, str(raw), person)
    elif (column.get('transform') or '') in translate.TOKENS:
        value = str(raw or '')
    else:
        value = translate.shaped(raw, column.get('transform') or '')
    if (
        column.get('transform') == 'tier'
        and not skip
        and person['kind'] == fields.EMPLOYEE
        and not value
        and not before
    ):
        notes.blank_tiers[index] = notes.blank_tiers.get(index, 0) + 1
    blank = translate.column_required(column) and not value and not skip
    return value, blank and applies(column, person['kind'], quoted)


def _warnings(fmt, notes, total):
    columns = fmt['columns']
    out = []
    for where, count in sorted(notes.territories.items()):
        out.append(
            f'{count} member{"s are" if count != 1 else " is"} in {county.territory_name(where)} — we left "out of '
            'area" blank rather than answering it. Confirm with the carrier whether the plan covers them.'
        )
    for index, count in sorted(notes.blank_tiers.items()):
        column = columns[index]
        line = lines.label(column['line']) if column.get('line') else ''
        named = f'"{column.get("header")}"' + (f' ({line})' if line else '')
        out.append(
            f'{count} employee{"s have" if count != 1 else " has"} no {named} on a line you are quoting — the carrier '
            'will read that as unknown.'
        )
    found = []
    for (code, header, token), ids in sorted(notes.found.items()):
        people = list(dict.fromkeys(ids))
        text = translate.note_text(code, len(people), header, token)
        if text:
            out.append(text)
            found.append({'code': code, 'text': text, 'count': len(people), 'header': header, 'token': token,
                          'row_ids': people})  # fmt: skip
    limit = fmt.get('max_rows') or 0
    if limit and total > limit:
        out.append(overflow_text(fmt, total))
    return out, found


def overflow_text(fmt, total):
    """The truthful cap warning (K97, OQ61 default): the file stops at the template's rows and says who is left."""
    limit = fmt['max_rows']
    left = total - limit
    text = (
        f'This file has room for {limit} people; the last {left} on the census '
        f'{"does" if left == 1 else "do"} not fit and {"is" if left == 1 else "are"} not in it.'
    )
    return text + (' The CSV for their portal carries everyone.' if 'csv' in fmt['formats'] else '')


def build(fmt, people, quoted, as_of):
    """Built(headers, rows [[shown text]], people (in row order), missing [(row, col)], notes, warnings).
    `quoted`: the deal's requested lines; `as_of`: the date ages are measured at (the effective date)."""
    ordered = family_order(people)
    family = _Family(people)
    notes = _Notes()
    columns = fmt['columns']
    quoted = set(quoted or ())
    rows, missing = [], []
    for ri, person in enumerate(ordered):
        values = []
        for ci, column in enumerate(columns):
            value, blank = _cell(column, ci, person, family, quoted, as_of, notes)
            values.append(value)
            if blank:
                missing.append((ri, ci))
        rows.append(values)
    warnings, found = _warnings(fmt, notes, len(rows))
    if missing:
        warnings.append(f'{len(missing)} required cell{"s are" if len(missing) != 1 else " is"} empty.')
    return Built([column.get('header') or '' for column in columns], rows, ordered, missing, found, warnings)
