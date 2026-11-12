"""Moving plans to another line in place (plan.md §5.4, §7.8; F59; slice 8 "done when": a plan moved to dental keeps
its id)."""

import pytest

from conftest import write_path_contract
from deals import activity
from deals.models import Activity
from quotes import services
from quotes.models import Plan

pytestmark = pytest.mark.django_db

MEDICAL = {'deductible_single': '3000', 'network': 'Open Access', 'rate_ee': '489.15', 'rate_fam': '1508.92'}


@pytest.fixture
def line(user, deal):
    a = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='HMO 1500')
    b = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='PPO 2000')
    renewal = services.create_renewal(user, a.id)
    quote = services.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='MetLife',
        name='Dental PPO',
        replaces_ids=[a.id],
        values=MEDICAL,
    )
    dental = services.create_plan(user, deal, line='dental', role='current', carrier='Delta', name='PPO 50')
    return {'a': a, 'b': b, 'renewal': renewal, 'quote': quote, 'dental': dental}


def fresh(plan):
    return Plan.objects.get(pk=plan.id)


def move(api, deal, plans, to):
    return api.post(
        f'/api/deals/{deal.id}/plans/move-line/', {'plan_ids': [p.id for p in plans], 'line': to}, format='json'
    )


def test_F59_done_when_a_plan_moved_to_dental_keeps_its_id_and_what_dental_reads(api, user, deal, line):
    quote = line['quote']
    services.star(user, deal, [quote.id], True)
    services.set_enrollment(user, deal, 'medical', plans=[{'id': quote.id, 'enrollment': {'EE': 4}}])
    services.create_package(user, deal, 'medical', 'Switch', [quote.id])
    response = move(api, deal, [quote], 'dental')
    assert response.status_code == 200
    body = response.json()
    assert [plan['id'] for plan in body['plans']] == [quote.id] and body['line'] == 'dental'
    moved = fresh(quote)
    assert moved.id == quote.id and moved.line == 'dental'
    assert moved.values == {'network': 'Open Access', 'rate_ee': '489.15', 'rate_fam': '1508.92'}  # dental's fields
    assert moved.sources['rate_ee']['origin'] == 'typed'  # sources of the kept values stay
    assert (moved.starred, moved.recommended, moved.enrollment) == (False, False, {})
    assert list(moved.replaces.all()) == [] and list(moved.packages.all()) == []
    dental_ids = [plan['id'] for plan in api.get(f'/api/deals/{deal.id}/plans/?line=dental').json()['plans']]
    assert dental_ids == [line['dental'].id, quote.id]
    row = Activity.objects.get(pk=body['activity_id'])
    assert row.action == 'moved' and row.summary == 'Moved MetLife Dental PPO to Dental'
    assert row.changes[0]['k']['deductible_single'] == ['3000', None]  # a dropped value is kept in Activity


def test_F59_Q3_move_write_path_and_revert_puts_back_what_it_lost(user, deal, line):
    quote = line['quote']
    services.star(user, deal, [quote.id], True)
    package = services.create_package(user, deal, 'medical', 'Switch', [quote.id])

    def state(plan):
        return (
            plan.line,
            plan.values,
            plan.starred,
            sorted(plan.replaces.values_list('id', flat=True)),
            sorted(plan.packages.values_list('id', flat=True)),
        )

    before = state(fresh(quote))
    write_path_contract(
        user,
        quote,
        call=lambda: services.move_line(user, deal, [quote.id], 'dental'),
        read=state,
        later=lambda: services.star(user, deal, [quote.id], True),
    )
    assert before[4] == [package.id]


def test_F59_a_current_plan_moves_to_the_end_of_the_current_plans_and_leaves_its_links_behind(user, deal, line):
    a, renewal, quote = line['a'], line['renewal'], line['quote']
    changed, row = services.move_line(user, deal, [a.id], 'dental')
    assert {plan.id for plan in changed} == {a.id, renewal.id, quote.id}
    assert fresh(a).role == 'current' and fresh(a).line == 'dental'
    assert (fresh(renewal).role, fresh(renewal).renews_id) == ('alternate', None)
    assert list(fresh(quote).replaces.all()) == []
    dental = Plan.objects.filter(deal=deal, line='dental', role='current').order_by('sort_order', 'id')
    assert [plan.id for plan in dental] == [line['dental'].id, a.id]
    activity.revert(row.id, user)
    assert fresh(a).line == 'medical' and (fresh(renewal).role, fresh(renewal).renews_id) == ('renewal', a.id)
    assert [p.id for p in fresh(quote).replaces.all()] == [a.id]


def test_F59_a_moved_renewal_arrives_as_an_alternate(user, deal, line):
    services.move_line(user, deal, [line['renewal'].id], 'dental')
    moved = fresh(line['renewal'])
    assert (moved.line, moved.role, moved.renews_id) == ('dental', 'alternate', None)


def test_F59_refusals_are_in_words(api, user, deal, line):
    quote = line['quote']
    copy = services.copy_plan(user, quote.id)
    refused = move(api, deal, [copy], 'dental')
    assert refused.status_code == 409
    assert (
        refused.json()['detail']
        == "MetLife Dental PPO — copy is a priced version or a copy: it stays on its original's line."
    )
    assert move(api, deal, [quote], 'dental').json()['detail'] == (
        'MetLife Dental PPO has priced versions or copies, priced on its Medical rates. Remove them before moving it.'
    )
    services.set_sold(user, line['b'].id, True)
    assert move(api, deal, [line['b']], 'dental').json()['detail'] == (
        'Aetna PPO 2000 is sold: its line was booked with the sale. Undo the sale before moving it.'
    )
    Plan.objects.filter(pk=copy.id).update(derived={'kind': 'bundle', 'requires': [line['renewal'].id]})
    assert move(api, deal, [line['renewal']], 'dental').json()['detail'] == (
        'Aetna HMO 1500 is required by the bundling discount on MetLife Dental PPO — copy. Remove that discount before '
        'moving it.'
    )
    assert fresh(line['renewal']).line == 'medical'  # all or nothing


def test_F59_the_same_move_twice_writes_once_and_bad_input_answers_400(api, deal, line):
    assert move(api, deal, [line['quote']], 'dental').json()['activity_id']
    again = move(api, deal, [line['quote']], 'dental').json()
    assert again == {'line': 'dental', 'plans': [], 'activity_id': None}
    assert move(api, deal, [line['quote']], 'boats').status_code == 400
    assert api.post(f'/api/deals/{deal.id}/plans/move-line/', {'line': 'dental'}, format='json').status_code == 400


def test_F59_revert_of_a_move_is_refused_once_a_package_it_left_is_deleted(user, deal, line):
    package = services.create_package(user, deal, 'medical', 'Switch', [line['quote'].id])
    _, row = services.move_line(user, deal, [line['quote'].id], 'dental')
    services.delete_package(user, package.id)
    with pytest.raises(activity.Refused) as refused:
        activity.revert(row.id, user)
    assert refused.value.sentence == (
        'A package one of these plans was in has been deleted, so this change cannot be reverted.'
    )
    assert fresh(line['quote']).line == 'dental'
