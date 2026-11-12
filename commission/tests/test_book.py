"""The Book, By person, the exports and the CAA disclosure (plan.md §7.10, §8.18, §9.15; H45, H49–H53, H57, H68, H102,
H108; OQ73): what each tier sees, the filters, the tiles, and the files read back."""

import io

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from pypdf import PdfReader
from rest_framework.test import APIClient

from accounts.models import Profile
from commission import services
from commission.models import Party, Record
from conftest import make_deal
from quotes import services as quotes

pytestmark = pytest.mark.django_db


def signed_in(user):
    client = APIClient()
    client.force_login(user)
    return client


def person(username, tier=None):
    login = get_user_model().objects.create_user(username, f'{username}@example.com', 'pw-Example-1')
    if tier:
        Profile.objects.create(user=login, commissions_access=tier)
    return login


@pytest.fixture
def book(user, admin_user, django_capture_on_commit_callbacks):
    """Two clients: one sold through the app (medical at 5 % on $120,000, owned by `user`) and one booked by hand
    with a partner's referral, plus a void record."""
    deal = make_deal(user, name='Sold Co. (synthetic)', effective_date='2027-01-01')
    plan = quotes.create_plan(
        user, deal, line='medical', role='alternate', carrier='Cigna', name='One',
        values={'rate_ee': '500', 'rate_es': '500', 'rate_ec': '500', 'rate_fam': '500'},
    )  # fmt: skip
    quotes.set_enrollment(user, deal, 'medical', plans=[{'id': plan.id, 'enrollment': {'EE': 20}}])
    services.update(user, deal.id, {'rates': {'medical': '5', 'dental': '5'}})
    with django_capture_on_commit_callbacks(execute=True):
        quotes.set_sold(user, plan.id, True)
    partner = Party.objects.create(kind='partner', name='=Riverside Partners (synthetic)')
    hand = services.add_to_book(
        admin_user,
        {'client_name': 'Outside Co. (synthetic)', 'line': 'dental', 'carrier': 'Delta', 'premium_annual': '40000',
         'rate': '10', 'effective_date': '2026-07-01'},
    ).record  # fmt: skip
    services.set_shares(
        admin_user, hand.id, [{'role': 'house', 'pct': '75'}, {'party': partner.id, 'role': 'referral', 'pct': '25'}],
        'Referral agreed',
    )  # fmt: skip
    void = services.add_to_book(admin_user, {'client_name': 'Gone Co. (synthetic)', 'line': 'vision'}).record
    services.edit_record(admin_user, void.id, {'status': 'void'})
    return {'deal': deal, 'plan': plan, 'hand': hand, 'void': void, 'partner': partner}


def test_H49_H50_H45_the_book_lists_live_records_with_its_tiles(admin_api, book):
    answer = admin_api.get('/api/commissions/records/').json()
    names = {row['client_name'] for row in answer['rows']}
    assert names == {'Sold Co. (synthetic)', 'Outside Co. (synthetic)'}  # void hidden by default
    assert answer['totals']['expected'] == 6000 + 4000
    assert answer['totals']['house'] == 3600 + 3000 and answer['totals']['pool'] == 3400
    assert answer['capped'] is False
    voided = admin_api.get('/api/commissions/records/', {'status': 'void'}).json()['rows']
    assert [row['client_name'] for row in voided] == ['Gone Co. (synthetic)']
    found = admin_api.get('/api/commissions/records/', {'q': 'delta'}).json()['rows']
    assert [row['carrier'] for row in found] == ['Delta']
    by_party = admin_api.get('/api/commissions/records/', {'party': book['partner'].id}).json()['rows']
    assert [row['id'] for row in by_party] == [book['hand'].id]
    assert admin_api.get('/api/commissions/records/', {'year': '2026'}).json()['totals']['records'] == 1
    assert admin_api.get('/api/commissions/records/', {'client': 'x'}).status_code == 400


def test_H102_OQ73_the_own_tier_sees_its_own_records_and_its_own_share_only(api, user, book):
    rows = api.get('/api/commissions/records/').json()['rows']
    assert [row['client_name'] for row in rows] == ['Sold Co. (synthetic)']
    (share,) = rows[0]['shares']
    assert share['role'] == 'primary' and share['amount'] == 2400
    assert rows[0]['house_share'] is None
    assert 'house' not in api.get('/api/commissions/records/').json()['totals']
    other = signed_in(person('pat'))
    assert other.get('/api/commissions/records/').json()['rows'] == []
    assert other.get(f'/api/commissions/records/{book["hand"].id}/').status_code == 404
    assert signed_in(person('nell', tier='none')).get('/api/commissions/records/').status_code == 403


def test_H53_H57_the_record_drawer_shows_holes_and_history_to_the_all_tier(admin_api, api, book):
    record = Record.objects.get(deal=book['deal'])
    services.edit_record(book['deal'].owner, record.id, {'policy_number': 'POL-1'})
    answer = admin_api.get(f'/api/commissions/records/{record.id}/').json()
    assert answer['record']['policy_number'] == 'POL-1' and answer['record']['holes'] == []
    assert [row['action'] for row in answer['history']] == ['updated', 'booked']
    assert api.get(f'/api/commissions/records/{record.id}/').json()['history'] == []
    gone = Record.objects.get(pk=book['void'].id)
    assert {'premium', 'rate'} <= set(admin_api.get(f'/api/commissions/records/{gone.id}/').json()['record']['holes'])


def test_H68_by_person_rolls_up_each_share_and_the_own_tier_sees_its_own_row(admin_api, api, book):
    rows = admin_api.get('/api/commissions/people/').json()['rows']
    by_key = {row['key']: row for row in rows}
    assert by_key['house']['expected'] == 3600 + 3000
    assert by_key[book['partner'].id]['expected'] == 1000 and by_key[book['partner'].id]['records'] == 1
    assert sum(row['share_of_book'] for row in rows) == pytest.approx(100, abs=0.2)
    (mine,) = api.get('/api/commissions/people/').json()['rows']
    assert mine['kind'] == 'producer' and mine['expected'] == 2400
    drill = admin_api.get(f'/api/commissions/people/{book["partner"].id}/').json()['rows']
    assert [row['mine']['amount'] for row in drill] == [1000]
    assert api.get('/api/commissions/people/house/').json()['rows'] == []


def test_H52_the_book_export_has_the_16_columns_and_keeps_typed_text_as_text(admin_api, book):
    response = admin_api.get('/api/commissions/records/export/')
    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    sheet = workbook['Book']
    headers = [cell.value for cell in sheet[4]]
    assert headers[:3] == ['Client', 'LOB', 'Line'] and headers[-1] == 'Holes' and len(headers) == 16
    who = [row[14] for row in sheet.iter_rows(min_row=5, values_only=True) if row[0] == 'Outside Co. (synthetic)']
    assert who and who[0].startswith('House') and '=Riverside' in who[0]
    assert all(cell.data_type != 'f' for row in sheet.iter_rows() for cell in row)
    assert 'Totals' in workbook.sheetnames
    people = admin_api.get('/api/commissions/people/export/')
    assert 'By person' in openpyxl.load_workbook(io.BytesIO(people.content)).sheetnames


def test_H108_the_disclosure_prints_medical_dental_and_vision_rates_for_the_all_tier(admin_api, api, book):
    url = f'/api/deals/{book["deal"].id}/commission/disclosure.pdf'
    assert api.get(url).status_code == 403
    response = admin_api.get(url)
    assert response.status_code == 200 and response['Content-Type'] == 'application/pdf'
    text = ' '.join(page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages)
    assert 'Medical Insurance' in text and '5%' in text and 'Cigna' in text
    assert 'Medical Stop Loss Insurance' in text
    assert '2,400' not in text and '3,600' not in text  # never a split or anyone's earnings
    bare = make_deal(book['deal'].owner, name='Nothing Booked Co.')
    assert admin_api.get(f'/api/deals/{bare.id}/commission/disclosure.pdf').status_code == 409


def test_H38_the_deal_facts_count_booked_records_in_a_fixed_number_of_queries(book, user):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    from commission import summary

    other = make_deal(user, name='Not Sold Co.')
    with CaptureQueriesContext(connection) as one:
        summary.facts([book['deal'].id])
    with CaptureQueriesContext(connection) as two:
        found = summary.facts([book['deal'].id, other.id])
    assert len(one.captured_queries) == len(two.captured_queries)
    assert found[book['deal'].id]['records'] == 1 and found[book['deal'].id]['booked_expected'] == 6000
    assert found[book['deal'].id]['rated_lines'] == ['dental', 'medical']
    assert found[other.id] == {'rated_lines': [], 'records': 0, 'booked_expected': None, 'holes': 0, 'booked': False}
