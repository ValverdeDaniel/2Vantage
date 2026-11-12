"""The census template and export (plan.md §9.1, §9.2; C38; Q.9 row 41): the blank template's columns follow the lines
to quote, it re-imports at full confidence, a prefilled copy re-imports with nothing to change, the export lists every
column and each person's issues, and a file with member data writes one `downloaded` row (§3.8)."""

import io

import pytest

from census import fields, services, template
from census.importer import mapping, open_table
from census.models import Member
from conftest import make_deal
from deals.models import Activity

from .helpers import family, import_file, imported, roster, xlsx

pytestmark = pytest.mark.django_db

SMITH = family('E1', 'Smith', tier='ES', deps=[('Spouse', 'Blake', '02/02/1981')])
LEE = family('E3', 'Lee', first='Robin', dob='03/04/1979', zip_code='02139')
EVERY_LINE = ('medical', 'dental', 'vision', 'basic_life_add', 'std')


def book(content):
    import openpyxl

    return openpyxl.load_workbook(io.BytesIO(content))


def headers(content):
    return [cell.value for cell in book(content)['Census'][1]]


def test_C38_the_blank_template_asks_for_the_lines_quoted_and_the_columns_required(user):
    deal = make_deal(user, requested_lines=('medical',))
    content, prefilled = template.template(deal)
    assert prefilled == 0
    found = book(content)
    assert found.sheetnames == ['Census', 'How to fill this in']
    labels = headers(content)
    assert 'Medical Tier' in labels and 'Date of Birth' in labels
    assert not {'Dental Tier', 'Vision Plan', 'STD Benefit Amount'} & set(labels)
    first = found['Census']['A1']
    assert (first.font.bold, first.fill.fgColor.rgb[-6:], found['Census'].freeze_panes) == (True, '173A63', 'A2')
    guide = [row for row in found['How to fill this in'].iter_rows(values_only=True) if row[0]]
    assert guide[0][0] == 'Employee census — Example Co.'
    needed = dict(guide)['Needed to quote']
    assert 'Medical Tier' in needed and 'Dental Tier' not in needed


@pytest.mark.parametrize('lines', [('medical',), EVERY_LINE])
def test_Q9_41_C38_the_blank_template_re_imports_at_full_confidence(user, lines):
    deal = make_deal(user, requested_lines=lines)
    content, _ = template.template(deal)
    opened = open_table('census template.xlsx', content)
    proposed = mapping.propose(opened.table.headers)
    by_label = {fields.label(key): key for key in fields.KEYS}
    assert [item['field'] for item in proposed] == [by_label[header] for header in headers(content)]
    assert not [item['header'] for item in proposed if item['low']]


def test_Q9_41_C38_a_prefilled_template_re_imports_with_nothing_to_change(user, api):
    deal = make_deal(user, requested_lines=EVERY_LINE)
    imported(user, deal, xlsx(roster(SMITH, LEE)))
    Member.objects.filter(values__first_name='Robin').update(values={'first_name': 'Robin', 'last_name': 'Lee'})
    services.edit_values(user, Member.objects.get(values__first_name='Robin').id, {'dob': '3/4/1979', 'zip': '2139'})
    response = api.get(f'/api/deals/{deal.id}/census/template/')
    assert response.status_code == 200
    assert response['Content-Disposition'] == 'attachment; filename="Example Co. - Census template.xlsx"'
    content = b''.join(response.streaming_content)
    rows = list(book(content)['Census'].iter_rows(min_row=2, values_only=True))
    assert [row[headers(content).index('First Name')] for row in rows] == ['Avery', 'Blake', 'Robin']
    assert rows[2][headers(content).index('ZIP')] == '02139'  # text, its leading zero kept
    assert rows[2][headers(content).index('Date of Birth')] == '03/04/1979'
    again = import_file(user, deal, content, name='census template (returned).xlsx')
    answer = services.dry_run(again.id)
    assert answer['added'] == answer['changed'] == answer['removed'] == answer['kept'] == []
    assert answer['counts']['unchanged'] == 3
    downloaded = Activity.objects.filter(deal=deal, action='downloaded').get()
    assert downloaded.summary == 'Downloaded the census template, prefilled'


def test_C38_a_blank_template_carries_no_one_and_logs_nothing(user, api):
    deal = make_deal(user)
    response = api.get(f'/api/deals/{deal.id}/census/template/')
    assert response.status_code == 200
    assert not Activity.objects.filter(deal=deal, action='downloaded').exists()


def test_D114_a_value_that_begins_like_a_formula_stays_text(user):
    deal = make_deal(user, requested_lines=('medical',))
    imported(user, deal, xlsx(roster(family('E1', 'Smith'))))
    person = Member.objects.get(deal=deal)
    services.edit_values(user, person.id, {'job_title': '=HYPERLINK("http://x","y")'})
    cell = next(cell for cell in book(template.template(deal)[0])['Census'][2] if str(cell.value or '').startswith('='))
    assert (cell.data_type, cell.quotePrefix) == ('s', True)


def test_9_2_the_export_lists_every_column_and_each_persons_issues(user, api):
    deal = make_deal(user, requested_lines=('medical',))
    imported(user, deal, xlsx(roster(SMITH, LEE)))
    services.edit_values(user, Member.objects.get(values__first_name='Robin').id, {'dob': 'soon', 'ssn': '123456789'})
    response = api.get(f'/api/deals/{deal.id}/census/export/')
    assert response['Content-Disposition'] == 'attachment; filename="Example Co. - Census.xlsx"'
    content = b''.join(response.streaming_content)
    labels = headers(content)
    assert labels == ['Type', *[fields.label(key) for key in fields.KEYS], 'Issues']
    rows = list(book(content)['Census'].iter_rows(min_row=2, values_only=True))
    assert [row[0] for row in rows] == ['Employee', 'Dependent', 'Employee']
    assert rows[2][labels.index('SSN')] == '123-45-6789'  # staff only: unmasked
    assert rows[2][-1] == 'Could not read "soon" as a date'
    assert Activity.objects.filter(deal=deal, action='downloaded').get().summary == 'Downloaded the census'
