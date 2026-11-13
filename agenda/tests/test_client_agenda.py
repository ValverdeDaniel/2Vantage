"""The client's Agenda (plan.md §7.15, §8.5; CL24, I103 as Simplified; Q.9 row 68): `GET clients/{id}/agenda/` — one
panel per deal still being worked, each equal to that deal's own Agenda; the rollup (`counts`) the sidebar, the nav
badge and the Overview's Agenda tile read; a task added from the client page lands on the deal's Agenda and in the Work
queue, and Later holds it; the same queries whatever the deals hold. Synthetic deals; GD1-sold from `sell_gd1`."""

from datetime import date, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from agenda import client_agenda, selectors, services
from conftest import make_client, make_deal
from deals import clock
from deals.models import Deal
from deals.services import mark_lost

pytestmark = pytest.mark.django_db


def day(n):
    return (clock.today() + timedelta(days=n)).isoformat()


def sister(user, client, name, effective=None):
    """A second deal of `client` (v1 opens one deal per client; the client Agenda lists every deal still worked)."""
    other = make_deal(user, name=name)
    Deal.objects.filter(pk=other.id).update(client=client, effective_date=effective)
    return Deal.objects.get(pk=other.id)


def read(api, client_id):
    response = api.get(f'/api/clients/{client_id}/agenda/')
    assert response.status_code == 200
    return response.json()


def deal_read(api, deal):
    return api.get(f'/api/deals/{deal.id}/agenda/').json()


def test_Q9_68_GD1_sold_the_client_agenda_equals_its_deals_agenda(api, user, sell_gd1):
    deal = sell_gd1.deal
    services.add_task(user, deal.id, title='Call HR about the renewal (synthetic)', due=day(5))
    payload = read(api, deal.client_id)
    [panel] = payload['deals']
    own = deal_read(api, deal)
    assert panel['deal'] == {'id': deal.id, 'stage': 'sold', 'effective_date': deal.effective_date.isoformat(),
                             'link': f'/deals/{deal.id}/agenda'}  # fmt: skip
    assert panel['rows'] == own['rows'] and panel['next_step'] == own['next_step']
    assert panel['waiting'] == own['waiting'] and payload['today'] == own['today']
    assert payload['counts'] == {'overdue': 0, 'soon': 1, 'total': 1}  # the task, due within 30 days


def test_CL24_every_deal_still_worked_has_its_panel_equal_to_its_own_agenda(api, user):
    client, first = make_client(user, name='Two Deals Co. (synthetic)', effective_date=clock.today() + timedelta(60))
    second = sister(user, client, 'Two Deals Second (synthetic)', clock.today() + timedelta(days=30))
    services.set_later(user, first.id, 'complete_intake', day(2))
    services.add_task(user, second.id, title='Send the renewal to HR', due=day(1))
    payload = read(api, client.id)
    assert [panel['deal']['id'] for panel in payload['deals']] == [second.id, first.id]  # the soonest first
    for panel, deal in zip(payload['deals'], (second, first), strict=True):
        own = deal_read(api, deal)
        assert (panel['rows'], panel['next_step'], panel['waiting']) == (own['rows'], own['next_step'], own['waiting'])


def test_CL24_a_lost_deal_and_one_a_year_past_its_effective_date_have_no_panel(api, user):
    client, live = make_client(user, name='Past Deals Co. (synthetic)')
    lost = sister(user, client, 'Past Deals Lost (synthetic)')
    services.add_task(user, lost.id, title='Return the binder', due=day(-3))
    mark_lost(user, lost.id, 'Went with another broker')
    sister(user, client, 'Past Deals Old (synthetic)', clock.today() - timedelta(days=400))
    payload = read(api, client.id)
    assert [panel['deal']['id'] for panel in payload['deals']] == [live.id]
    assert payload['counts']['overdue'] == 0  # the lost deal's overdue task is not this agenda's


def test_CL13_CL18_the_rollup_counts_open_rows_by_their_day_and_the_overview_tile_reads_it(api, user):
    client, deal = make_client(user, name='Rollup Co. (synthetic)')
    services.add_task(user, deal.id, title='Overdue', due=day(-1))
    services.add_task(user, deal.id, title='Soon', due=day(30))
    services.add_task(user, deal.id, title='Far', due=day(31))
    services.add_task(user, deal.id, title='Ticked', due=day(-5), done=True)
    payload = read(api, client.id)
    open_rows = [row for row in payload['deals'][0]['rows'] if row['section'] in ('up_next', 'waiting')]
    assert payload['counts']['total'] == len(open_rows)
    assert payload['counts']['overdue'] == 1
    ahead = [(date.fromisoformat(row['date'][:10]) - clock.today()).days for row in open_rows if row['date']]
    soon = [days for days in ahead if 0 <= days <= 30]
    assert payload['counts']['soon'] == len(soon) >= 1  # by the day it falls due (the "Soon" task), never undated
    tile = api.get(f'/api/clients/{client.id}/overview/').json()['tiles']['agenda']
    assert tile == payload['counts']
    services.set_later(user, deal.id, 'complete_intake', day(3))  # a Later'd step leaves the open count
    assert read(api, client.id)['counts']['total'] < payload['counts']['total']


def test_CL24_a_task_added_on_the_client_agenda_lands_on_the_deal_and_the_work_queue_and_later_holds_it(api, user):
    client, deal = make_client(user, name='Client Task Co. (synthetic)')
    added = api.post(f'/api/deals/{deal.id}/tasks/', {'title': 'Walk the census with HR (synthetic)', 'due': day(2)},
                     format='json')  # fmt: skip
    assert added.status_code == 201
    task_id = added.json()['task_id']
    row = next(row for row in read(api, client.id)['deals'][0]['rows'] if row.get('task_id') == task_id)
    assert row['section'] == 'up_next' and row['date'] == day(2)
    assert any(entry.get('task_id') == task_id for entry in deal_read(api, deal)['rows'])
    queue = api.get('/api/work-queue/').json()['rows']
    assert next(entry for entry in queue if entry.get('task_id') == task_id)['due'] == day(2)

    moved = api.patch(f'/api/tasks/{task_id}/', {'due': day(5), 'move_note': 'HR is out until then'}, format='json')
    assert moved.status_code == 200
    held = next(row for row in read(api, client.id)['deals'][0]['rows'] if row.get('task_id') == task_id)
    assert held['date'] == day(5) and held['section'] == 'up_next'
    assert next(entry for entry in api.get('/api/work-queue/').json()['rows'] if entry.get('task_id') == task_id)[
        'due'
    ] == day(5)


def test_CL24_a_client_with_no_deal_reads_an_empty_agenda(api, user):
    from deals.services import create_client

    client, _none = create_client(user, name='No Deal Co. (synthetic)', first_deal=False)
    assert read(api, client.id) == {'today': clock.today().isoformat(),
                                    'counts': {'overdue': 0, 'soon': 0, 'total': 0}, 'deals': []}  # fmt: skip


def test_Q3_4_the_client_agenda_reads_in_the_same_queries_for_one_deal_or_three(api, user):
    one, deal = make_client(user, name='One Deal Co. (synthetic)')
    services.add_task(user, deal.id, title='One', due=day(1))
    three, first = make_client(user, name='Three Deals Co. (synthetic)')
    for n in range(2):
        sister(user, three, f'Three Deals {n} (synthetic)')
    for found in Deal.objects.filter(client=three):
        for n in range(4):
            services.add_task(user, found.id, title=f'Task {n}', due=day(n), assigned_to=user.id)
        services.set_later(user, found.id, 'complete_intake', day(3))

    def queries(client_id):
        with CaptureQueriesContext(connection) as found:
            read(api, client_id)
        return len(found.captured_queries)

    assert queries(one.id) == queries(three.id)


def test_CL24_the_pieces_answer_what_the_endpoint_answers(user):
    client, deal = make_client(user, name='Pieces Co. (synthetic)')
    services.add_task(user, deal.id, title='Call the carrier', due=day(4))
    whole = client_agenda.client_agenda(client, user)
    assert whole['deals'][0]['rows'] == selectors.deal_agenda(deal, user)['rows']
