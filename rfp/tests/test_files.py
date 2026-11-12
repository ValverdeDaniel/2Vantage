"""The carrier census files, downloaded and read back (plan.md §9.8, §3.8; K82, K90–K97, K101, K107, K113; OQ61;
Q.9 row 45: each file matches its template, the printed count equals the band, no member value in errors)."""

import io

import openpyxl
import pytest

from deals.models import Activity
from quotes import facts as quote_facts
from rfp import services
from rfp.formats import fill
from rfp.xlsx.package import read_sheet

from .roster import book, crowd, dependent, employee, family

pytestmark = pytest.mark.django_db


def download(api, deal, key):
    return api.get(f'/api/deals/{deal.id}/rfp/files/{key}/')


def test_K113_a_census_file_downloads_named_for_the_client_and_the_carrier_and_is_logged(api, user, deal):
    family(user, deal)
    before = Activity.objects.filter(deal=deal, action='downloaded').count()
    response = download(api, deal, 'census-aetna')
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert response['Content-Disposition'] == 'attachment; filename="Example Co. - Aetna census.xlsx"'
    assert response['Cache-Control'] == 'private, no-store'
    rows = Activity.objects.filter(deal=deal, action='downloaded').order_by('-id')
    assert rows.count() == before + 1
    assert rows[0].summary == 'Downloaded the Aetna census file'
    assert 'Avery' not in rows[0].summary


def test_K90_the_warner_file_is_warners_workbook_with_the_roster_typed_and_the_examples_cleared(api, user, deal):
    family(user, deal)
    content = b''.join(download(api, deal, 'census-warner').streaming_content)
    ws = book(content)['Census Template']
    assert ws['A5'].value is None and ws['C5'].value is None  # Warner's "Ex:" John Doe rows are gone
    assert [ws.cell(row=r, column=2).value for r in range(7, 11)] == ['Employee', 'Spouse/Partner', 'Child/Dependent',
                                                                       'Employee']  # fmt: skip
    assert ws['C7'].value == 'Avery' and ws['E7'].value.year == 1980  # a real date
    assert ws['U7'].value == 61500 and ws['V7'].value == 'Annual'  # a number, and its pay mode
    assert ws['S7'].value == ws['X7'].value == 'Salaried'  # OQ109
    assert ws['G10'].value == '07030'  # a leading zero keeps the ZIP text
    assert ws['A7'].value == 1  # Warner's own row counter, untouched
    assert len(ws.data_validations.dataValidation) == 4  # their drop-downs survive


def test_K93_each_carriers_file_carries_the_roster_in_its_own_columns(api, user, deal):
    family(user, deal)
    aetna = book(b''.join(download(api, deal, 'census-aetna').streaming_content))['Census Input']
    assert (aetna['A7'].value, aetna['H7'].value, aetna['F7'].value) == ('Synthetic', 'EE', 'EEOnly')
    assert aetna['A4'].value is None  # Aetna's sample row cleared
    angle = book(b''.join(download(api, deal, 'census-angle').streaming_content))['Sheet1']
    assert (angle['B10'].value, angle['D10'].value, angle['E10'].value) == ('Avery', 'Employee', 'Female')
    uhc = book(b''.join(download(api, deal, 'census-uhc').streaming_content))
    roster = uhc['Employee Info']
    assert (roster['A4'].value, roster['F4'].value, roster['Q4'].value) == ('Employee', 'Synthetic', 'No')
    assert roster['L7'].value == 'Cobra'


def test_K101_K17_uhcs_group_tab_prints_the_bands_count_and_the_requests_funding(api, user, deal):
    family(user, deal)
    services.update(user, deal.id, {'funding': {'remove': ['level_funded', 'aso']}})
    group = book(b''.join(download(api, deal, 'census-uhc').streaming_content))['Group Info']
    count = quote_facts.enrolled_headcount(deal)['count']
    assert group['B13'].value == count
    assert group['A5'].value == 'Example Co.'
    assert group['H5'].value == 'Fully Insured'
    assert (group['I5'].value, group['L5'].value) == ('Quote', 'Do not Quote')
    assert group['F13'].value == 2  # FTE: both employees work 40 hours


def test_K93_aetnas_selector_follows_the_funding_asked(api, user, deal):
    family(user, deal)
    services.update(user, deal.id, {'funding': {'remove': ['fully_insured', 'aso'], 'add': ['level_funded']}})
    ws = book(b''.join(download(api, deal, 'census-aetna').streaming_content))['Census Input']
    assert ws['J1'].value == 'AFA UW'


def test_K90_uhcs_formulas_that_read_the_roster_are_recalculated_on_open(api, user, deal):
    family(user, deal)
    content = b''.join(download(api, deal, 'census-uhc').streaming_content)
    import zipfile

    assert 'fullCalcOnLoad="1"' in zipfile.ZipFile(io.BytesIO(content)).read('xl/workbook.xml').decode()


def test_K91_K107_angles_csv_is_the_filled_sheet_and_fences_formula_like_text(api, user, deal):
    from .roster import add

    add(user, deal, [employee(1, first_name='=cmd', last_name='Synthetic')])
    response = download(api, deal, 'census-angle-csv')
    assert response['Content-Type'] == 'text/csv'
    assert response['Content-Disposition'].endswith('Angle Health census.csv"')
    text = b''.join(response.streaming_content).decode('utf-8-sig')
    assert ",'=cmd,Synthetic,Employee,Female,01/15/1980,33101,Employee," in text


def test_K97_OQ61_a_roster_past_the_cap_stops_there_with_a_truthful_warning_and_the_csv_carries_everyone(user, deal):
    people = crowd(215)
    built = fill.build(deal, 'angle', people=people)
    ws = openpyxl.load_workbook(io.BytesIO(built.content))['Sheet1']
    assert ws.cell(row=10 + 212, column=2).value == 'Avery213'
    assert ws.cell(row=10 + 213, column=2).value is None
    assert any('room for 213 people; the last 2 on the census do not fit' in text for text in built.warnings)
    csv_file = fill.build(deal, 'angle-csv', people=people)
    assert 'Avery215' in csv_file.content.decode('utf-8-sig')
    assert not any('do not fit' in text for text in csv_file.warnings)


def test_Q9_45_no_member_value_reaches_a_files_warnings(user, deal):
    people = [employee(1, first_name='Zelda', medical_tier='Platinum', employment_status='Terminated'),
              dependent(2, 1, first_name='Quill', relationship='')]  # fmt: skip
    for key in fill.file_keys():
        built = fill.build(deal, key, people=people)
        text = ' '.join(built.warnings)
        assert built.warnings and 'Zelda' not in text and 'Quill' not in text and 'Platinum' not in text


def test_K41_no_census_answers_409_and_an_unknown_key_400(api, deal):
    assert download(api, deal, 'census-uhc').status_code == 409
    assert download(api, deal, 'census-cigna').status_code == 400
    assert download(api, deal, 'questionnaire-nobody').status_code == 400  # a key this deal's packet does not have


def test_K82_the_real_file_look_is_the_built_file_in_windows_and_is_logged(api, user, deal):
    family(user, deal)
    response = api.get(f'/api/deals/{deal.id}/rfp/files/census-uhc/look/')
    assert response.status_code == 200
    data = response.json()
    assert data['sheet'] == 'Employee Info'  # it opens on the roster, not the group tab
    assert [s['name'] for s in data['sheets']][:2] == ['Group Info', 'Employee Info']
    assert data['rows'][3][0] == 'Employee' and data['format'] is not None
    content = b''.join(download(api, deal, 'census-uhc').streaming_content)
    found, shared = read_sheet(content, 'Employee Info')
    assert data['rows'][3][5] == found.text_at('F4', shared)
    assert Activity.objects.filter(deal=deal, action='viewed', area='rfp').exists()
    other = api.get(f'/api/deals/{deal.id}/rfp/files/census-uhc/look/', {'sheet': 'Group Info'}).json()
    assert other['sheet'] == 'Group Info'
    assert api.get(f'/api/deals/{deal.id}/rfp/files/census-uhc/look/', {'start': 'x'}).status_code == 400
    csv_look = api.get(f'/api/deals/{deal.id}/rfp/files/census-angle-csv/look/').json()
    assert csv_look['rows'][9][1] == 'Avery'


def test_Q9_45_on_gd6_the_band_and_every_printed_count_agree(get_to_market):
    """GD6 (60 people on its census, 51+): the band's count is what UHC's group tab prints, and the carrier files
    carry the whole roster in each carrier's own columns."""
    built = get_to_market.step('census_arrives').built
    deal = built.deal
    count = quote_facts.enrolled_headcount(deal)['count']
    uhc = fill.build(deal, 'uhc')
    group = openpyxl.load_workbook(io.BytesIO(uhc.content))['Group Info']
    assert group['B13'].value == count and count >= 51
    people = len(uhc.built.rows)
    for key in ('warner', 'aetna', 'angle'):
        assert len(fill.build(deal, key).built.rows) == people
