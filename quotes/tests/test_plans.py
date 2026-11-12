"""Plan rules through the API, and the write path (plan.md §3.7, §5.4, §12.3)."""

import threading
import time
from unittest import mock

import pytest
from django.db import connection

from conftest import make_deal
from deals.models import Activity
from quotes import services
from quotes import values as cleaning
from quotes.models import Plan


def add(api, deal, **data):
    data.setdefault('line', 'medical')
    data.setdefault('carrier', 'Aetna')
    data.setdefault('name', 'HDHP 3300')
    data.setdefault('role', 'current')
    response = api.post(f'/api/deals/{deal.id}/plans/', data, format='json')
    assert response.status_code == 201, response.json()
    return response.json()


@pytest.mark.parametrize(
    'field, raw, expected',
    [
        ('deductible_single', '$3,300', ('3300', None)),
        ('deductible_single', '20% after deductible', ('20% after deductible', None)),
        ('rate_ee', '$512.34', ('512.34', None)),
        ('rate_ee', 'N/A', ('', None)),
        ('rate_ee', '512.345', ('512.345', 'Rate — EE takes dollars and cents, not "512.345"')),
        ('unit_rate', '0.185', ('0.185', None)),
        ('rate_ee', 'abc', ('abc', 'Rate — EE takes a number, not "abc"')),
        ('minimum_value', 'y', ('Yes', None)),
        ('funding', 'Level-funded', ('level_funded', None)),
        (
            'sbc_url',
            'example.com',
            ('example.com', 'Summary of Benefits (SBC) link takes a web address starting with http:// or https://'),
        ),
    ],
)
def test_value_cleaning(field, raw, expected):
    assert cleaning.clean(field, raw) == expected


def test_role_and_link_rules(api, deal):
    current = add(api, deal)
    bad = api.post(
        f'/api/deals/{deal.id}/plans/',
        {'line': 'medical', 'role': 'renewal', 'carrier': 'Aetna', 'name': 'R'},
        format='json',
    )
    assert bad.status_code == 400
    add(api, deal, role='renewal', renews_id=current['id'])
    second = api.post(
        f'/api/deals/{deal.id}/plans/',
        {'line': 'medical', 'role': 'renewal', 'carrier': 'Aetna', 'name': 'R2', 'renews_id': current['id']},
        format='json',
    )
    assert second.status_code == 400 and 'already has a renewal' in str(second.json())
    other = add(api, deal, name='PPO 1500')
    consolidated = add(api, deal, role='alternate', carrier='UHC', name='U1', replaces_ids=[current['id'], other['id']])
    assert sorted(consolidated['replaces_ids']) == sorted([current['id'], other['id']])


def test_values_save_all_or_nothing_and_unknown_keys_are_refused(api, deal):
    plan = add(api, deal)
    response = api.patch(f'/api/plans/{plan["id"]}/', {'values': {'rate_ee': '500', 'rate_es': 'x'}}, format='json')
    assert response.status_code == 400 and 'rate_es' in response.json()['values']
    assert Plan.objects.get(pk=plan['id']).values == {}
    unknown = api.patch(f'/api/plans/{plan["id"]}/', {'values': {'den_annual_max': '1000'}}, format='json')
    assert unknown.status_code == 400


def test_an_unchanged_write_changes_nothing(api, deal, user):
    plan = add(api, deal, values={'deductible_single': '3300'})
    before = Plan.objects.get(pk=plan['id']).sources['deductible_single']
    activity_count = Activity.objects.count()
    _, changed = services.update_plan(user, plan['id'], {'values': {'deductible_single': '$3,300'}})
    after = Plan.objects.get(pk=plan['id']).sources['deductible_single']
    assert changed == [] and after == before and Activity.objects.count() == activity_count


@pytest.mark.django_db(transaction=True)
def test_two_concurrent_writes_to_different_keys_both_survive(user):
    deal = make_deal(user)
    plan = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='HDHP')
    real_clean = services.plans.clean_values

    def slow_clean(line, raw):
        time.sleep(0.2)  # hold the row between read and write
        return real_clean(line, raw)

    def write(key, value):
        try:
            services.update_plan(user, plan.id, {'values': {key: value}})
        finally:
            connection.close()

    with mock.patch.object(services.plans, 'clean_values', slow_clean):
        threads = [
            threading.Thread(target=write, args=('pcp_copay', '25')),
            threading.Thread(target=write, args=('er_copay', '300')),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert Plan.objects.get(pk=plan.id).values == {'pcp_copay': '25', 'er_copay': '300'}


def test_create_renewal_and_copy_as_alternate_copy_design_not_rates(api, deal):
    current = add(api, deal, values={'deductible_single': '3300', 'funding': 'fully_insured', 'rate_ee': '500'})
    renewal = api.post(f'/api/plans/{current["id"]}/renewal/').json()
    assert renewal['role'] == 'renewal' and renewal['renews_id'] == current['id']
    assert renewal['values'] == {'deductible_single': '3300', 'funding': 'fully_insured'}
    copy = api.post(f'/api/plans/{renewal["id"]}/copy/').json()
    assert copy['role'] == 'alternate' and copy['replaces_ids'] == [current['id']]
    assert 'rate_ee' not in copy['values']


def test_sold_and_recommended_any_number(api, deal):
    a = add(api, deal)
    b = add(api, deal, name='PPO')
    x = add(api, deal, role='alternate', carrier='Cigna', name='X', replaces_ids=[a['id']])
    y = add(api, deal, role='alternate', carrier='Cigna', name='Y', replaces_ids=[a['id']])
    refused = api.post(f'/api/plans/{a["id"]}/recommend/', {'recommended': True}, format='json')
    assert refused.status_code == 409
    assert (
        refused.json()['detail']
        == "A current plan can't be recommended — recommend its renewal to keep what they have."
    )
    for plan in (x, y):
        assert api.post(f'/api/plans/{plan["id"]}/recommend/', {'recommended': True}, format='json').json()[
            'recommended'
        ]
    sold = api.post(f'/api/plans/{x["id"]}/sold/', {'sold': True}, format='json').json()
    assert sold['deal']['stage'] == 'sold'
    api.post(f'/api/plans/{y["id"]}/sold/', {'sold': True}, format='json')
    assert Plan.objects.filter(deal=deal, sold=True).count() == 2
    comparison = api.get(f'/api/deals/{deal.id}/plans/?line=medical').json()
    assert comparison['recommendation']['covered'] is False
    assert comparison['recommendation']['missing'] == ['PPO']
    api.post(f'/api/plans/{x["id"]}/sold/', {'sold': False}, format='json')
    unsold = api.post(f'/api/plans/{y["id"]}/sold/', {'sold': False}, format='json').json()
    assert unsold['deal']['stage'] == 'proposal'
    del b


def test_enrollment_by_basis_and_comparison_prices(api, deal):
    a = add(api, deal, values={'rate_ee': '500', 'rate_es': '1000.50', 'rate_ec': '900.25', 'rate_fam': '1500.75'})
    response = api.post(
        f'/api/deals/{deal.id}/plans/enrollment/',
        {'plans': [{'id': a['id'], 'enrollment': {'EE': 10, 'ES': 3, 'EC': 2, 'FAM': 5}, 'on': True}]},
        format='json',
    )
    assert response.status_code == 200
    bad = api.post(
        f'/api/deals/{deal.id}/plans/enrollment/',
        {'plans': [{'id': a['id'], 'enrollment': {'lives': 4}}]},
        format='json',
    )
    assert bad.status_code == 400
    plans = api.get(f'/api/deals/{deal.id}/plans/?line=medical').json()['plans']
    assert plans[0]['premium']['monthly'] == 17306


def test_quoted_premium_only_plans_do_not_flag_tier_rates_missing(api, deal):
    add(api, deal, values={'group_premium_monthly': '15000'})
    cells = api.get(f'/api/deals/{deal.id}/plans/?line=medical').json()['plans'][0]['cells']
    assert 'rate_ee' not in cells and cells['deductible_single'] == {'s': 'missing'}


def test_member_built_packages(api, deal):
    a = add(api, deal)
    created = api.post(
        f'/api/deals/{deal.id}/plans/packages/',
        {'line': 'medical', 'name': 'Keep', 'plan_ids': [a['id']]},
        format='json',
    )
    assert created.status_code == 201
    duplicate = api.post(
        f'/api/deals/{deal.id}/plans/packages/', {'line': 'medical', 'name': 'Keep', 'plan_ids': []}, format='json'
    )
    assert duplicate.status_code == 400
    api.delete(f'/api/plans/{a["id"]}/')
    packages = api.get(f'/api/deals/{deal.id}/plans/packages/?line=medical').json()
    assert packages == [{'id': created.json()['id'], 'name': 'Keep', 'plan_ids': []}]
