"""The census format lens (plan.md §8.12; K79–K88; OQ63): the list behind the readiness cards and chips, and one
format's detail, built by the same rows the download writes."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from rfp import services
from rfp.formats import fill

from .roster import add, crowd, dependent, employee, family

pytestmark = pytest.mark.django_db


def formats(api, deal):
    response = api.get(f'/api/deals/{deal.id}/rfp/formats/')
    assert response.status_code == 200
    return {found['key']: found for found in response.json()['formats']}


def detail(api, deal, key, **query):
    response = api.get(f'/api/deals/{deal.id}/rfp/formats/{key}/', query)
    assert response.status_code == 200, response.content
    return response.json()


def test_K79_K80_the_list_gives_each_formats_rows_columns_gaps_packet_and_what_to_fix(api, user, deal):
    family(user, deal)
    services.update(user, deal.id, {'carriers': {'add': ['unitedhealthcare']}})
    found = formats(api, deal)
    assert list(found) == ['census-warner', 'census-aetna', 'census-angle', 'census-uhc']
    uhc = found['census-uhc']
    assert (uhc['rows'], uhc['columns'], uhc['gaps'], uhc['max_rows']) == (4, 24, 3, 350)
    assert uhc['in_packet'] and uhc['required_by'] == ['UnitedHealthcare']
    assert found['census-angle']['file_formats'] == ['xlsx', 'csv']
    assert not found['census-aetna']['in_packet']
    assert uhc['to_fix'] == 0
    add(user, deal, [employee(9, gender='')])
    assert {key: found['to_fix'] for key, found in formats(api, deal).items()} == dict.fromkeys(found, 1)


def test_K83_K87_one_formats_columns_say_what_fills_them_and_how_full_they_are(api, user, deal):
    add(user, deal, [employee(1, gender=''), dependent(2, 1), employee(3)])
    found = detail(api, deal, 'census-aetna', rows=2)
    columns = {column['letter']: column for column in found['columns']}
    assert columns['E']['header'] == 'Gender' and columns['E']['fills']['text'] == 'our Gender'
    assert (columns['E']['expected'], columns['E']['blank'], columns['E']['required_blanks']) == (3, 1, 1)
    assert columns['F']['expected'] == 2  # the medical tier applies to employees only
    assert columns['H']['fills']['kind'] == 'derived' and 'EE' in columns['H']['translation']
    assert 'employee-only' in columns['I']['rules']
    assert found['geometry'] == 'rows 7–491, columns A–I'
    assert found['preview']['total_rows'] == 3 and len(found['preview']['rows']) == 2
    assert found['preview']['missing_cells'] == [[0, 4]]
    assert found['filled_pct'] < 100
    assert found['needs'] == [{'key': 'gender', 'label': 'Gender'}]


def test_K84_the_gap_queue_names_the_person_and_the_cell_to_fill_on_our_screen_only(api, user, deal):
    add(user, deal, [employee(1, first_name='Wren', gender='', zip='')])
    found = detail(api, deal, 'census-uhc')
    items = {item['field']: item for item in found['gap_items']}
    assert (
        items['zip']['derived'] and items['zip']['header'] == '*Out of Area (Medical Only)'
    )  # a derived column asks for its input
    assert items['gender']['person'] == 'Wren Synthetic'
    assert items['gender']['member_id'] and not items['gender']['derived']
    assert found['gap_total'] == len(found['gap_items'])
    built = fill.build_rows(deal, fill.resolve('uhc')[0])
    assert not any('Wren' in text for text in built.warnings)


def test_K88_the_gaps_and_the_columns_we_never_write_are_listed(api, user, deal):
    family(user, deal)
    found = detail(api, deal, 'census-uhc')
    assert [gap['header'] for gap in found['gaps']] == ['Applicant Id', 'Individual Applicant Id', 'Special Employee']
    assert found['not_sent']['unwritten_banner'] == 'Employee Information - Enrollment'
    assert found['not_sent']['columns'][0]['letter'] == 'Y'
    assert found['gap_notes'] and 'Active' in found['gap_notes'][0]
    assert found['geometry'] == 'rows 4–353, columns A–X of A–BX printed'


def test_K87_translation_notes_name_people_on_screen_and_count_them_in_the_warnings(api, user, deal):
    add(user, deal, [employee(1, first_name='Wren', medical_tier='Waived')])
    found = detail(api, deal, 'census-angle')
    note = next(n for n in found['notes'] if n['code'] == 'no_carrier_code')
    assert note['people'] == ['Wren Synthetic'] and 'Wren' not in note['text']
    assert note['text'] in found['warnings']


def test_K79_a_bad_key_or_row_count_answers_400(api, user, deal):
    family(user, deal)
    response = api.get(f'/api/deals/{deal.id}/rfp/formats/census-angle-csv/')
    assert response.status_code == 400 and 'census-angle' in response.json()['valid']
    assert api.get(f'/api/deals/{deal.id}/rfp/formats/census-uhc/', {'rows': 'x'}).status_code == 400
    assert api.get(f'/api/deals/{deal.id}/rfp/formats/census-uhc/', {'rows': 500}).status_code == 400


def test_Q3_4_the_lens_list_reads_in_a_fixed_number_of_queries(api, user, deal):
    from conftest import make_deal

    def count(target):
        with CaptureQueriesContext(connection) as captured:
            assert api.get(f'/api/deals/{target.id}/rfp/formats/').status_code == 200
        return len(captured.captured_queries)

    add(user, deal, crowd(1))
    bigger = make_deal(user, name='Bigger Co.')
    add(user, bigger, crowd(40))
    services.update(user, bigger.id, {'carriers': {'add': ['aetna', 'cigna']}})
    services.update(user, deal.id, {'carriers': {'add': ['unum']}})
    assert count(bigger) == count(deal)
