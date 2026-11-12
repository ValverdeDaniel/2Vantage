"""`GET deals/{id}/plans/stop-loss/` and the stop-loss saved settings (plan.md §7.8, §8.14; F29, F98–F106; Q.9 row 36:
the basis names its source, the what-if is never saved, lasers never in Activity)."""

import pytest

from conftest import make_deal
from deals.models import Activity
from quotes import services

pytestmark = pytest.mark.django_db

CONTRACT = {
    'sl_spec_deductible': '50000',
    'sl_spec_rate': '85.20',
    'sl_agg_rate': '12.10',
    'sl_agg_factor': '850',
    'sl_agg_corridor': '1.25',
    'sl_lasers': 'A.B. 125000, C.D. 90000',
}


def _deal(user, lines=('medical', 'stop_loss')):
    return make_deal(user, name='Stop-loss shop (synthetic)', requested_lines=list(lines))


def _plan(user, deal, role='current', values=CONTRACT, line='stop_loss', **kwargs):
    return services.create_plan(user, deal, line=line, role=role, carrier='Symetra', name=f'{role} SL', values=values,
                                **kwargs)  # fmt: skip


def _get(api, deal, **params):
    response = api.get(f'/api/deals/{deal.id}/plans/stop-loss/', params)
    assert response.status_code == 200, response.content
    return response.json()


def test_F98_with_no_enrolled_employees_the_basis_is_empty_and_nothing_annual_reads(api, user):
    deal = _deal(user)
    _plan(user, deal)
    body = _get(api, deal)
    assert body['basis'] == {'lives': None, 'months': 12, 'source': None, 'words': ''}
    figures = body['columns'][0]['figures']
    assert figures['annual_premium'] is None and figures['max_annual_liability'] is None
    assert figures['premium_pepm'] == 97.3


def test_F98_lives_typed_on_the_contract_win_and_the_basis_says_so(api, user):
    deal = _deal(user)
    medical = _plan(user, deal, line='medical', values={'rate_ee': '500'})
    services.set_enrollment(user, deal, 'medical', plans=[{'id': medical.id, 'enrollment': {'EE': 30}}])
    body = _get(api, deal)
    assert body['columns'] == []  # no stop-loss plan yet: the board's empty state
    contract = _plan(user, deal)
    assert _get(api, deal)['basis'] == {'lives': 30, 'months': 12, 'source': 'medical',
                                        'words': 'From medical enrollment'}  # fmt: skip
    services.set_enrollment(user, deal, 'stop_loss', plans=[{'id': contract.id, 'enrollment': {'lives': 40}}])
    body = _get(api, deal)
    assert body['basis'] == {'lives': 40, 'months': 12, 'source': 'typed', 'words': 'Typed on the in-force contract'}
    assert body['columns'][0]['figures']['annual_premium'] == 46704  # 97.30 × 40 × 12


def test_F104_the_what_if_is_a_read_never_saved_and_never_in_activity(api, user):
    deal = _deal(user)
    contract = _plan(user, deal)
    services.set_enrollment(user, deal, 'stop_loss', plans=[{'id': contract.id, 'enrollment': {'lives': 40}}])
    before = Activity.objects.count()
    body = _get(api, deal, without=f'{contract.id}:1')
    column = body['columns'][0]
    assert column['what_if'] is True and column['figures']['laser_liability'] == 40000
    assert Activity.objects.count() == before
    assert _get(api, deal)['columns'][0]['figures']['laser_liability'] == 115000  # nothing kept


@pytest.mark.parametrize('bad', ['x', '12', '12:a', '12:0'])
def test_F104_a_malformed_what_if_answers_400(api, user, bad):
    deal = _deal(user)
    response = api.get(f'/api/deals/{deal.id}/plans/stop-loss/', {'without': bad})
    assert response.status_code == 400 and 'without' in response.json()


def test_F106_two_in_force_contracts_compare_nothing_and_refuse_the_workbook(api, user):
    deal = _deal(user)
    _plan(user, deal)
    _plan(user, deal, values={**CONTRACT, 'sl_spec_rate': '90'})
    _plan(user, deal, role='alternate', values=CONTRACT)
    body = _get(api, deal)
    assert body['current_id'] is None and len(body['currents']) == 2
    assert body['refusal'].startswith('This deal has 2 in-force stop-loss contracts')
    assert all(column['vs'] is None for column in body['columns'])


def test_F104_rule10_no_laser_reaches_activity_by_claimant(user):
    deal = _deal(user)
    plan = _plan(user, deal)
    services.update_plan(user, plan.id, {'values': {'sl_lasers': 'Z.Z. 150000'}})
    text = ' '.join(str(row.changes) + row.summary for row in Activity.objects.filter(deal=deal))
    assert 'Z.Z.' not in text and 'A.B.' not in text


def test_F29_stop_loss_settings_are_saved_cleaned_and_refused_in_words(api):
    response = api.post(
        '/api/saved-views/',
        {'name': 'Premium first', 'view': 'stop-loss', 'line': 'stop_loss', 'config': {'rank_by': 'annual_premium'}},
        format='json',
    )
    assert response.status_code == 201, response.content
    assert response.json()['config'] == {
        'rank_by': 'annual_premium',
        'annual_mode': False,
        'show_terms': True,
        'hide_unscored': False,
    }
    listed = api.get('/api/saved-views/', {'view': 'stop-loss', 'line': 'stop_loss'}).json()
    assert [row['name'] for row in listed] == ['Premium first']
    assert api.get('/api/saved-views/', {'view': 'quotes', 'line': 'stop_loss'}).json() == []
    bad = api.post(
        '/api/saved-views/',
        {'name': 'Bad', 'view': 'stop-loss', 'config': {'rank_by': 'closeness', 'find': 'UHC'}},
        format='json',
    )
    assert bad.status_code == 400
    assert set(bad.json()['config']) == {'rank_by', 'find'}


def test_F102_meta_serves_the_rank_keys_terms_and_defaults(api):
    found = api.get('/api/meta/').json()['stop_loss']
    assert found['rank_keys'][0] == {'key': 'max_annual_liability', 'label': 'Maximum annual liability'}
    assert found['settings']['show_terms'] is True
    assert {'key': 'tpa_name', 'label': 'TPA'} in found['terms']
