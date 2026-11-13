"""The Work queue's feed (plan.md §7.15, §8.3; I70–I82, I86, I122–I125; Q.9 row 61): each live deal's row with its next
step (the Agenda tab's, I68), the client's status, type, due, owner and progress; open hand tasks and nudges; closed
deals only on request; the Prospects cards summed on the server. Factory deals; synthetic names only."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from agenda import selectors, services
from agenda.queue import rows as queue_rows
from conftest import make_client, make_deal
from deals import clock
from deals.services import mark_lost, set_archived, set_facts
from review import services as review_services

from .world import sent_ask

pytestmark = pytest.mark.django_db


def day(n):
    return (clock.today() + timedelta(days=n)).isoformat()


def feed(api, **params):
    response = api.get('/api/work-queue/', params)
    assert response.status_code == 200
    return response.json()


def row_of(payload, kind, deal_id):
    return next((row for row in payload['rows'] if row['kind'] == kind and row['deal_id'] == deal_id), None)


def test_I70_I68_a_deal_row_reads_the_agendas_next_step_with_its_deal_facts(api, user):
    effective = date.today() + timedelta(days=40)
    _client, deal = make_client(user, name='Queue Row Co. (synthetic)', effective_date=effective)
    payload = feed(api)
    row = row_of(payload, 'deal', deal.id)
    agenda = selectors.deal_agenda(deal, user)
    assert (row['key'], row['label'], row['link']) == (
        agenda['next_step']['key'],
        agenda['next_step']['label'],
        agenda['next_step']['link'],
    )
    assert row['client_name'] == 'Queue Row Co. (synthetic)' and row['client_status'] == 'prospect'
    assert row['type'] == 'new_business' and row['stage'] == 'intake' and row['category'] == 'pipeline'
    assert row['due'] == deal.effective_date.isoformat()
    assert row['due_in'] == (deal.effective_date - clock.today()).days
    assert row['owner_id'] == user.id and row['progress_pct'] == agenda['progress']['pct']
    assert row['home'] == f'/deals/{deal.id}' and row['finished'] is False and row['lost'] is False
    assert row['steps'] and all(step['link'].startswith(f'/deals/{deal.id}/') for step in row['steps'])
    assert payload['today'] == clock.today().isoformat()
    assert {'id': user.id, 'name': row['owner_name']} in payload['owners']
    assert 'Queue Row Co. (synthetic)' in payload['client_names']


def test_I123_an_existing_clients_deal_is_a_renewal_row(api, user):
    _client, deal = make_client(user, name='Renewing Co. (synthetic)', relationship='existing_client')
    row = row_of(feed(api), 'deal', deal.id)
    assert row['type'] == 'renewal' and row['client_status'] == 'existing_client'


def test_I71_open_tasks_list_on_lost_deals_too_and_done_ones_leave(api, user):
    deal = make_deal(user, name='Lost With Task Co. (synthetic)')
    kept = services.add_task(user, deal.id, title='Check back in six months', due=day(3), assigned_to=user.id)
    services.add_task(user, deal.id, title='Already called', due=day(1), done=True)
    mark_lost(user, deal.id, 'Went with another broker')
    payload = feed(api)
    assert row_of(payload, 'deal', deal.id) is None  # a lost deal's row waits for include=closed (I80)
    tasks = [row for row in payload['rows'] if row['kind'] == 'task' and row['deal_id'] == deal.id]
    assert [row['task_id'] for row in tasks] == [kept.id]
    task = tasks[0]
    assert task['category'] == 'task' and task['lost'] is True and task['owner_id'] == user.id
    assert task['link'] == f'/deals/{deal.id}/agenda?focus=task%3A{kept.id}'
    assert task['severity'] == 'warn' and task['due_in'] == 3


def test_I80_closed_deals_come_only_with_include_closed(api, user):
    lost = make_deal(user, name='Lost Co. (synthetic)')
    mark_lost(user, lost.id, '')
    assert row_of(feed(api), 'deal', lost.id) is None
    row = row_of(feed(api, include='closed'), 'deal', lost.id)
    assert row['lost'] is True and row['finished'] is True and row['severity'] == 'lost'
    assert row['progress_pct'] == 0 and row['steps'] == [] and row['label'].startswith('Deal lost')
    assert api.get('/api/work-queue/', {'include': 'everything'}).status_code == 400


def test_A18_an_archived_clients_deal_and_tasks_leave_the_feed(api, user):
    client, deal = make_client(user, name='Archived Co. (synthetic)')
    services.add_task(user, deal.id, title='Gone with the client', due=day(2))
    set_archived(user, client.id, True)
    payload = feed(api, include='closed')
    assert not [row for row in payload['rows'] if row['deal_id'] == deal.id]


def test_I75_a_held_next_step_carries_its_later_day(api, user):
    deal = make_deal(user, name='Held Co. (synthetic)')
    for step in selectors.deal_agenda(deal, user)['rows']:
        if step['kind'] == 'step' and step['can']['later']:
            services.set_later(user, deal.id, step['key'], day(4))
    row = row_of(feed(api), 'deal', deal.id)
    assert row['held'] == day(4)


def test_I86_I124_the_prospects_cards_count_open_prospects_and_sum_their_sizes(api, user):
    one = make_deal(user, name='Sized One (synthetic)')
    two = make_deal(user, name='Sized Two (synthetic)')
    make_deal(user, name='No Size Yet (synthetic)')
    _client, existing = make_client(user, name='Client Already (synthetic)', relationship='existing_client')
    set_facts(user, one.id, deal_size='250000')
    set_facts(user, two.id, deal_size='120000.50')
    set_facts(user, existing.id, deal_size='999999')
    lost = make_deal(user, name='Lost Sized (synthetic)')
    set_facts(user, lost.id, deal_size='50000')
    mark_lost(user, lost.id, '')
    card = feed(api)['cards']['prospects']
    assert card == {'count': 3, 'deal_size': '370000.50', 'unsized': 1}
    assert Decimal(card['deal_size']) == Decimal('250000') + Decimal('120000.50')


def test_L118_the_client_response_waits_on_us_until_handled():
    review = {'response': {'state': 'answered', 'at': '2026-11-10T15:00:00+00:00', 'name': 'Casey'},
              'questions': {'open': 1, 'oldest_at': None}, 'pending': {'total': 2}, 'in_progress': []}  # fmt: skip
    found = queue_rows.response(review)
    assert found['state'] == 'waiting' and (found['questions'], found['answers']) == (1, 2)
    assert found['who'] == 'Casey' and found['kind'] == 'submitted'
    handled = queue_rows.response({**review, 'questions': {'open': 0}, 'pending': {'total': 0}})
    assert handled['state'] == 'answered'
    typing = {'response': {'state': 'answering', 'at': 'x', 'name': 'Riley'}, 'in_progress': [{'link_id': 1}]}
    assert queue_rows.response(typing)['state'] == 'answering'
    assert queue_rows.response({'response': {'state': 'waiting', 'at': 'x', 'name': ''}}) is None
    assert queue_rows.response({}) is None


def test_I35_an_open_nudge_is_a_task_row_that_opens_the_links_settings(api, user):
    deal = make_deal(user, name='Nudge Co. (synthetic)')
    link = sent_ask(user, deal, days_ago=1)
    review_services.set_nudge(user, link.id, day(2))  # the link settings card's writer (slice 57)
    row = row_of(feed(api), 'nudge', deal.id)
    assert row['category'] == 'task' and row['due_in'] == 2
    assert row['link'] == f'/deals/{deal.id}/review?view=request&target=link%3A{link.id}&settings={link.id}'
