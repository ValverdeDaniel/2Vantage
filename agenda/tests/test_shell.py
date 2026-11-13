"""The deal shell's one read, `GET deals/{id}/journey/` (plan.md §7.15, §8.4; A21, A23, A24, M39, M40, H9; Q.9 row 61):
the stepper's two modules with the current dot on the milestone owning the next step, never a skipped step; the badges
the old sidebar drew (Intake's count is the Review board's Missing); the readiness meters; the ready chip; a fixed
number of queries. Factory deals and GD3 (quote-first, built per test); synthetic only."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from agenda import selectors, services
from conftest import make_deal
from deals.services import mark_lost, set_owner
from quotes import services as quote_services

pytestmark = pytest.mark.django_db


def journey(api, deal):
    response = api.get(f'/api/deals/{deal.id}/journey/')
    assert response.status_code == 200
    return response.json()


def states(payload):
    return {step['key']: step['state'] for module in payload['journey']['modules'] for step in module['steps']}


def plan(user, deal, role='alternate', **values):
    return quote_services.create_plan(
        user, deal, line='medical', role=role, carrier='Example Health', name='Example PPO', values=values
    )


def test_A24_M39_two_modules_and_the_current_dot_owns_the_next_step(api, user, deal):
    payload = journey(api, deal)
    modules = payload['journey']['modules']
    assert [(module['key'], module['label']) for module in modules] == [
        ('get_to_market', 'Get to Market'),
        ('quote_to_close', 'Quote to Close'),
    ]
    assert payload['next_step']['key'] == selectors.deal_agenda(deal, user)['next_step']['key'] == 'complete_intake'
    assert [key for key, state in states(payload).items() if state == 'current'] == ['intake_ready']
    assert {step['tab'] for module in modules for step in module['steps']} <= {
        'intake', 'census', 'advisor', 'proposal', 'commission'
    }  # fmt: skip
    assert payload['journey']['complete'] is False and payload['progress']['done'] == 0
    assert payload['ready'] == 'blocked'


def test_M39_a_held_lead_step_moves_the_dot_with_the_next_step(api, user, deal):
    agenda = selectors.deal_agenda(deal, user)
    for row in agenda['rows']:
        if row['kind'] == 'step' and row['track'] == 'intake' and row['can']['later']:
            services.set_later(user, deal.id, row['key'], '2099-01-01')
    payload = journey(api, deal)
    owner = payload['next_step']['key']
    assert payload['next_step'] == {**payload['next_step'], **selectors.deal_agenda(deal, user)['next_step']}
    current = [key for key, state in states(payload).items() if state == 'current']
    assert len(current) <= 1 and owner


def test_M40_I69_GD3_quote_first_never_shows_a_skipped_step_and_progress_counts_what_applies(api, user, quote_first):
    deal = quote_first.built.deal
    payload = journey(api, deal)
    assert set(states(payload).values()) <= {'done', 'current', 'todo'}
    assert states(payload)['quotes_in'] == 'done' and states(payload)['intake_ready'] == 'todo'
    agenda = selectors.deal_agenda(deal, user)
    assert payload['progress'] == agenda['progress']
    assert payload['progress']['total'] < sum(len(module['steps']) for module in payload['journey']['modules'])


def test_A21_L13_the_intake_badge_is_the_review_boards_missing_and_review_wears_three_tones(api, user, deal):
    payload = journey(api, deal)
    board = api.get(f'/api/deals/{deal.id}/review/board/').json()
    badges = payload['badges']
    assert badges['intake'] == board['sections']['intake']['missing'] > 0
    assert set(badges['review']) == {'review', 'waiting', 'missing', 'questions'}
    assert badges['review']['waiting'] == board['counts']['waiting']
    assert badges['review']['review'] == board['counts']['to_review']
    assert badges['returned'] == {'intake': False, 'census': False, 'questionnaire': False}


def test_A21_A23_the_proposal_badge_and_meter_count_required_values_on_proposed_plans(api, user, deal):
    plan(user, deal, role='current', rate_ee='400')  # a current plan never counts (old `proposal_metrics`)
    empty = journey(api, deal)
    assert empty['badges']['proposal'] == 0 and empty['meters']['proposal'] == 100
    plan(user, deal, rate_ee='512.40')
    payload = journey(api, deal)
    assert payload['badges']['proposal'] > 0
    assert 0 < payload['meters']['proposal'] < 100
    assert set(payload['meters']) == {'intake', 'proposal', 'census'}


def test_H9_commission_wears_a_1_while_no_primary_producer_is_set(api, user, deal):
    assert journey(api, deal)['badges']['commission'] == 0  # the owner stands as the primary (H10)
    set_owner(user, None, deal_id=deal.id)
    set_owner(user, None, client_id=deal.client_id)
    assert journey(api, deal)['badges']['commission'] == 1


def test_I66_a_lost_deal_keeps_its_meters_and_has_no_current_dot(api, user, deal):
    mark_lost(user, deal.id, 'Stayed with their broker')
    payload = journey(api, deal)
    assert payload['next_step']['state'] == 'lost' and payload['waiting'] is None
    assert 'current' not in states(payload).values()
    assert payload['meters'] and payload['badges']


def test_Q3_4_the_journey_reads_in_the_same_queries_whatever_the_deal_holds(api, user):
    small, big = make_deal(user, name='Small Shell (synthetic)'), make_deal(user, name='Big Shell (synthetic)')
    for n in range(6):
        plan(user, big, rate_ee=str(400 + n))
        services.add_task(user, big.id, title=f'Task {n}', due='2099-01-01')
    plan(user, small, rate_ee='400')

    def queries(deal):
        with CaptureQueriesContext(connection) as found:
            journey(api, deal)
        return len(found.captured_queries)

    assert queries(small) == queries(big)


def test_Q3_journey_ids_past_bigint_or_unknown_are_404(api):
    assert api.get(f'/api/deals/{2**63}/journey/').status_code == 404
    assert api.get('/api/deals/999999/journey/').status_code == 404
