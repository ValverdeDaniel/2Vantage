"""The coverage intent door (plan.md §5.2, §7.6; B16–B20, B32; Q.9 row 11): the round trip through `set_intent` and
the payload, the confirmation that lapses, and `requested_lines` changing only through `set_intent`."""

import pytest

from conftest import make_deal
from deals import activity
from deals.models import Activity, Deal
from intake import services
from intake.models import CurrentCoverage, Intake

pytestmark = pytest.mark.django_db


def _intent(api, deal, **body):
    return api.post(f'/api/deals/{deal.id}/intake/intent/', body, format='json')


def _rows(api, deal):
    return {row['line']: row for row in api.get(f'/api/deals/{deal.id}/intake/').json()['intent']['rows']}


def test_B16_B17_intent_round_trip_through_the_door_and_the_payload(api, deal):
    rows = _rows(api, deal)
    assert [line for line in rows] == ['medical', 'dental', 'vision']
    assert not any(row['answered'] for row in rows.values()) and rows['medical']['this_year'] == 'market'

    body = _intent(api, deal, lines=['medical', 'dental', 'vision'], has_today=True).json()
    assert body['requested_lines'] == ['medical', 'dental', 'vision'] and body['activity_id']
    _intent(api, deal, line='dental', this_year='keep')
    answer = _intent(api, deal, line='vision', this_year='off')
    assert answer.json()['requested_lines'] == ['medical']

    rows = _rows(api, deal)
    assert {line: row['this_year'] for line, row in rows.items()} == {
        'medical': 'market',
        'dental': 'keep',
        'vision': 'off',
    }
    assert rows['dental']['this_year_label'] == 'Keep as-is' and rows['dental']['state'] == 'presented'
    assert all(row['answered'] and row['in_force'] for row in rows.values())
    assert Deal.objects.get(pk=deal.pk).requested_lines == ['medical']

    _intent(api, deal, line='dental', this_year='market')  # and back
    assert Deal.objects.get(pk=deal.pk).requested_lines == ['medical', 'dental']


def test_B17_a_control_left_out_keeps_each_lines_own_answer(api, deal):
    _intent(api, deal, line='medical', has_today=True)
    _intent(api, deal, line='dental', has_today=False)
    _intent(api, deal, lines=['medical', 'dental'], this_year='keep')
    rows = _rows(api, deal)
    assert rows['medical']['in_force'] and not rows['dental']['in_force']
    assert rows['dental']['this_year_label'] == 'Present it'  # a gap line kept: presented, not marketed


def test_B17_bulk_is_all_or_nothing(api, deal):
    before = Activity.objects.count()
    answer = _intent(api, deal, lines=['medical', 'teeth'], has_today=True)
    assert answer.status_code == 400 and 'teeth' in answer.json()['lines'][0]
    assert not CurrentCoverage.objects.filter(deal=deal).exists() and Activity.objects.count() == before
    assert _intent(api, deal, lines=[], has_today=True).status_code == 400
    assert _intent(api, deal, line='medical', this_year='later').status_code == 400
    assert _intent(api, deal, line='medical').status_code == 400  # no control


def test_B17_remove_takes_the_line_out_of_the_conversation(api, deal):
    _intent(api, deal, line='dental', has_today=True)
    CurrentCoverage.objects.create(deal=deal, line='dental', carrier='Second row', sort_order=9)
    assert _intent(api, deal, lines=['dental'], remove=True).status_code == 400  # one line at a time
    assert _intent(api, deal, line='dental', remove=True).status_code == 200
    assert 'dental' not in _rows(api, deal) and not CurrentCoverage.objects.filter(deal=deal).exists()
    assert Deal.objects.get(pk=deal.pk).requested_lines == ['medical', 'vision']


def test_B32_the_chips_shop_a_line_without_answering_it(api, user):
    deal = make_deal(user, requested_lines=())
    _intent(api, deal, lines=['dental', 'medical'], shop=True)
    assert Deal.objects.get(pk=deal.pk).requested_lines == ['medical', 'dental']
    assert not CurrentCoverage.objects.filter(deal=deal).exists()
    _intent(api, deal, line='medical', has_today=True)
    _intent(api, deal, line='medical', this_year='off')
    _intent(api, deal, line='medical', shop=True)  # shopping again puts it back on the proposal
    assert _rows(api, deal)['medical']['this_year'] == 'market'
    _intent(api, deal, line='medical', shop=False)
    assert _rows(api, deal)['medical']['this_year'] == 'keep'
    assert _intent(api, deal, line='medical', shop=True, this_year='keep').status_code == 400


def test_B20_confirmation_lapses_on_a_change_and_holds_again_when_it_is_undone(api, deal, user):
    _intent(api, deal, lines=['medical', 'dental', 'vision'], has_today=True)
    card = api.post(f'/api/deals/{deal.id}/intake/intent/confirm/').json()['intent']
    assert card['state'] == 'done' and card['confirmed_by'] == 'Dana'
    again = api.post(f'/api/deals/{deal.id}/intake/intent/confirm/').json()
    assert again['activity_id'] is None  # confirming unchanged decisions writes nothing

    coverage_id = CurrentCoverage.objects.get(deal=deal, line='medical').id
    api.patch(f'/api/coverage/{coverage_id}/', {'carrier': 'Aetna', 'notes': 'Renews in March'}, format='json')
    assert _card(api, deal)['state'] == 'done'  # carrier and notes are not decisions

    _intent(api, deal, line='dental', this_year='keep')
    stale = _card(api, deal)
    assert stale['state'] == 'stale' and stale['stale'] and not stale['confirmed']
    _intent(api, deal, line='dental', this_year='market')
    assert _card(api, deal)['state'] == 'done'  # the same decisions again: confirmed again

    api.patch(f'/api/coverage/{coverage_id}/', {'rate_guarantee_through': '2027-06-30'}, format='json')
    assert _card(api, deal)['state'] == 'stale'
    reopened = api.post(f'/api/deals/{deal.id}/intake/intent/reopen/').json()['intent']
    assert reopened['state'] == 'open' and reopened['confirmed_at'] is None


def _card(api, deal):
    return api.get(f'/api/deals/{deal.id}/intake/').json()['intent']


def test_B20_reopen_with_nothing_confirmed_creates_nothing(api, deal):
    answer = api.post(f'/api/deals/{deal.id}/intake/intent/reopen/')
    assert answer.status_code == 200 and answer.json()['activity_id'] is None
    assert not Intake.objects.filter(deal=deal).exists()


def test_B17_requested_lines_change_only_through_set_intent(api, deal):
    patched = api.patch(f'/api/deals/{deal.id}/', {'requested_lines': ['medical']}, format='json')
    assert patched.status_code == 400 and 'intake/intent/' in patched.json()['requested_lines'][0]
    created = api.post('/api/clients/', {'name': 'X', 'requested_lines': ['medical']}, format='json')
    assert created.status_code == 400 and 'intake/intent/' in created.json()['requested_lines'][0]
    assert Deal.objects.get(pk=deal.pk).requested_lines == ['medical', 'dental', 'vision']
    services.set_intent(None, deal.id, line='vision', shop=False)
    assert Deal.objects.get(pk=deal.pk).requested_lines == ['medical', 'dental']


def test_B17_one_activity_row_holds_the_gesture_and_revert_puts_it_back(user, deal):
    services.set_intent(user, deal.id, line='medical', has_today=True)
    changed = services.set_intent(user, deal.id, line='medical', this_year='off')
    row = changed.activity
    targets = {entry['t'] for entry in row.changes}
    assert targets == {f'deal:{deal.id}', f'coverage:{CurrentCoverage.objects.get(deal=deal).id}'}
    activity.revert(row.id, user)
    assert Deal.objects.get(pk=deal.pk).requested_lines == ['medical', 'dental', 'vision']
    assert CurrentCoverage.objects.get(deal=deal).on_proposal is True


def test_B17_revert_of_a_remove_rebuilds_the_row_and_the_line(user, deal):
    services.set_intent(user, deal.id, line='dental', has_today=True)
    services.update_coverage(user, CurrentCoverage.objects.get(deal=deal).id, {'carrier': 'Guardian'})
    row = services.set_intent(user, deal.id, line='dental', remove=True).activity
    activity.revert(row.id, user)
    rebuilt = CurrentCoverage.objects.get(deal=deal)
    assert rebuilt.line == 'dental' and rebuilt.carrier == 'Guardian' and rebuilt.in_force
    assert 'dental' in Deal.objects.get(pk=deal.pk).requested_lines


def test_B19_revert_of_an_answer_that_created_a_row_is_refused_after_a_later_edit(user, deal):
    first = services.set_intent(user, deal.id, line='std', has_today=False).activity
    services.update_coverage(user, CurrentCoverage.objects.get(deal=deal).id, {'notes': 'Ask about STD'})
    with pytest.raises(activity.Refused):
        activity.revert(first.id, user)
    assert CurrentCoverage.objects.filter(deal=deal, line='std').exists()
