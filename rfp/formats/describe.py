"""What fills each column of a carrier format, in the reader's words (plan.md §9.8; K87, K88, K109). Pure. The lens's
helpers from old Vantage 891f1b3 `benefits/reports/census_mapping.py` (`kind_of`, `DERIVE_INPUTS`, `_consumes`,
`_translation`, `_rules`, `_geometry`) and `market/census_lens._fills`; the developer report itself is not ported.
"""

from census import fields
from deals import lines

from . import bundled

# What each derivation reads. A derivation added to `rows` without an entry here fails a test.
DERIVE_INPUTS = {
    'age': [('dob', 'value')],
    'county': [('county', 'value'), ('zip', 'value')],
    'out_of_area': [('zip', 'value')],
}
TRANSFORM_WORDS = {
    'zip5': '5 digits, a dropped leading zero restored',
    'date': 'a real date cell',
    'initial': 'the first letter only',
}
STATUS_NOTE = (
    'We do not track COBRA or retiree status, so every employee exports as Active — '
    'correct any continuants in the file.'
)


def kind_of(column):
    """census · derived · gap: a column with a `source` is mapped, just not to a census cell."""
    if column.get('field'):
        return 'census'
    return 'derived' if column.get('source') else 'gap'


def consumes(column):
    """[(census key, 'value' | 'presence')] a column reads: `row:enroll:<key>` reads the key's presence, the member
    type reads the relationship, a derivation its inputs."""
    if column.get('field'):
        return [(column['field'], 'value')]
    source = column.get('source') or ''
    if source.startswith('row:enroll:'):
        return [(source.split(':', 2)[2], 'presence')]
    if source == 'row:member_type':
        return [('relationship', 'presence')]
    if source.startswith('derive:'):
        return list(DERIVE_INPUTS.get(source.removeprefix('derive:'), []))
    return []


def fills(column):
    """{kind, text, field}: what fills the column ("our First Name", "worked out from Date of Birth", "nothing")."""
    kind = kind_of(column)
    if kind == 'census':
        return {'kind': 'census', 'text': f'our {fields.label(column["field"])}', 'field': column['field']}
    if kind == 'derived':
        inputs = [fields.label(key) for key, _how in consumes(column) if key in fields.BY_KEY]
        text = f'worked out from {" / ".join(inputs)}' if inputs else 'worked out from the roster'
        return {'kind': 'derived', 'text': text, 'field': ''}
    return {'kind': 'gap', 'text': 'nothing — we do not store this', 'field': ''}


def translation(column):
    value_map = column.get('value_map') or {}
    if value_map:
        return ' · '.join(f'{token}→{word}' if word else f'{token}→(blank)' for token, word in value_map.items())
    return TRANSFORM_WORDS.get(column.get('transform') or '', '')


def rules_of(column):
    out = []
    if column.get('required'):
        out.append('required')
    if column.get('employee_only'):
        out.append('employee-only')
    if column.get('line'):
        out.append(f'only when quoting {lines.label(column["line"])}')
    if column.get('inherits'):
        out.append("a dependent inherits the employee's")
    return out


def geometry(fmt):
    """The rows and columns the format fills: "rows 7–506, columns B–X" (the cap is the template's own rows)."""
    found = bundled.letters(fmt)
    last = fmt['data_row'] + fmt['max_rows'] - 1 if fmt['max_rows'] else None
    rows = f'rows {fmt["data_row"]}–{last}' if last else f'rows {fmt["data_row"]} down'
    span = f'{found[0]}–{found[-1]}' if found else ''
    not_sent = (fmt.get('not_sent') or {}).get('columns') or []
    if span and not_sent:
        span = f'{span} of {found[0]}–{not_sent[-1]["letter"]} printed'
    return f'{rows}, columns {span}' if span else rows


def gap_notes(fmt):
    """Notes about what the format asks that we answer only partly (the old `template_gaps` notes)."""
    return [STATUS_NOTE] if any((column.get('transform') or '') == 'status' for column in fmt['columns']) else []
