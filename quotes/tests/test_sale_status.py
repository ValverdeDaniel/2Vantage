"""A sale and the client status (plan.md §5.1, §5.4; CL2, CL3, CL5, CL8; F123, H124; §13.2's row 6).

`set_sold` calls `deals.services.sale_changed` inside the sale's transaction, after `advance`.
"""

import random
from unittest import mock

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import make_deal
from deals import activity, clock, services
from deals.models import Activity, Client, Deal
from quotes import services as plans
from quotes.services import marks

SOLD = 'A plan is marked sold — un-sell it first.'


@pytest.fixture
def sale(user):
    deal = make_deal(user, name='Small Shop')
    made = [
        plans.create_plan(user, deal, line=line, role='alternate', carrier='Aetna', name=f'{line} plan')
        for line in ('medical', 'dental')
    ]
    return deal, made


def client_of(deal):
    return Client.objects.get(pk=deal.client_id)


def status_rows(deal):
    return Activity.objects.filter(deal=deal, area='client')


def sell(api, plan, sold=True):
    return api.post(f'/api/plans/{plan.id}/sold/', {'sold': sold}, format='json')


def test_CL2_a_sale_converts_a_prospect_once_with_one_activity_row(api, sale):
    deal, (medical, dental) = sale
    body = sell(api, medical).json()
    assert body['deal']['stage'] == 'sold'
    assert body['deal']['client'] == {**body['deal']['client'], 'relationship': 'new_client'}
    assert body['deal']['client']['client_since'] == clock.today().isoformat()
    client = client_of(deal)
    assert (client.relationship, client.converted_by_sale) == ('new_client', True)
    (row,) = status_rows(deal)
    assert (row.deal_id, row.action, row.summary) == (deal.id, 'converted', 'Now a new client (a plan was sold)')
    summaries = list(deal.activity.order_by('id').values_list('summary', flat=True))[-3:]
    assert summaries == [f'Marked Aetna {medical.name} sold', 'Moved to Sold (a plan was sold)', row.summary]
    sell(api, dental)
    assert status_rows(deal).count() == 1


def test_CL2_the_conversion_is_part_of_the_sales_transaction(user, sale):
    deal, (medical, _) = sale
    real = marks.sale_changed

    def then_fail(*args):
        real(*args)
        raise RuntimeError('the sale failed after the conversion')

    with mock.patch.object(marks, 'sale_changed', then_fail), pytest.raises(RuntimeError):
        marks.set_sold(user, medical.id, True)
    assert client_of(deal).relationship == 'prospect'
    assert not deal.plans.filter(sold=True).exists()


def test_CL3_un_selling_the_last_sold_plan_returns_the_prospect(api, sale):
    deal, (medical, dental) = sale
    sell(api, medical)
    sell(api, dental)
    sell(api, medical, False)  # one of two sold plans: nothing changes
    assert client_of(deal).relationship == 'new_client'
    body = sell(api, dental, False).json()
    assert body['deal']['stage'] == 'proposal'
    assert body['deal']['client']['relationship'] == 'prospect' and body['deal']['client']['client_since'] is None
    assert status_rows(deal).latest('id').summary == 'Back to a prospect (no plan is sold now)'
    assert status_rows(deal).count() == 2


def test_CL4_a_hand_conversion_survives_an_un_sell(api, user, sale):
    deal, (medical, _) = sale
    services.set_status(user, deal.client_id, 'new_client')
    sell(api, medical)
    sell(api, medical, False)
    client = client_of(deal)
    assert (client.relationship, client.converted_by_sale) == ('new_client', False)


def test_CL2_existing_clients_ignore_sales(api, user):
    deal = make_deal(user, name='Served Co.', relationship='existing_client')
    plan = plans.create_plan(user, deal, line='medical', role='alternate', carrier='Cigna', name='OA')
    sell(api, plan)
    sell(api, plan, False)
    assert client_of(deal).relationship == 'existing_client'
    assert not status_rows(deal).exists()


def test_CL5_back_to_prospect_answers_409_while_a_plan_is_sold(api, sale):
    deal, (medical, _) = sale
    sell(api, medical)
    response = api.post(f'/api/clients/{deal.client_id}/status/', {'to': 'prospect'}, format='json')
    assert (response.status_code, response.json()) == (409, {'detail': SOLD})
    moves = api.get(f'/api/clients/{deal.client_id}/').json()['moves']
    assert moves[0] == {'to': 'prospect', 'label': 'Back to prospect', 'allowed': False, 'sentence': SOLD}


def test_H124_a_lost_deal_refuses_a_sale_with_its_sentence(api, sale):
    deal, (medical, _) = sale
    api.post(f'/api/deals/{deal.id}/lost/', {'reason': 'Went elsewhere'}, format='json')
    response = sell(api, medical)
    assert response.status_code == 409
    assert response.json() == {'detail': 'This deal is marked lost — reopen it before selling a plan.'}
    assert client_of(deal).relationship == 'prospect'


def test_CL8_opened_as_freezes_at_the_sale(api, user, sale):
    deal, (medical, _) = sale
    sell(api, medical)
    assert Deal.objects.get(pk=deal.id).opened_as == 'prospect'  # a won prospect's deal stays New business
    sell(api, medical, False)
    services.set_status(user, deal.client_id, 'existing_client')
    assert Deal.objects.get(pk=deal.id).opened_as == 'existing_client'  # nothing sold: it follows again


def test_A34_a_sales_status_row_refuses_revert_and_a_hand_row_reverts(api, user, sale):
    deal, (medical, _) = sale
    sell(api, medical)
    converted = status_rows(deal).get()
    rows = api.get(f'/api/deals/{deal.id}/activity/').json()['results']  # by id: the clock can step back under load
    assert next(row for row in rows if row['id'] == converted.id)['can_revert'] is False
    response = api.post(f'/api/activity/{converted.id}/revert/')
    assert (response.status_code, response.json()) == (409, {'detail': 'Un-sell the plan to undo this.'})
    sell(api, medical, False)
    undone = status_rows(deal).latest('id')
    response = api.post(f'/api/activity/{undone.id}/revert/')
    assert (response.status_code, response.json()) == (409, {'detail': 'Mark the plan sold again to undo this.'})
    services.set_status(user, deal.client_id, 'new_client')
    assert api.post(f'/api/activity/{status_rows(deal).latest("id").id}/revert/').status_code == 200
    assert client_of(deal).relationship == 'prospect'


def test_F123_set_sold_locks_the_deal_before_the_plan(user, sale):
    _, (medical, _) = sale
    with CaptureQueriesContext(connection) as queries:
        marks.set_sold(user, medical.id, True)
    locks = [q['sql'] for q in queries.captured_queries if 'FOR UPDATE' in q['sql']]
    tables = [next(t for t in ('"deals_deal"', '"quotes_plan"', '"deals_client"') if t in sql) for sql in locks]
    assert tables[:2] == ['"deals_deal"', '"quotes_plan"']
    assert tables.index('"deals_client"') > tables.index('"quotes_plan"')


def test_CL1_over_random_runs_a_client_with_a_sold_plan_is_never_a_prospect(user, sale):
    deal, made = sale
    made.append(plans.create_plan(user, deal, line='vision', role='alternate', carrier='VSP', name='Vision'))
    steps = random.Random(6)
    for _ in range(60):
        try:
            if steps.random() < 0.6:
                marks.set_sold(user, steps.choice(made).id, steps.random() < 0.55)
            else:
                services.set_status(user, deal.client_id, steps.choice(['prospect', 'new_client', 'existing_client']))
        except activity.Refused:
            pass
        client = client_of(deal)
        if deal.plans.filter(sold=True).exists():
            assert client.relationship != 'prospect'
        assert (client.client_since is None) == (client.relationship != 'new_client')
