"""GD4's two census files, made by code from its people (plan.md §13.4, §9.8; slice 12), and the seed's import.

- The client's own export: one sheet "Census", one row per person (employee, then dependents), with column names a
  payroll system uses — most map exactly; "Home Street" maps by guess and a bare "Effective Date" takes medical from
  the column before it, both checked in the dialog; "Notes" maps to nothing.
- The same people on Warner Pacific's census template, laid out from the old app's format definition
  (891f1b3 `benefits/migrations/0054_real_carrier_templates.py`, `warner_census`): sheet "Census Template", the header
  on row 3 (B–X, MEMBER NAME over First and Last), hints on row 4, two "Ex:" rows, people from row 7, and Warner's row
  counter 1–500 down column A. No Warner file is opened: no Warner census template is tracked in the old repo's
  assets/, so the layout is rebuilt from the definition and every value is synthetic.
`attach` uploads both through documents' one door (kind census) and imports the client's file through the census
services with the proposed mapping, as a member who clicks Apply would. A census that arrives later (GD3's, at its
checkpoint B; slice 13) is left out of the seed and brought in by `arrive`, the same way.
"""

import datetime
import io
import json

from django.core.files.uploadedfile import SimpleUploadedFile

from census import services as census
from documents import services as documents
from documents import xlsx_safe

from . import census_roster

CLIENT_COLUMNS = [
    ('Employee ID', 'ext_emp_id'),
    ('Relationship', 'relationship'),
    ('First Name', 'first_name'),
    ('Last Name', 'last_name'),
    ('Date of Birth', 'dob'),
    ('Gender', 'gender'),
    ('Home Street', 'address1'),
    ('City', 'city'),
    ('State', 'state'),
    ('Zip Code', 'zip'),
    ('Phone', 'phone'),
    ('Email', 'email'),
    ('Hire Date', 'hire_date'),
    ('Hours Per Week', 'hours_per_week'),
    ('Annual Salary', 'annual_salary'),
    ('Job Title', 'job_title'),
    ('Medical Plan', 'medical_plan'),
    ('Medical Tier', 'medical_tier'),
    ('Effective Date', 'effective_date'),
    ('Dental Plan', 'dental_plan'),
    ('Dental Tier', 'dental_tier'),
    ('Vision Plan', 'vision_plan'),
    ('Vision Tier', 'vision_tier'),
    ('Waiver Reason', 'waiver_reason'),
    ('Notes', None),
]
DATES = ('dob', 'hire_date', 'effective_date')

# Warner's census, columns B–X (the definition's order); None = a column we do not fill.
WARNER_COLUMNS = [
    ('RELATIONSHIP', 'warner:relationship'),
    ('MEMBER NAME', 'first_name'),
    ('', 'last_name'),
    ('DATE OF BIRTH', 'dob'),
    ('GENDER', 'gender'),
    ('ZIP CODE', 'zip'),
    ('COUNTY', None),
    ('HOURS', 'hours_per_week'),
    ('EE STATUS', 'warner:status'),
    ('COVERAGE TYPE', 'warner:medical_tier'),
    ('WAIVE REASON', 'waiver_reason'),
    ('CURRENT PLAN ELECTION', 'medical_plan'),
    ('COVERAGE TYPE', 'warner:dental_tier'),
    ('CURRENT PLAN ELECTION', 'dental_plan'),
    ('COVERAGE TYPE', 'warner:vision_tier'),
    ('CURRENT PLAN ELECTION', 'vision_plan'),
    ('COVERAGE TYPE', None),
    ('CLASSES', 'warner:class'),
    ('ELECTIONS', None),
    ('SALARY', 'annual_salary'),
    ('PAY MODE', 'warner:pay_mode'),
    ('JOB TITLE', 'job_title'),
    ('CLASSES', 'warner:class'),
]
WARNER_HINTS = {'first_name': 'First', 'last_name': 'Last', 'hours_per_week': 'Per week'}
WARNER_TIERS = {'EE': 'EE', 'ES': 'ES', 'EC': 'EC', 'FAM': 'EF', 'Waived': 'Waive'}
WARNER_RELATIONSHIPS = {'Employee': 'Employee', 'Spouse': 'Spouse/Partner', 'Child': 'Child/Dependent'}
WARNER_ROWS = 500  # Warner's own row counter
_made = {}


def _value(person, key):
    value = person.get(key, '')
    if key in DATES and value:
        return datetime.date.fromisoformat(value)
    return value if value != '' else None


def client_xlsx(people):
    out = io.BytesIO()
    book = xlsx_safe.workbook(out)
    head = book.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
    date = book.add_format({'num_format': 'mm/dd/yyyy'})
    sheet = book.add_worksheet('Census')
    for col, (label, _key) in enumerate(CLIENT_COLUMNS):
        xlsx_safe.write_text(sheet, 0, col, label, head)
    for row, person in enumerate(people, start=1):
        for col, (_label, key) in enumerate(CLIENT_COLUMNS):
            value = _value(person, key) if key else ('Synthetic test row' if row == 1 else None)
            xlsx_safe.write(sheet, row, col, value, date if key in DATES else None)
    book.close()
    return out.getvalue()


def _warner(person, key):
    employee = person['kind'] == 'employee'
    if key == 'warner:relationship':
        return WARNER_RELATIONSHIPS[person['relationship']]
    if key.startswith('warner:') and key.endswith('_tier'):
        return WARNER_TIERS.get(person.get(key[7:]), None) if employee else None
    if key == 'warner:status':
        return 'Active' if employee else None
    if key == 'warner:class':
        return 'All Eligible' if employee else None
    if key == 'warner:pay_mode':
        return 'Annual' if person.get('annual_salary') else None
    return _value(person, key)


def warner_xlsx(people):
    out = io.BytesIO()
    book = xlsx_safe.workbook(out)
    title = book.add_format({'bold': True, 'font_size': 14})
    head = book.add_format({'bold': True, 'bg_color': '#1F3864', 'font_color': '#FFFFFF', 'border': 1})
    hint = book.add_format({'italic': True, 'font_color': '#595959'})
    date = book.add_format({'num_format': 'mm/dd/yy'})
    sheet = book.add_worksheet('Census Template')
    sheet.merge_range(0, 1, 0, 23, 'CENSUS TEMPLATE (synthetic copy of the layout)', title)
    xlsx_safe.write_text(sheet, 1, 1, 'List each employee, then their dependents beneath them.')
    for col, (label, key) in enumerate(WARNER_COLUMNS, start=1):
        if key not in ('first_name', 'last_name'):  # MEMBER NAME is merged over First and Last below
            xlsx_safe.write_text(sheet, 2, col, label, head)
        if key in WARNER_HINTS:
            xlsx_safe.write_text(sheet, 3, col, WARNER_HINTS[key], hint)
    sheet.merge_range(2, 2, 2, 3, 'MEMBER NAME', head)
    examples = [
        ['Ex:', 'Employee', 'John', 'Sample', datetime.date(1980, 1, 1), 'M', '00000', None, 40, 'Active', 'ES'],
        [None, 'Spouse/Partner', 'Jane', 'Sample', datetime.date(1982, 2, 2), 'F', '00000'],
    ]
    for row, values in enumerate(examples, start=4):
        for col, value in enumerate(values):
            xlsx_safe.write(sheet, row, col, value, date if isinstance(value, datetime.date) else None)
    for number in range(1, WARNER_ROWS + 1):
        xlsx_safe.write(sheet, 5 + number, 0, number)
    for row, person in enumerate(people, start=6):
        for col, (_label, key) in enumerate(WARNER_COLUMNS, start=1):
            if key:
                value = _warner(person, key)
                xlsx_safe.write(sheet, row, col, value, date if isinstance(value, datetime.date) else None)
    book.close()
    return out.getvalue()


def files(spec):
    """(client file bytes, Warner copy bytes), made once per spec in a process."""
    key = json.dumps(spec['census'], sort_keys=True)
    if key not in _made:
        people = census_roster.people(spec)
        _made[key] = (client_xlsx(people), warner_xlsx(people))
    return _made[key]


def attach(user, deal, spec):
    """Upload GD4's census and its Warner copy, and import the census. {} for a spec with no census, or one whose
    census arrives at a later checkpoint (GD3's, at B: `arrive`)."""
    if not spec.get('census') or spec['census'].get('arrives'):
        return {}
    return _upload_and_import(user, deal, spec)


def arrive(user, deal, spec):
    """A census that arrives at a checkpoint (GD3's at B, slice 13): uploaded and imported as `attach` does."""
    return _upload_and_import(user, deal, spec)


def _upload_and_import(user, deal, spec):
    client, warner = files(spec)
    names = spec['census']
    uploaded = {
        'census': documents.upload(user, deal, SimpleUploadedFile(names['file'], client), {'kind': 'census'}),
        'warner': documents.upload(user, deal, SimpleUploadedFile(names['warner_file'], warner), {'kind': 'census'}),
    }
    proposed = census.create_import(user, deal.id, uploaded['census'].id)
    census.apply_import(user, proposed.id)
    return uploaded
