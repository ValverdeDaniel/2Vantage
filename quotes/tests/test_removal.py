"""Soft delete, Clear line and Restore by Revert (plan.md §5.4, §7.8; F60, F61, H.6, O.3.7; slice 8 "done when")."""

import pytest

from conftest import make_deal, write_path_contract
from contract_helpers import assert_write_path
from deals import activity
from quotes import services
from quotes.models import Plan

pytestmark = pytest.mark.django_db


class AllPlans:
    """A plan seen through `all_objects`, for the write-path contract: the default manager hides a removed plan."""

    objects = Plan.all_objects
    _meta = Plan._meta

    def __init__(self, plan):
        self.pk = plan.pk


@pytest.fixture
def line(user, deal):
    a = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='HMO 1500')
    b = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='PPO 2000')
    renewal = services.create_renewal(user, a.id)
    quote = services.create_plan(
        user, deal, line='medical', role='alternate', carrier='Cigna', name='Open Access', replaces_ids=[a.id, b.id]
    )
    other = services.create_plan(
        user, deal, line='medical', role='alternate', carrier='UHC', name='Choice', replaces_ids=[b.id]
    )
    return {'a': a, 'b': b, 'renewal': renewal, 'quote': quote, 'other': other}


def fresh(plan):
    return Plan.all_objects.get(pk=plan.id)


def links(plan):
    plan = fresh(plan)
    return (plan.role, plan.renews_id, sorted(plan.replaces.values_list('id', flat=True)))


def delete(api, deal, plans):
    return api.post(f'/api/deals/{deal.id}/plans/delete/', {'plan_ids': [p.id for p in plans]}, format='json')


def test_F60_done_when_deleting_a_current_plan_turns_its_renewal_into_an_alternate_and_revert_restores_both(
    api, deal, line
):
    a, renewal, quote = line['a'], line['renewal'], line['quote']
    body = delete(api, deal, [a]).json()
    assert body['removed'] == [a.id] and body['kept'] == [] and body['note'] == ''
    assert {plan['id'] for plan in body['plans']} == {renewal.id, quote.id}  # only what changed
    assert fresh(a).removed_at is not None and not Plan.objects.filter(pk=a.id).exists()
    assert links(renewal) == ('alternate', None, [])
    assert links(quote) == ('alternate', None, [line['b'].id])  # it leaves every `replaces` list
    row = activity.Activity.objects.get(pk=body['activity_id'])
    assert row.action == 'removed' and row.summary == 'Removed Aetna HMO 1500'
    assert api.post(f'/api/activity/{row.id}/revert/').status_code == 200
    assert fresh(a).removed_at is None
    assert links(renewal) == ('renewal', a.id, [])
    assert links(quote) == ('alternate', None, sorted([a.id, line['b'].id]))


def test_F60_Q3_delete_write_path(user, deal, line):
    renewal = line['renewal']
    write_path_contract(
        user,
        renewal,
        call=lambda: services.delete_plans(user, deal, [line['a'].id]),
        read=lambda p: (links(p), fresh(line['a']).removed_at is None),
        later=lambda: services.set_role(user, deal, [renewal.id], 'current'),
    )


def test_F61_Q3_clear_line_write_path(user, deal, line):
    """A removed plan's only key is its removal, and only a Revert writes it again: the contract stops at "already
    undone" (Restore's refusals are below)."""
    quote = AllPlans(line['quote'])
    row = assert_write_path(lambda: services.clear_line(user, deal, 'medical'), quote)
    assert {entry['t'] for entry in row.changes} == {
        f'plan:{p.id}' for p in (line['renewal'], line['quote'], line['other'])
    }
    activity.revert(row.id, user)
    assert fresh(line['quote']).removed_at is None
    with pytest.raises(activity.Refused) as refused:
        activity.revert(row.id, user)
    assert refused.value.sentence == activity.ALREADY_UNDONE


def test_F61_clear_line_keeps_current_and_sold_plans_and_names_the_sold(api, user, deal, line):
    services.set_sold(user, line['other'].id, True)
    body = api.post(f'/api/deals/{deal.id}/plans/clear/', {'line': 'medical'}, format='json').json()
    assert sorted(body['removed']) == sorted([line['renewal'].id, line['quote'].id])
    assert body['kept'] == [{'id': line['other'].id, 'name': 'UHC Choice', 'reason': 'sold'}]
    assert body['note'] == 'UHC Choice is sold, so it stays. Unmark sold first.'
    left = set(Plan.objects.filter(deal=deal, line='medical').values_list('id', flat=True))
    assert left == {line['a'].id, line['b'].id, line['other'].id}
    summary = activity.Activity.objects.get(pk=body['activity_id']).summary
    assert summary == 'Cleared Medical: removed 2 plans'


def test_F60_H6_a_sold_plan_cannot_be_deleted(api, user, deal, line):
    services.set_sold(user, line['quote'].id, True)
    refused = delete(api, deal, [line['quote']])
    assert refused.status_code == 409
    assert refused.json()['detail'] == 'Cigna Open Access is sold, so it stays. Unmark sold first.'
    assert Plan.objects.filter(pk=line['quote'].id).exists()
    body = delete(api, deal, [line['quote'], line['other']]).json()  # a batch removes the rest and names the sold one
    assert body['removed'] == [line['other'].id] and [k['id'] for k in body['kept']] == [line['quote'].id]


def test_F60_the_same_delete_twice_writes_once_and_a_stranger_plan_answers_400(api, user, deal, line):
    first = delete(api, deal, [line['other']]).json()
    again = delete(api, deal, [line['other']])
    assert again.status_code == 200 and again.json()['activity_id'] is None and again.json()['removed'] == []
    assert first['activity_id']
    stranger = services.create_plan(
        user, make_deal(user, name='Other Co.'), line='medical', role='current', carrier='Aetna', name='HMO'
    )
    assert delete(api, deal, [stranger]).status_code == 400
    assert api.post(f'/api/deals/{deal.id}/plans/delete/', {'plan_ids': ['x']}, format='json').status_code == 400
    assert api.post(f'/api/deals/{deal.id}/plans/delete/', {'plan_ids': []}, format='json').status_code == 400


def test_F60_removed_plans_leave_every_read_and_restore_brings_back_their_packages(api, user, deal, line):
    package = services.create_package(user, deal, 'medical', 'Switch', [line['quote'].id, line['other'].id])
    removal = services.delete_plans(user, deal, [line['quote'].id])
    comparison = api.get(f'/api/deals/{deal.id}/plans/?line=medical').json()
    assert line['quote'].id not in {plan['id'] for plan in comparison['plans']}
    assert {p['key']: p['plan_ids'] for p in comparison['packages']}[f'package:{package.id}'] == [line['other'].id]
    medical = next(row for row in api.get(f'/api/deals/{deal.id}/plans/lines/').json() if row['line'] == 'medical')
    assert (medical['renewal'], medical['alternate']) == (1, 1)
    listed = api.get(f'/api/deals/{deal.id}/plans/packages/?line=medical').json()
    assert listed[0]['plan_ids'] == [line['other'].id]
    activity.revert(removal.row.id, user)
    listed = api.get(f'/api/deals/{deal.id}/plans/packages/?line=medical').json()
    assert listed[0]['plan_ids'] == sorted([line['quote'].id, line['other'].id])


def test_F60_restore_refuses_in_words_when_a_rule_now_blocks_it(user, deal, line):
    a = line['a']
    removal = services.delete_plans(user, deal, [line['renewal'].id])
    services.create_renewal(user, a.id)  # a new renewal takes the plan's one place
    with pytest.raises(activity.Refused) as refused:
        activity.revert(removal.row.id, user)
    assert refused.value.sentence == 'This change cannot be reverted: Aetna HMO 1500 already has a renewal.'
    assert fresh(line['renewal']).removed_at is not None


def test_F60_restore_refuses_past_the_16_column_cap(user, deal, line):
    quotes = [
        services.create_plan(user, deal, line='medical', role='alternate', carrier='Kaiser', name=f'Q{n}')
        for n in range(13)
    ]
    services.star(user, deal, [line['quote'].id], True)
    removal = services.delete_plans(user, deal, [line['quote'].id])
    services.star(user, deal, [line['other'].id, *(q.id for q in quotes)], True)  # 2 current + 14 starred = 16
    with pytest.raises(activity.Refused) as refused:
        activity.revert(removal.row.id, user)
    assert refused.value.sentence == (
        'This change cannot be reverted: the Medical proposal would hold more than 16 plans.'
    )


def test_F60_an_edit_to_a_plan_removed_since_waits_for_its_restore(user, deal, line):
    edited, _ = services.update_plan(user, line['other'].id, {'values': {'rate_ee': '500'}})
    removal = services.delete_plans(user, deal, [line['other'].id])
    with pytest.raises(activity.Refused) as refused:
        activity.revert(edited.activity_id, user)
    assert 'has been removed' in refused.value.sentence
    activity.revert(removal.row.id, user)
    activity.revert(edited.activity_id, user)  # restored, the plan takes the edit's Revert again
    assert 'rate_ee' not in fresh(line['other']).values
