"""Priced versions through their doors (plan.md §5.4, §7.8; F76–F84; Q.9 row 35: the dry run equals the commit; no
auto star on an unstarred line). Synthetic deals; GD1's done-when is in test_golden_advisor.py."""

import threading
import time
from unittest import mock

import pytest
from django.db import connection

from conftest import make_deal, write_path_contract
from deals.models import Activity
from quotes import flags, order, services
from quotes.models import Plan
from quotes.selectors import line_state
from quotes.services import priced

pytestmark = pytest.mark.django_db

RATES = {'rate_ee': '489.15', 'rate_es': '1051.67', 'rate_ec': '916.66', 'rate_fam': '1508.92'}
COUNTS = {'EE': 10, 'ES': 3, 'EC': 2, 'FAM': 5}
FIVE_OFF = {'kind': 'concession', 'all': {'op': 'pct_off', 'value': 5}}


def make_line(user, deal):
    a = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='HMO 1500', values=RATES)
    services.set_enrollment(user, deal, 'medical', plans=[{'id': a.id, 'enrollment': COUNTS}])
    cigna = services.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='Cigna',
        name='HDHP 3000',
        replaces_ids=[a.id],
        values={**RATES, 'group_premium_monthly': '20000', 'deductible_single': '3000'},
    )
    uhc = services.create_plan(
        user, deal, line='medical', role='alternate', carrier='UHC', name='Choice', replaces_ids=[a.id], values=RATES
    )
    dental = services.create_plan(user, deal, line='dental', role='alternate', carrier='Cigna', name='Dental PPO')
    return {'a': a, 'cigna': cigna, 'uhc': uhc, 'dental': dental}


@pytest.fixture
def line(user, deal):
    return make_line(user, deal)


def post(api, deal, body, code=200):
    response = api.post(f'/api/deals/{deal.id}/plans/priced/', body, format='json')
    assert response.status_code == code, response.json()
    return response.json()


def shown(api, deal, line_key='medical'):
    return {plan['id']: plan for plan in api.get(f'/api/deals/{deal.id}/plans/?line={line_key}').json()['plans']}


def test_F76_Q9_the_dry_run_equals_the_commit_and_writes_nothing(api, deal, line):
    cigna = line['cigna']
    body = {'plan_ids': [cigna.id], **FIVE_OFF, 'note': 'per the rep'}
    plans, log = Plan.objects.count(), Activity.objects.count()
    dry = post(api, deal, {**body, 'dry_run': True})
    assert (Plan.objects.count(), Activity.objects.count()) == (plans, log)
    (draft,) = dry['drafts']
    assert (draft['original_id'], draft['name'], draft['label']) == (
        cigna.id,
        'HDHP 3000 — 5% concession',
        '5% concession',
    )
    assert draft['changes'] == {
        'rate_ee': '464.69',
        'rate_es': '999.09',
        'rate_ec': '870.83',
        'rate_fam': '1433.47',
        'group_premium_monthly': '19000',
    }
    made = post(api, deal, body, code=201)
    (version,) = made['plans']
    assert made['drafts'] == dry['drafts']
    board = shown(api, deal)
    for key in ('premium', 'change', 'credit', 'enrollment_used', 'enrollment_source'):
        assert board[version['id']][key] == draft[key], key
    assert board[version['id']]['values'] == {**board[cigna.id]['values'], **draft['changes']}
    assert draft['premium']['monthly'] < board[cigna.id]['premium']['monthly']


def test_F76_F87_a_version_rides_behind_its_original_and_prices_its_people(api, user, deal, line):
    cigna = line['cigna']
    made = post(api, deal, {'plan_ids': [cigna.id], **FIVE_OFF}, code=201)['plans'][0]
    board = shown(api, deal)
    ids = list(board)
    assert ids.index(made['id']) == ids.index(cigna.id) + 1
    assert board[made['id']]['enrollment_used'] == board[cigna.id]['enrollment_used'] == COUNTS
    assert board[made['id']]['enrollment_source'] == 'from original plan'
    assert (made['role'], made['replaces_ids'], made['derived_from']) == ('alternate', [line['a'].id], cigna.id)
    assert made['derived']['ops'][0] == {'key': 'rate_ee', 'op': 'pct_off', 'value': 5}
    services.arrange(user, deal, 'medical', ('move', cigna.id, 1, None))
    after = [plan.id for plan in line_state(deal, 'medical').plans]
    assert after.index(made['id']) == after.index(cigna.id) + 1  # it moves with its original (F120)


def test_F77_a_version_keeps_its_originals_design_and_sources_but_a_changed_rate_loses_the_file(user, deal, line):
    cigna = Plan.objects.get(pk=line['cigna'].id)
    cigna.sources['rate_ee'] = {'origin': 'ai', 'doc': 4, 'page': 2, 'low': True, 'mark': {'state': 'check'}}
    cigna.sources['deductible_single'] = {'origin': 'ai', 'doc': 4, 'page': 1, 'read_value': '3000'}
    cigna.save()
    result = priced.price(user, deal, [cigna.id], FIVE_OFF)
    (version,) = result.plans
    version.refresh_from_db()
    assert version.values['deductible_single'] == '3000'
    assert version.sources['deductible_single'] == {'origin': 'ai', 'doc': 4, 'page': 1}
    assert version.sources['rate_ee']['origin'] == 'typed' and 'doc' not in version.sources['rate_ee']
    assert (version.starred, version.recommended, version.sold) == (False, False, False)
    assert flags.rebuild([deal.id]) == []  # the stored count is right (Q.3 #9)
    row = Activity.objects.get(pk=result.row.id)
    assert (row.action, row.summary, row.revertible) == ('created', 'Priced Cigna HDHP 3000: 5% concession', False)


def test_F83_Q9_no_auto_star_on_a_line_with_no_stars(user, deal, line):
    result = priced.price(user, deal, [line['cigna'].id], FIVE_OFF)
    assert not result.plans[0].starred and result.warning == ''


def test_F83_a_new_version_is_starred_while_its_starred_line_has_room(user, deal, line):
    services.star(user, deal, [line['uhc'].id], True)
    result = priced.price(user, deal, [line['cigna'].id], FIVE_OFF)
    version = Plan.objects.get(pk=result.plans[0].id)
    assert (version.starred, version.star_reason) == (True, '5% concession')
    assert not Plan.objects.get(pk=line['cigna'].id).starred  # the original's star is its own


def test_F83_past_the_room_a_version_is_added_unstarred_with_a_warning(user, deal, line):
    a = line['a']
    for n in range(14):
        services.create_plan(
            user, deal, line='medical', role='alternate', carrier='Oscar', name=f'Q{n}', replaces_ids=[a.id]
        )
    quotes = Plan.objects.filter(deal=deal, line='medical', role='alternate').exclude(pk=line['cigna'].id)
    services.star(user, deal, list(quotes.values_list('id', flat=True))[:15], True)
    result = priced.price(user, deal, [line['cigna'].id], FIVE_OFF)
    assert not result.plans[0].starred
    assert result.warning == 'The Medical shortlist is full — the 5% concession was added unstarred.'


def test_F77_refusals_answer_409_and_bad_requests_400(api, user, deal, line):
    a, cigna = line['a'], line['cigna']
    assert 'in-force baseline' in post(api, deal, {'plan_ids': [a.id], **FIVE_OFF}, 409)['detail']
    below = {'kind': 'concession', 'each': {'rate_ee': {'op': 'flat_off', 'value': 600}}}
    assert post(api, deal, {'plan_ids': [cigna.id], **below}, 409)['detail'] == (
        'Rate — EE: the change lands below zero (-110.85).'
    )
    services.set_sold(user, cigna.id, True)
    sold = post(api, deal, {'plan_ids': [cigna.id], **FIVE_OFF}, 409)['detail']
    assert sold.startswith('Cigna — HDHP 3000 is already sold')
    both = post(api, deal, {'plan_ids': [line['uhc'].id, line['dental'].id], **FIVE_OFF}, 409)['detail']
    assert both == 'Priced versions apply to one line of business at a time.'
    assert post(api, deal, {'plan_ids': [line['uhc'].id], 'kind': 'concession'}, 400)['detail'] == (
        'Set a change for all rates, or for at least one rate.'
    )
    assert 'plan_ids' in post(api, deal, {'plan_ids': ['x'], **FIVE_OFF}, 400)
    assert 'plan_ids' in post(api, deal, {'plan_ids': [], **FIVE_OFF}, 400)
    other = make_deal(user, name='Other Co.')
    assert 'plan_ids' in post(api, other, {'plan_ids': [line['uhc'].id], **FIVE_OFF}, 400)


def test_F78_a_bundle_prices_each_quote_of_the_carrier_and_names_what_must_sell(api, user, deal, line):
    cigna, uhc, dental = line['cigna'], line['uhc'], line['dental']
    body = {
        'plan_ids': [cigna.id, uhc.id],
        'kind': 'bundle',
        'parts': [{'line': 'dental', 'op': 'pct_off', 'value': 2, 'plan_id': dental.id}],
    }
    made = post(api, deal, body, code=201)
    names = [plan['name'] for plan in made['plans']]
    assert names == ['HDHP 3000 — 2% bundled (Dental)', 'Choice — 2% bundled (Dental)']
    derived = made['plans'][0]['derived']
    assert (derived['requires'], derived['conditional'], derived['pct']) == ([dental.id], True, 2)
    assert derived['parts'][0]['plan_label'] == 'Cigna Dental PPO'
    assert made['drafts'][0]['changes']['rate_ee'] == '479.37'  # 489.15 × 0.98
    row = Activity.objects.get(pk=made['activity_id'])
    assert row.summary == 'Priced 2 plans (Cigna / UHC): 2% bundled (Dental)' and len(row.changes) == 2
    # the dental quote the bundle needs cannot move line alone (F59, slice 8)
    moved = api.post(
        f'/api/deals/{deal.id}/plans/move-line/', {'plan_ids': [dental.id], 'line': 'vision'}, format='json'
    )
    assert moved.status_code == 409 and 'required by the bundling discount' in moved.json()['detail']


def test_F78_a_quote_whose_rates_include_the_bundle_takes_no_bundled_version(api, deal, line):
    uhc = line['uhc']
    patched = api.patch(f'/api/plans/{uhc.id}/', {'bundling': 'included'}, format='json')
    assert patched.status_code == 200 and patched.json()['bundling'] == 'included'
    assert api.patch(f'/api/plans/{uhc.id}/', {'bundling': 'maybe'}, format='json').status_code == 400
    body = {'plan_ids': [uhc.id], 'kind': 'bundle', 'parts': [{'line': 'vision', 'op': 'pct_off', 'value': 1}]}
    assert 'would discount them twice' in post(api, deal, body, 409)['detail']
    row = Activity.objects.filter(deal=deal).latest('id')
    assert row.changes == [{'t': f'plan:{uhc.id}', 'k': {'plan.bundling': ['', 'included']}}] and row.revertible
    assert api.post(f'/api/activity/{row.id}/revert/').status_code == 200
    assert Plan.objects.get(pk=uhc.id).bundling == ''


def test_F80_a_premium_holiday_keeps_the_rates_and_shows_the_net_after_its_credit(api, deal, line):
    a, cigna = line['a'], line['cigna']
    months = post(api, deal, {'plan_ids': [a.id], 'kind': 'holiday', 'credit': {'months': 1}}, code=201)
    current = shown(api, deal)[a.id]['premium']
    (draft,) = months['drafts']
    assert draft['changes'] == {} and draft['premium'] == current
    assert draft['credit'] == {
        'annual': current['monthly'],
        'months': 1,
        'net_annual': current['annual'] - current['monthly'],
        'change': {'delta': -current['monthly'], 'pct': -8.3},
        'reason': None,
    }
    assert shown(api, deal)[months['plans'][0]['id']]['credit'] == draft['credit']
    two = {'plan_ids': [cigna.id, line['uhc'].id], 'kind': 'holiday', 'credit': {'annual': 30000}}
    assert post(api, deal, two, 409)['detail'].startswith('A dollar credit belongs to one plan')
    huge = post(api, deal, {**two, 'plan_ids': [cigna.id], 'credit': {'annual': 10**7}, 'dry_run': True})
    assert huge['drafts'][0]['credit']['reason'] == 'credit_exceeds_year'


def test_F82_reprice_rebuilds_from_the_original_and_keeps_its_kind(api, user, deal, line):
    cigna = line['cigna']
    version = priced.price(user, deal, [cigna.id], FIVE_OFF).plans[0]
    services.update_plan(user, version.id, {'values': {'rate_es': '1', 'pcp_copay': '30'}})  # tweaks on the version
    url = f'/api/plans/{version.id}/priced/'
    dry = api.post(url, {'kind': 'concession', 'all': {'op': 'pct_off', 'value': 10}, 'dry_run': True}, format='json')
    assert dry.status_code == 200 and Plan.objects.get(pk=version.id).values['rate_es'] == '1'
    done = api.post(url, {'kind': 'concession', 'all': {'op': 'pct_off', 'value': 10}}, format='json').json()
    assert done['drafts'] == dry.json()['drafts']
    version.refresh_from_db()
    assert (version.values['rate_ee'], version.values['rate_es']) == ('440.24', '946.5')
    assert 'pcp_copay' not in version.values and version.name == 'HDHP 3000 — 10% concession'
    assert version.derived['label'] == '10% concession'
    holiday = api.post(url, {'kind': 'holiday', 'credit': {'months': 1}}, format='json')
    assert holiday.status_code == 409 and holiday.json()['detail'].startswith('A priced version keeps its kind')
    plain = api.post(f'/api/plans/{cigna.id}/priced/', FIVE_OFF, format='json')
    assert plain.status_code == 409 and plain.json()['detail'].startswith('Only a priced version can be re-priced')


def test_F82_Q3_reprice_write_path(user, deal, line):
    version = priced.price(user, deal, [line['cigna'].id], FIVE_OFF).plans[0]
    ten = {'kind': 'concession', 'all': {'op': 'pct_off', 'value': 10}}
    write_path_contract(
        user,
        version,
        call=lambda: priced.reprice(user, version.id, ten),
        read=lambda plan: (plan.values, plan.name, {k: v for k, v in plan.derived.items() if k != 'at'}),
        later=lambda: services.update_plan(user, version.id, {'values': {'rate_ee': '400'}}),
    )


def test_F82_a_typed_name_stays_through_a_reprice_and_a_gone_original_refuses(api, user, deal, line):
    cigna = line['cigna']
    version = priced.price(user, deal, [cigna.id], {**FIVE_OFF, 'name': 'Negotiated'}).plans[0]
    priced.reprice(user, version.id, {'kind': 'concession', 'all': {'op': 'pct_off', 'value': 6}})
    assert Plan.objects.get(pk=version.id).name == 'Negotiated'
    services.delete_plans(user, deal, [cigna.id])
    gone = api.post(f'/api/plans/{version.id}/priced/', FIVE_OFF, format='json')
    assert gone.status_code == 409 and gone.json()['detail'].startswith('The original this version was priced from')


def test_F83_x_removes_a_version_through_the_delete_door_and_undo_brings_it_back(api, user, deal, line):
    version = priced.price(user, deal, [line['cigna'].id], FIVE_OFF).plans[0]
    removed = api.post(f'/api/deals/{deal.id}/plans/delete/', {'plan_ids': [version.id]}, format='json').json()
    assert removed['removed'] == [version.id] and version.id not in shown(api, deal)
    assert api.post(f'/api/activity/{removed["activity_id"]}/revert/').status_code == 200
    assert version.id in shown(api, deal)


def test_F53_a_priced_version_never_becomes_current(api, user, deal, line):
    version = priced.price(user, deal, [line['cigna'].id], FIVE_OFF).plans[0]
    body = {'plan_ids': [version.id], 'role': 'current'}
    assert api.post(f'/api/deals/{deal.id}/plans/role/', body, format='json').status_code == 409


def test_F120_versions_of_several_plans_each_ride_behind_their_own(user, deal, line):
    cigna, uhc = line['cigna'], line['uhc']
    made = priced.price(user, deal, [uhc.id, cigna.id], FIVE_OFF).plans
    plans = line_state(deal, 'medical').plans
    ids = [plan.id for plan in plans]
    assert ids.index(made[0].id) == ids.index(uhc.id) + 1 and ids.index(made[1].id) == ids.index(cigna.id) + 1
    assert [p.id for p in order.layout(line_state(deal, 'medical').data)] == ids


@pytest.mark.django_db(transaction=True)
def test_F83_Q3_two_versions_racing_for_the_last_star_leave_the_cap(user):
    deal = make_deal(user)
    made = make_line(user, deal)
    for n in range(13):
        services.create_plan(user, deal, line='medical', role='alternate', carrier='Oscar', name=f'Q{n}')
    others = Plan.objects.filter(deal=deal, line='medical', carrier='Oscar').values_list('id', flat=True)
    services.star(user, deal, [*others, made['uhc'].id], True)  # 1 current + 14 starred: room for one more column
    real_line = priced.locks.line
    results = []

    def slow_line(*args):
        found = real_line(*args)
        time.sleep(0.15)  # hold the room check open while the other request arrives
        return found

    def race(plan_id):
        try:
            results.append(priced.price(user, deal, [plan_id], FIVE_OFF).plans[0].starred)
        finally:
            connection.close()

    with mock.patch.object(priced.locks, 'line', slow_line):
        threads = [threading.Thread(target=race, args=(made[key].id,)) for key in ('cigna', 'uhc')]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert sorted(results) == [False, True]
    held = Plan.objects.filter(deal=deal, line='medical', starred=True).count() + 1
    assert held == 16
