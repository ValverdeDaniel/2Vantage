"""The Q.3 contracts for commission (plan.md §12.3): the write paths, GETs write nothing, the permission matrix with the
deal owner and the commission tiers (OQ70, H102), ids past bigint and the lock order. Reads that cost a fixed number of
queries (Q.3 #4) are in test_scaling.py."""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from accounts.models import Profile
from commission import services
from commission.models import ClientSplit, Commission, Party, Record, Settings
from conftest import check_permissions, sweep_gets, write_path_contract
from deals.models import Client, Deal

pytestmark = pytest.mark.django_db


def signed_in(username, tier=None, staff=False):
    login = get_user_model().objects.create_user(username, f'{username}@example.com', 'pw-Example-1', is_staff=staff)
    if tier:
        Profile.objects.create(user=login, commissions_access=tier)
    client = APIClient()
    client.force_login(login)
    return client


@pytest.fixture
def tiers(anon_api, api, admin_api):
    """Q.3 #3's commission actors: `owner` is the deal's (and client's) owner at the default own tier, `producer`
    another user at own, then none and all (not staff), and an admin."""
    return {
        'signed_out': anon_api,
        'owner': api,
        'producer': signed_in('pat'),
        'none': signed_in('nell', tier='none'),
        'all': signed_in('alma', tier='all'),
        'admin': admin_api,
    }


@pytest.fixture
def party(db):
    return Party.objects.create(kind='partner', name='Riverside Partners (synthetic)')


@pytest.fixture
def record(user, deal, django_capture_on_commit_callbacks):
    """The deal sold and booked (slice 49): one medical record, its primary the deal's owner (`user`)."""
    from quotes import services as quotes

    plan = quotes.create_plan(user, deal, line='medical', role='alternate', carrier='Cigna', name='One', values={})
    with django_capture_on_commit_callbacks(execute=True):
        quotes.set_sold(user, plan.id, True)
    return Record.objects.get(deal=deal)


def samples(deal, party, record=None):
    return {
        'api/deals/<int:pk>/commission/book/': {'pk': deal.id},
        'api/deals/<int:pk>/commission/disclosure.pdf': {'pk': deal.id},
        'api/commissions/records/': {},
        'api/commissions/records/export/': {},
        'api/commissions/records/<int:pk>/': {'pk': getattr(record, 'id', 0)},
        'api/commissions/records/<int:pk>/shares/': {'pk': getattr(record, 'id', 0)},
        'api/commissions/records/<int:pk>/rebook/': {'pk': getattr(record, 'id', 0)},
        'api/commissions/people/': {},
        'api/commissions/people/export/': {},
        'api/commissions/people/<str:key>/': {'key': 'house'},
        'api/commissions/clients/': {'query': {'q': 'Example'}},
        'api/deals/<int:pk>/commission/': {'pk': deal.id},
        'api/deals/<int:pk>/commission/split/': {'pk': deal.id},
        'api/deals/<int:pk>/commission/split/preview/': {'pk': deal.id},
        'api/clients/<int:pk>/commission/split/': {'pk': deal.client_id},
        'api/clients/<int:pk>/commission/split/preview/': {'pk': deal.client_id},
        'api/clients/<int:pk>/commission/records/': {'pk': deal.client_id},
        'api/commissions/parties/': {},
        'api/commissions/parties/<int:pk>/': {'pk': party.id},
        'api/commissions/settings/': {},
    }


EVERYONE = {'signed_out': 401, 'owner': 200, 'producer': 200, 'none': 200, 'all': 200, 'admin': 200}
OWNER_OR_ALL = {'signed_out': 401, 'owner': 200, 'producer': 403, 'none': 403, 'all': 200, 'admin': 200}
A_TIER = {'signed_out': 401, 'owner': 200, 'producer': 200, 'none': 403, 'all': 200, 'admin': 200}
ALL_TIER = {'signed_out': 401, 'owner': 403, 'producer': 403, 'none': 403, 'all': 200, 'admin': 200}


def matrix(user):
    split = {'scope': 'deal', 'rows': [{'user': user.id, 'role': 'primary'}]}
    return [
        ('GET', 'api/deals/<int:pk>/commission/', EVERYONE),
        ('PATCH', 'api/deals/<int:pk>/commission/', EVERYONE, {'rates': {'medical': '5'}}),
        ('PUT', 'api/deals/<int:pk>/commission/split/', OWNER_OR_ALL, split),
        ('POST', 'api/deals/<int:pk>/commission/split/preview/', EVERYONE, split),
        ('GET', 'api/clients/<int:pk>/commission/split/', EVERYONE),
        ('PUT', 'api/clients/<int:pk>/commission/split/', OWNER_OR_ALL, split),
        ('POST', 'api/clients/<int:pk>/commission/split/preview/', EVERYONE, split),
        ('GET', 'api/commissions/parties/', A_TIER),
        ('POST', 'api/commissions/parties/', {**ALL_TIER, 'all': 201, 'admin': 201}, {'kind': 'partner', 'name': 'X'}),
        ('PATCH', 'api/commissions/parties/<int:pk>/', ALL_TIER, {'npn': '1234'}),
        ('GET', 'api/commissions/settings/', ALL_TIER),
        ('PATCH', 'api/commissions/settings/', ALL_TIER, {'confirm': True}),
        ('POST', 'api/deals/<int:pk>/commission/book/', ALL_TIER),
        ('GET', 'api/deals/<int:pk>/commission/disclosure.pdf', ALL_TIER),
        ('GET', 'api/commissions/records/', A_TIER),
        (
            'POST',
            'api/commissions/records/',
            {**ALL_TIER, 'all': 201, 'admin': 201},
            {'client_name': 'Outside Co.', 'line': 'dental'},
        ),
        ('GET', 'api/commissions/records/export/', A_TIER),
        ('GET', 'api/commissions/records/<int:pk>/', {**A_TIER, 'producer': 404}),
        ('PATCH', 'api/commissions/records/<int:pk>/', ALL_TIER, {'notes': 'Billed quarterly'}),
        (
            'PUT',
            'api/commissions/records/<int:pk>/shares/',
            ALL_TIER,
            {'shares': [{'role': 'house', 'pct': '100'}], 'reason': 'House account'},
        ),
        ('POST', 'api/commissions/records/<int:pk>/rebook/', ALL_TIER),
        ('GET', 'api/commissions/people/', A_TIER),
        ('GET', 'api/commissions/people/export/', A_TIER),
        ('GET', 'api/commissions/people/<str:key>/', A_TIER),
        ('GET', 'api/commissions/clients/', ALL_TIER),
        ('GET', 'api/clients/<int:pk>/commission/records/', A_TIER),  # the client page's Commissions tab (slice 68)
    ]


def test_Q3_commission_gets_write_nothing(admin_api, deal, party, record):
    sweep_gets(admin_api, ('commission',), samples(deal, party, record))


def test_Q3_OQ70_H102_commission_permission_matrix(tiers, no_csrf_api, user, deal, party, record):
    check_permissions(tiers, ('commission',), matrix(user), samples(deal, party, record), no_csrf_api)


def test_Q3_ids_past_bigint_answer_404(admin_api):
    big = 2**64
    assert admin_api.get(f'/api/deals/{big}/commission/').status_code == 404
    assert admin_api.put(f'/api/deals/{big}/commission/split/', {}, format='json').status_code == 404
    assert admin_api.post(f'/api/deals/{big}/commission/split/preview/', {}, format='json').status_code == 404
    assert admin_api.get(f'/api/clients/{big}/commission/split/').status_code == 404
    assert admin_api.get(f'/api/clients/{big}/commission/records/').status_code == 404
    assert admin_api.patch(f'/api/commissions/parties/{big}/', {}, format='json').status_code == 404


def test_Q3_junk_in_a_body_answers_400(api, deal):
    url = f'/api/deals/{deal.id}/commission/'
    assert api.patch(url, ['rates'], format='json').status_code == 400
    assert api.post(url + 'split/preview/', {'rows': 'x', 'revenue': 'lots'}, format='json').status_code == 400
    assert api.put(url + 'split/', {'rows': [{'party': 'abc', 'role': 'primary'}]}, format='json').status_code == 400


def test_Q3_rates_write_path(user, deal):
    write_path_contract(
        user,
        Commission.objects.create(deal=deal),
        lambda: services.update(user, deal.id, {'rates': {'medical': '5', 'dental': {'type': 'pepm', 'value': '2'}}}),
        lambda row: (row.rates, row.year_number),
        lambda: services.update(user, deal.id, {'rates': {'medical': '6'}}),
    )


def test_Q3_split_write_path(user, deal, party):
    rows = [{'user': user.id, 'role': 'primary'}, {'party': party.id, 'role': 'split', 'amount': '25'}]
    services.save_split(user, deal_id=deal.id, rows=rows[:1])  # the Party exists and the owner is set before
    write_path_contract(
        user,
        Commission.objects.get(deal=deal),
        lambda: services.save_split(user, deal_id=deal.id, rows=rows),
        lambda row: row.split,
        lambda: services.save_split(user, deal_id=deal.id, rows=[*rows[:1], {**rows[1], 'amount': '30'}]),
    )


def test_Q3_client_split_write_path(user, deal, party):
    services.save_split(user, client_id=deal.client_id, rows=[{'user': user.id, 'role': 'primary'}])
    rows = [{'user': user.id, 'role': 'primary'}, {'party': party.id, 'role': 'referral', 'amount': '10'}]
    write_path_contract(
        user,
        ClientSplit.objects.get(client=deal.client),
        lambda: services.save_split(user, client_id=deal.client_id, rows=rows),
        lambda row: row.rows,
        lambda: services.save_split(user, client_id=deal.client_id, rows=rows[:1]),
    )


def test_Q3_party_write_path(admin_user, party):
    write_path_contract(
        admin_user,
        party,
        lambda: services.save_party(admin_user, party.id, {'default_split': '15', 'npn': '123'}),
        lambda row: (row.default_split, row.npn),
        lambda: services.save_party(admin_user, party.id, {'npn': '456'}),
    )


def test_Q3_settings_write_path(admin_user):
    write_path_contract(
        admin_user,
        Settings.objects.create(pk=1),
        lambda: services.save_settings(admin_user, {'renewal_pct': '25'}),
        lambda row: (row.renewal_pct, row.confirmed_at),
        lambda: services.save_settings(admin_user, {'renewal_pct': '20'}),
    )


def test_Q3_writes_lock_the_deal_then_the_client_then_commission(user, deal):
    def tables(call):
        with CaptureQueriesContext(connection) as queries:
            call()
        locks = [
            q['sql'].split(' FROM ', 1)[1].split()[0] for q in queries.captured_queries if 'FOR UPDATE' in q['sql']
        ]
        return list(dict.fromkeys(locks))  # the order each table is first locked in

    deal_t, client_t, row_t = (f'"{model._meta.db_table}"' for model in (Deal, Client, Commission))
    assert tables(lambda: services.update(user, deal.id, {'rates': {'vision': '3'}})) == [deal_t, row_t]
    rows = [{'user': user.id, 'role': 'primary'}]
    assert tables(lambda: services.save_split(user, deal_id=deal.id, rows=rows))[:3] == [deal_t, client_t, row_t]


def test_Q3_record_ids_past_bigint_answer_404_and_junk_answers_400(admin_api, record):
    big = 2**64
    assert admin_api.get(f'/api/commissions/records/{big}/').status_code == 404
    assert admin_api.patch(f'/api/commissions/records/{big}/', {}, format='json').status_code == 404
    assert admin_api.get(f'/api/commissions/people/{big}/').status_code == 404
    assert admin_api.get('/api/commissions/people/nobody/').status_code == 404
    url = f'/api/commissions/records/{record.id}/'
    assert admin_api.patch(url, ['notes'], format='json').status_code == 400
    assert admin_api.put(url + 'shares/', {'shares': 'all', 'reason': 'x'}, format='json').status_code == 400
    assert (
        admin_api.post('/api/commissions/records/', {'line': 'medical', 'client': 'abc'}, format='json').status_code
        == 400
    )
    assert admin_api.get('/api/commissions/records/', {'status': 'gone'}).status_code == 400


def test_Q3_record_write_path(admin_user, record):
    write_path_contract(
        admin_user,
        record,
        lambda: services.edit_record(admin_user, record.id, {'premium_annual': '1200', 'policy_number': 'P-1'}),
        lambda row: (row.values, row.notes),
        lambda: services.edit_record(admin_user, record.id, {'premium_annual': '1300'}),
    )


def test_Q3_booking_locks_the_deal_then_its_records(user, deal, record):
    with CaptureQueriesContext(connection) as queries:
        services.rebook(user, deal.id)
    locks = [q['sql'].split(' FROM ', 1)[1].split()[0] for q in queries.captured_queries if 'FOR UPDATE' in q['sql']]
    assert list(dict.fromkeys(locks))[:2] == [f'"{Deal._meta.db_table}"', f'"{Record._meta.db_table}"']
