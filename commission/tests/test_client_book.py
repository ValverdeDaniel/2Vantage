"""The client page's Commissions tab (plan.md §7.10, §8.5; CL25, H106; Q.9 row 68): `GET clients/{id}/commission/
records/` — GD1-sold's booked records by plan year in the viewer's tier (all: every share and the house's figures; own:
only the records it holds a share in, and only its own share; none: 403), and a 60/40 client split that saves, which a
Rebook carries into the records. GD1-sold from the root conftest (`gd1_sold` read-only, `sell_gd1` when it writes)."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import Profile
from commission.models import ClientSplit

pytestmark = pytest.mark.django_db

KEY_TOTAL = 20490.6  # golden/keys/gd1-sold.json: 10,454.40 + 10,036.20


def person(username, *, tier=None, staff=False):
    login = get_user_model().objects.create_user(username, f'{username}@example.com', 'pw-Example-1', is_staff=staff)
    if tier:
        Profile.objects.create(user=login, commissions_access=tier)
    return login


def signed_in(login):
    client = APIClient()
    client.force_login(login)
    return client


def records(api, client_id):
    return api.get(f'/api/clients/{client_id}/commission/records/')


def test_Q9_68_GD1_sold_the_all_tier_sees_every_record_every_share_and_the_house_by_plan_year(admin_api, gd1_sold):
    deal = gd1_sold.deal
    response = records(admin_api, deal.client_id)
    assert response.status_code == 200
    payload = response.json()
    assert payload['tier'] == 'all' and len(payload['rows']) == 2
    assert {row['carrier'] for row in payload['rows']} == {'Cigna', 'UnitedHealthcare'}
    for row in payload['rows']:
        assert [share['role'] for share in row['shares']] == ['house', 'primary']
        assert row['house_share'] is not None
    assert payload['totals']['expected'] == KEY_TOTAL
    assert payload['totals']['house'] + payload['totals']['pool'] == pytest.approx(KEY_TOTAL)
    [year] = payload['years']
    assert year['key'] == str(deal.effective_date.year) and year['deal_id'] == deal.id
    assert year['expected'] == KEY_TOTAL and year['house'] == payload['totals']['house']
    assert sorted(year['records']) == sorted(row['id'] for row in payload['rows'])
    assert year['disclosure'] is True and year['change_pct'] is None


def test_Q9_68_an_own_tier_producer_sees_only_the_records_they_share_and_only_their_own_share(api, user, sell_gd1):
    """`user` is a producer (no Profile: the own tier) and GD1-sold's owner, so the primary on both records."""
    client_id = sell_gd1.deal.client_id
    payload = records(api, client_id).json()
    assert payload['tier'] == 'own' and len(payload['rows']) == 2
    for row in payload['rows']:
        assert [share['role'] for share in row['shares']] == ['primary']
        assert row['house_share'] is None
    assert 'house' not in payload['totals'] and 'pool' not in payload['totals']
    assert 'house' not in payload['years'][0] and payload['years'][0]['disclosure'] is False
    stranger = signed_in(person('own-stranger'))
    assert records(stranger, client_id).json()['rows'] == []  # no share in them: no record
    assert records(signed_in(person('no-tier', tier='none')), client_id).status_code == 403


def test_H106_CL25_a_60_40_client_split_saves_and_a_rebook_carries_it_to_the_records(admin_api, user, sell_gd1):
    deal = sell_gd1.deal
    producer = person('pat-secondary')
    rows = [{'user': user.id, 'role': 'primary'}, {'user': producer.id, 'role': 'secondary', 'amount': '40'}]
    saved = admin_api.put(f'/api/clients/{deal.client_id}/commission/split/', {'rows': rows}, format='json')
    assert saved.status_code == 200 and saved.json()['saved'] is True
    split = admin_api.get(f'/api/clients/{deal.client_id}/commission/split/').json()
    assert split['split']['source'] == 'client'
    assert [(row['role'], row['amount_label']) for row in split['split']['rows']] == [
        ('primary', ''),
        ('secondary', '40%'),
    ]
    shares = {share['role']: share['pct_label'] for share in split['preview']['shares']}
    assert shares == {'house': '60.0%', 'primary': '24.0%', 'secondary': '16.0%'}  # 60/40 of the first year's 40 % pool
    assert ClientSplit.objects.filter(client_id=deal.client_id).exists()

    assert admin_api.post(f'/api/deals/{deal.id}/commission/book/').status_code == 200  # Rebook takes the client split
    mine = records(signed_in(producer), deal.client_id).json()
    assert len(mine['rows']) == 2
    for row in mine['rows']:
        [share] = row['shares']
        assert (share['role'], share['pct_label']) == ('secondary', '16.0%')
        assert share['amount'] == pytest.approx(row['expected'] * 0.16, abs=0.01)
    every = records(admin_api, deal.client_id).json()
    assert {share['role'] for row in every['rows'] for share in row['shares']} == {'house', 'primary', 'secondary'}


def test_CL25_unknown_clients_and_ids_past_bigint_are_404(admin_api):
    assert records(admin_api, 2**63).status_code == 404
    assert records(admin_api, 999999).status_code == 404
