"""The request's writes (plan.md §6.10, §7.11; K9, K10, K20–K27, K111, K115; Q.9 row 44: five clicks, one Undo)."""

import pytest

from conftest import make_deal
from contract_helpers import later_clock
from deals import activity
from deals.models import Activity
from deals.services import mark_lost
from intake import services as intake_services
from rfp import services
from rfp.models import RfpRequest

pytestmark = pytest.mark.django_db


def rows(deal):
    return list(Activity.objects.filter(deal=deal, area='rfp').order_by('id'))


def test_K25_K115_five_chip_clicks_make_one_row_whose_undo_restores_the_first_state(user, deal):
    for change in (
        {'carriers': {'add': ['aetna']}},
        {'carriers': {'add': ['cigna']}},
        {'carriers': {'remove': ['aetna']}},
        {'funding': {'remove': ['level_funded']}},
        {'route': 'warner'},
    ):
        services.update(user, deal.id, change)
    row = RfpRequest.objects.get(deal=deal)
    assert (row.carriers, row.funding, row.route) == (['cigna'], ['fully_insured'], 'warner')
    written = rows(deal)
    assert len(written) == 1
    assert written[0].count == 5
    assert written[0].summary == 'Edited 5 RFP settings'
    assert written[0].changes[0]['k'] == {
        'carriers': [[], ['cigna']],
        'funding': [None, ['fully_insured']],
        'route': ['', 'warner'],
    }
    activity.revert(written[0].id, user)
    row.refresh_from_db()
    assert (row.carriers, row.funding, row.route) == ([], None, '')


def test_K115_an_unchanged_write_records_nothing(user, deal):
    services.update(user, deal.id, {'carriers': {'add': ['aetna']}, 'due_date': '2027-02-01'})
    before = rows(deal)
    stamp = RfpRequest.objects.get(deal=deal).updated_at
    again = services.update(user, deal.id, {'carriers': {'add': ['aetna']}, 'due_date': '2027-02-01', 'notes': ''})
    assert again == services.Updated({}, [], None)
    assert rows(deal) == before
    assert RfpRequest.objects.get(deal=deal).updated_at == stamp


def test_K10_an_edit_takes_its_own_cards_mark_off_and_undo_puts_it_back(user, deal):
    services.set_done(user, deal.id, 'request', True)
    services.set_done(user, deal.id, 'packet', True)
    with later_clock():
        written = services.update(user, deal.id, {'other_carriers': 'Oscar'})
    row = RfpRequest.objects.get(deal=deal)
    assert written.cleared == ['request']
    assert set(row.done) == {'packet'}  # another card's mark stays
    assert set(written.activity.changes[0]['k']) == {'other_carriers', 'done.request'}
    activity.revert(written.activity.id, user)
    row.refresh_from_db()
    assert (row.other_carriers, set(row.done)) == ('', {'packet', 'request'})


def test_K21_an_empty_funding_pick_is_kept_and_null_returns_to_the_default(user, deal, api):
    services.update(user, deal.id, {'funding': {'remove': ['fully_insured', 'level_funded']}})
    assert RfpRequest.objects.get(deal=deal).funding == []
    body = api.get(f'/api/deals/{deal.id}/rfp/').json()['request']
    assert (body['funding'], body['funding_default']) == ([], False)
    services.update(user, deal.id, {'funding': None})
    body = api.get(f'/api/deals/{deal.id}/rfp/').json()['request']
    assert (body['funding'], body['funding_default']) == (['fully_insured', 'level_funded'], True)


def test_K22_the_default_funding_follows_the_medical_coverage_row(user, deal, api):
    intake_services.create_coverage(user, deal.id, {'line': 'medical', 'carrier': 'Aetna', 'funding': 'self_funded'})
    assert api.get(f'/api/deals/{deal.id}/rfp/').json()['request']['funding'] == ['aso']
    services.update(user, deal.id, {'funding': {'add': ['level_funded']}})
    assert RfpRequest.objects.get(deal=deal).funding == ['level_funded', 'aso']


def test_K115_notes_never_enter_activity_by_value(user, deal):
    services.update(user, deal.id, {'notes': 'Match the current PPO design, please.'})
    services.update(user, deal.id, {'notes': 'Match the PPO and the HMO.'})
    written = rows(deal)
    assert len(written) == 1
    assert written[0].changes == [{'t': f'rfp:{deal.id}', 'k': ['notes']}]
    assert 'PPO' not in written[0].summary
    with pytest.raises(activity.Refused) as refused:
        activity.revert(written[0].id, user)
    assert refused.value.sentence == activity.KEYS_ONLY
    assert RfpRequest.objects.get(deal=deal).notes == 'Match the PPO and the HMO.'


def test_K111_a_lost_deal_keeps_its_edits(user, deal):
    mark_lost(user, deal.id, 'Went with another broker')
    written = services.update(user, deal.id, {'carriers': {'add': ['unum']}})
    assert written.changed == {'carriers': ['unum']}


def test_K9_a_mark_stores_who_and_when_and_never_merges(user, deal, api):
    first = services.set_done(user, deal.id, 'request', True)
    assert first.done['request']['by'] == user.id
    assert services.set_done(user, deal.id, 'request', True).activity is None  # marked already
    services.set_done(user, deal.id, 'request', False)
    services.set_done(user, deal.id, 'request', True)
    assert len(rows(deal)) == 3
    shown = api.get(f'/api/deals/{deal.id}/rfp/').json()['done']
    assert shown['request']['by'] == 'Dana'
    assert shown['request']['by_id'] == user.id


def test_K9_unknown_cards_and_non_booleans_are_refused(api, deal):
    url = f'/api/deals/{deal.id}/rfp/done/'
    assert api.post(url, {'card': 'lens', 'done': True}, format='json').status_code == 400
    assert api.post(url, {'card': 'request', 'done': 'y'}, format='json').status_code == 400
    assert not RfpRequest.objects.filter(deal=deal).exists()


def test_K10_a_coverage_edit_takes_the_coverage_cards_mark_off(user, deal):
    services.set_done(user, deal.id, 'coverage', True)
    services.set_done(user, deal.id, 'request', True)
    intake_services.set_intent(user, deal.id, line='vision', this_year='off')
    assert set(RfpRequest.objects.get(deal=deal).done) == {'request'}


def test_K27_a_bad_value_answers_400_by_field_and_writes_nothing(api, deal):
    response = api.patch(f'/api/deals/{deal.id}/rfp/', {'route': 'fax', 'notes': 'ok'}, format='json')
    assert response.status_code == 400
    assert set(response.json()) == {'route'}
    assert not RfpRequest.objects.filter(deal=deal).exists()


def test_K25_the_patch_answers_what_the_request_card_redraws(api, deal):
    response = api.patch(f'/api/deals/{deal.id}/rfp/', {'carriers': {'add': ['cigna']}}, format='json')
    assert response.status_code == 200
    body = response.json()
    assert body['changed'] == {'carriers': ['cigna']}
    assert body['request']['carriers'] == ['cigna']
    assert [chip['key'] for chip in body['carriers'] if chip['selected']] == ['cigna']
    assert body['activity_id'] is not None


def test_K6_a_get_makes_no_row(api, user):
    deal = make_deal(user)
    assert api.get(f'/api/deals/{deal.id}/rfp/').status_code == 200
    assert not RfpRequest.objects.filter(deal=deal).exists()
