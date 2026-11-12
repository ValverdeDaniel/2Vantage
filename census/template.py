"""The census template and the census export (plan.md §9.1, §9.2; C38). Ported from old Vantage 891f1b3
`pipeline/workbooks.py` (`blank_census_columns`, `build_blank_census_workbook`).

- `template(deal)`: what the employer fills in. Sheet **Census**: row 1 holds the labels of the deal's census columns
  (every column, minus the groups of lines the deal is not quoting, plus every column the deal requires), styled bold
  white on navy, wrapped, 28 high, 12–28 wide by label, frozen at A2. When the deal already has people the rows are
  prefilled from the roster, each employee followed by their dependents ("validate, don't re-key"). Sheet **How to
  fill this in** second: the group's name, the old notes and the columns needed to quote. Every label is an exact
  header synonym (§4.8), so a filled template re-imports at full confidence (the old invariant). The client portal's
  copy is always blank (L.6).
- `export(deal)`: the staff workbook (§9.2): **Type**, then all 45 columns, then **Issues** (the person's validation
  messages, and the required cells left blank), unmasked.
Text goes through `documents.xlsx_safe.put` (openpyxl): a value that begins like a formula stays text. Dates print
`MM/DD/YYYY`, as the grid shows them. Building a file writes nothing; the view logs the download (§3.8).
"""

import io

from deals import clock

from . import facts, fields, validation
from .selectors.page import family_groups
from .values import shown

NAVY = '173A63'
SHEET = 'Census'
GUIDE = 'How to fill this in'
NOTES = [
    (
        'One row per person',
        'List each employee, then a row per dependent directly beneath them. Do not merge cells or add blank spacer '
        'rows.',
    ),
    (
        'Keep the header row',
        'Row 1 names each column. Leave it exactly as it is — it is how we read the file back in.',
    ),
    ('Leave what you do not have blank', 'A blank cell is fine. We will come back to you for anything we still need.'),
    ('Dates', 'Any common format works (MM/DD/YYYY, YYYY-MM-DD).'),
    (
        'Tier / coverage level',
        'EE, ES (employee + spouse), EC (employee + children) or FAM. Spelled-out versions are fine too.',
    ),
    (
        'Extra columns are fine',
        'If your system exports columns we did not ask for, leave them in — we will sort it out on our side.',
    ),
]
TYPE_WORDS = {fields.EMPLOYEE: 'Employee', fields.DEPENDENT: 'Dependent'}


def template_keys(deal, needed):
    """The template's columns (C38): every column but the groups of lines not quoted, plus every required one."""
    requested = set(deal.requested_lines or [])
    required = set(needed[fields.EMPLOYEE]) | set(needed[fields.DEPENDENT])
    keys = []
    for field in fields.FIELDS:
        group_lines = fields.GROUP_LINES.get(field['group'])
        if group_lines and not requested & set(group_lines) and field['key'] not in required:
            continue
        keys.append(field['key'])
    return keys


def _ordered(deal_id):
    found = sorted(facts.people(deal_id), key=lambda person: (person['position'], person['id']))
    return [person for family in family_groups(found) for person in family]


def _header(ws, labels):
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    thin = Side(style='thin', color='D9DEE7')
    for index, label in enumerate(labels, start=1):
        cell = ws.cell(row=1, column=index, value=label)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor=NAVY)
        cell.alignment = Alignment(vertical='center', wrap_text=True)
        cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        ws.column_dimensions[get_column_letter(index)].width = max(12, min(28, len(label) + 4))
    ws.row_dimensions[1].height = 28
    ws.freeze_panes = 'A2'


def _rows(ws, people, keys, first=1):
    from documents.xlsx_safe import put

    for row, person in enumerate(people, start=2):
        for column, key in enumerate(keys, start=first):
            text = shown(key, person['values'].get(key))
            put(ws, row, column, text or None)


def _guide(book, deal, labels_needed):
    from openpyxl.styles import Alignment, Font

    guide = book.create_sheet(GUIDE)
    guide.column_dimensions['A'].width = 30
    guide.column_dimensions['B'].width = 84
    guide.cell(row=1, column=1, value=f'Employee census — {deal.client.name}').font = Font(bold=True, size=13)
    placed = [(row, heading, note) for row, (heading, note) in enumerate(NOTES, start=3)]
    if labels_needed:  # one blank row, then what carriers cannot do without
        needed = f'We cannot go to carriers without these columns: {", ".join(labels_needed)}.'
        placed.append((len(NOTES) + 4, 'Needed to quote', needed))
    for row, heading, note in placed:
        head = guide.cell(row=row, column=1, value=heading)
        head.font = Font(bold=True)
        head.alignment = Alignment(vertical='top')
        body = guide.cell(row=row, column=2, value=note)
        body.alignment = Alignment(vertical='top', wrap_text=True)


def _saved(book):
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def template(deal):
    """(bytes, people prefilled) — the census template to hand the employer (§9.1)."""
    import openpyxl

    needed = facts.needed(deal)
    keys = template_keys(deal, needed)
    required = set(needed[fields.EMPLOYEE]) | set(needed[fields.DEPENDENT])
    people = _ordered(deal.id)
    book = openpyxl.Workbook()
    ws = book.active
    ws.title = SHEET
    _header(ws, [fields.label(key) for key in keys])
    _rows(ws, people, keys)
    _guide(book, deal, [fields.label(key) for key in keys if key in required])
    return _saved(book), len(people)


def _issues(person, issues, missing):
    messages = [found['message'] for key in fields.KEYS for found in issues.get((person['id'], key), [])]
    if missing:
        messages.append('Required: ' + ', '.join(fields.label(key) for key in missing))
    return '; '.join(messages)


def export(deal):
    """The census workbook (§9.2): Type, the 45 columns, Issues. Unmasked: staff only, every download logged."""
    import openpyxl

    from documents.xlsx_safe import put

    found = facts.people(deal.id)
    issues = validation.validate(found, clock.today())
    needed = facts.needed(deal)
    people = _ordered(deal.id)
    book = openpyxl.Workbook()
    ws = book.active
    ws.title = SHEET
    _header(ws, ['Type', *[fields.label(key) for key in fields.KEYS], 'Issues'])
    _rows(ws, people, fields.KEYS, first=2)
    last = len(fields.KEYS) + 2
    for row, person in enumerate(people, start=2):
        put(ws, row, 1, TYPE_WORDS.get(person['kind'], person['kind']))
        text = _issues(person, issues, facts.missing_keys(person, needed[person['kind']]))
        put(ws, row, last, text or None)
    return _saved(book)
