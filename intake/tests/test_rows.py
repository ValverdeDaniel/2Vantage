"""Current coverage rows through their one service (plan.md §6.5, §7.6; B14, B19; OQ15) and intake's provider slots
with their defaults (O.1; Q.9 row 11)."""

import pytest

from deals.models import Activity
from intake import providers
from intake.models import CurrentCoverage, Intake

pytestmark = pytest.mark.django_db


def _add(api, deal, **body):
    return api.post(f'/api/deals/{deal.id}/coverage/', body, format='json')


def _edit(api, row_id, **body):
    return api.patch(f'/api/coverage/{row_id}/', body, format='json')


def test_B14_add_edit_and_remove_a_coverage_row(api, deal):
    created = _add(api, deal, line='medical', carrier='Aetna', funding='level_funded', renewal_date='1/1/2027')
    assert created.status_code == 201
    row = created.json()
    assert row['carrier'] == 'Aetna' and row['renewal_date'] == '2027-01-01' and row['from_plans'] is None
    edited = _edit(api, row['id'], commission='5%', commission_source='carrier').json()
    assert edited['commission'] == {'type': 'pct', 'value': '5'} and edited['commission_label'] == '5%'
    flat = _edit(api, row['id'], commission={'type': 'flat', 'value': '12,345.67'}).json()
    assert flat['commission_label'] == '$12,345.67/yr'
    assert api.get(f'/api/deals/{deal.id}/coverage/').json()[0]['id'] == row['id']
    assert api.delete(f'/api/coverage/{row["id"]}/').status_code == 204
    assert not CurrentCoverage.objects.filter(deal=deal).exists()


def test_B14_refusals_name_every_bad_field(api, deal):
    bad = _add(api, deal, line='teeth', funding='cash', renewal_date='soonish', commission='120', in_force='yes')
    assert bad.status_code == 400
    assert set(bad.json()) == {'line', 'funding', 'renewal_date', 'commission', 'in_force'}
    assert bad.json()['commission'] == ['Must be between 0 and 100']
    assert _add(api, deal, carrier='Aetna').status_code == 400  # a row names its line
    assert not CurrentCoverage.objects.filter(deal=deal).exists()


def test_B14_an_unchanged_edit_writes_nothing(api, deal):
    row = _add(api, deal, line='dental', carrier='Guardian').json()
    rows = Activity.objects.count()
    _edit(api, row['id'], carrier=' Guardian ')
    assert Activity.objects.count() == rows


def test_B14_edits_in_a_burst_share_one_activity_row(api, deal):
    row = _add(api, deal, line='dental').json()
    _edit(api, row['id'], carrier='Guardian')
    _edit(api, row['id'], notes='Rate guarantee to 2028')
    latest = Activity.objects.filter(deal=deal).order_by('-id').first()
    assert latest.summary == 'Edited 2 coverage values' and latest.count == 2


def test_B14_carrier_and_funding_come_from_the_current_plans_once_there_are_some(api, deal, monkeypatch):
    row = _add(api, deal, line='medical', carrier='Old carrier').json()
    plans = {'medical': {'presented': 3, 'sold': False, 'current': {'carrier': 'Aetna', 'funding': 'fully_insured'}}}
    monkeypatch.setitem(providers._slots, 'quote_lines', lambda deal_id: plans)
    refused = _edit(api, row['id'], carrier='Cigna')
    assert refused.status_code == 400
    assert refused.json() == {'carrier': ['Edit carrier and funding on the current plans in the Advisor.']}
    dated = _edit(api, row['id'], renewal_date='2027-01-01')
    assert dated.status_code == 200 and dated.json()['from_plans'] == plans['medical']['current']
    payload = api.get(f'/api/deals/{deal.id}/intake/').json()
    assert payload['intent']['rows'][0]['from_plans'] == {'carrier': 'Aetna', 'funding': 'fully_insured'}


def test_O1_provider_defaults_answer_before_the_right_apps_fill_them(deal):
    assert providers.DEFAULTS['quote_lines'](deal.id) == {}
    assert providers.DEFAULTS['questionnaire_items'](deal.id) == {}
    no_census = {'has_roster': False, 'employees': 0, 'errors': 0, 'ok': False}
    assert providers.DEFAULTS['census_state'](deal.id) == no_census
    headcount = providers.DEFAULTS['headcount']
    assert headcount(deal.id) == {'count': None, 'source': '', 'estimate': False}
    Intake.objects.create(deal=deal, answers={'employee_count': '42', 'total_employees': '50'})
    assert headcount(deal.id) == {'count': 42, 'source': 'intake.employee_count', 'estimate': True}
    Intake.objects.filter(deal=deal).update(answers={'enrolled_count': '30', 'employee_count': '42'})
    assert headcount(deal.id) == {'count': 30, 'source': 'intake.enrolled_count', 'estimate': False}
    with pytest.raises(KeyError):
        providers.fill('premium', lambda deal_id: None)


def test_O1_a_get_creates_no_intake_row(api, deal):
    body = api.get(f'/api/deals/{deal.id}/intake/').json()
    assert body['answers'] == {} and body['coverage'] == [] and body['intent']['state'] == 'open'
    assert 'waive_reason' in body['hidden']
    assert not Intake.objects.filter(deal=deal).exists()
