"""The client status door and its payloads (plan.md §5.1, §7.3; CL1, CL4–CL9). Sales are in quotes' tests."""

import pytest

from conftest import make_client, make_deal, write_path_contract
from deals import activity, clock, providers, services
from deals.models import Activity, Client, Deal

LOST = 'This deal is marked lost — reopen it before converting the client.'
SOLD = 'A plan is marked sold — un-sell it first.'


@pytest.fixture
def plan_is_sold(monkeypatch):
    monkeypatch.setitem(providers._slots, 'client_has_sold', lambda client_id: True)


def move(api, client_id, to):
    return api.post(f'/api/clients/{client_id}/status/', {'to': to}, format='json')


def status_rows(client_id):
    return Activity.objects.filter(area='client', changes__contains=[{'t': f'client:{client_id}'}])


def test_CL4_convert_to_client_makes_a_new_client_since_today_with_one_activity_row(api, deal):
    response = move(api, deal.client_id, 'new_client')
    assert response.status_code == 200, response.json()
    body = response.json()
    today = clock.today().isoformat()
    assert (body['relationship'], body['client_since']) == ('new_client', today)
    (row,) = status_rows(deal.client_id)
    assert (row.deal_id, row.action, row.summary) == (deal.id, 'converted', 'Converted to a client')
    assert row.revertible
    assert row.changes[0] == {
        't': f'client:{deal.client_id}',
        'k': {'relationship': ['prospect', 'new_client'], 'client_since': [None, today]},
    }
    assert move(api, deal.client_id, 'new_client').status_code == 200  # a move to the current status writes nothing
    assert status_rows(deal.client_id).count() == 1


def test_CL4_convert_answers_409_on_a_lost_deal(api, deal):
    api.post(f'/api/deals/{deal.id}/lost/', {'reason': 'Went elsewhere'}, format='json')
    response = move(api, deal.client_id, 'new_client')
    assert (response.status_code, response.json()) == (409, {'detail': LOST})
    assert Client.objects.get(pk=deal.client_id).relationship == 'prospect'


def test_CL5_back_to_prospect_answers_409_while_a_plan_is_sold(api, user, deal, plan_is_sold):
    services.set_status(user, deal.client_id, 'new_client')
    response = move(api, deal.client_id, 'prospect')
    assert (response.status_code, response.json()) == (409, {'detail': SOLD})


def test_CL5_back_to_prospect_clears_client_since(api, user, deal):
    services.set_status(user, deal.client_id, 'new_client')
    body = move(api, deal.client_id, 'prospect').json()
    assert (body['relationship'], body['client_since']) == ('prospect', None)
    assert status_rows(deal.client_id).latest('id').summary == 'Moved back to a prospect'


def test_CL7_new_client_to_existing_client_answers_409(api, user, deal):
    services.set_status(user, deal.client_id, 'new_client')
    response = move(api, deal.client_id, 'existing_client')
    assert response.status_code == 409
    assert response.json() == {
        'detail': "A new client becomes existing with its first renewal, which this version doesn't build yet."
    }


@pytest.mark.parametrize('body', [{}, {'to': 'existing'}, {'to': 7}])
def test_CL9_an_unknown_status_is_a_400(api, deal, body):
    assert api.post(f'/api/clients/{deal.client_id}/status/', body, format='json').status_code == 400


def test_CL6_create_refuses_new_client_and_an_existing_clients_deal_opens_as_a_renewal(api):
    refused = api.post('/api/clients/', {'name': 'Won Co.', 'relationship': 'new_client'}, format='json')
    assert refused.status_code == 400
    sentence = 'A prospect becomes a new client when a plan is sold, or with Convert to client.'
    assert refused.json() == {'relationship': [sentence]}
    created = api.post('/api/clients/', {'name': 'Served Co.', 'relationship': 'existing_client'}, format='json')
    assert created.status_code == 201
    assert created.json()['client']['relationship'] == 'existing_client'
    assert Deal.objects.get(pk=created.json()['deal']['id']).opened_as == 'existing_client'
    plain = api.post('/api/clients/', {'name': 'New Co.'}, format='json').json()
    assert plain['client']['relationship'] == 'prospect' and plain['deal']['client']['client_since'] is None


def test_CL9_patch_refuses_relationship_naming_the_status_door(api, deal):
    response = api.patch(f'/api/clients/{deal.client_id}/', {'relationship': 'new_client'}, format='json')
    assert response.status_code == 400
    assert response.json() == {'relationship': [f'Change the status through clients/{deal.client_id}/status/.']}


def test_CL9_the_status_filter_takes_a_comma_list(api, user):
    make_client(user, name='Prospect Co.')
    converted = make_deal(user, name='Converted Co.')
    services.set_status(user, converted.client_id, 'new_client')
    make_client(user, name='Served Co.', relationship='existing_client')

    def names(query):
        return sorted(row['name'] for row in api.get(f'/api/clients/?relationship={query}').json()['results'])

    assert names('prospect') == ['Prospect Co.']
    assert names('new_client,existing_client') == ['Converted Co.', 'Served Co.']
    assert names('') == ['Converted Co.', 'Prospect Co.', 'Served Co.']
    row = next(r for r in api.get('/api/clients/?relationship=new_client').json()['results'])
    assert row['client_since'] == clock.today().isoformat()
    assert api.get('/api/clients/?relationship=prospect,existing').status_code == 400


def test_CL8_opened_as_follows_the_status_while_no_plan_is_sold(user, deal, monkeypatch):
    def opened_as():
        return Deal.objects.get(pk=deal.id).opened_as

    for to in ('existing_client', 'prospect', 'new_client'):
        services.set_status(user, deal.client_id, to)
        assert opened_as() == to
    services.set_status(user, deal.client_id, 'prospect')
    monkeypatch.setitem(providers._slots, 'client_has_sold', lambda client_id: True)
    services.set_status(user, deal.client_id, 'existing_client')  # a sold deal's type is frozen
    assert opened_as() == 'prospect'


def test_CL9_the_client_detail_and_the_deal_header_carry_the_status(api, user, deal):
    services.set_status(user, deal.client_id, 'new_client')
    detail = api.get(f'/api/clients/{deal.client_id}/').json()
    assert detail['client_since'] == clock.today().isoformat()
    assert detail['moves'] == [
        {'to': 'prospect', 'label': 'Back to prospect', 'allowed': True, 'sentence': ''},
        {
            'to': 'existing_client',
            'label': 'Mark as an existing client',
            'allowed': False,
            'sentence': "A new client becomes existing with its first renewal, which this version doesn't build yet.",
        },
    ]
    header = api.get(f'/api/deals/{deal.id}/').json()['client']
    assert header == {**header, 'relationship': 'new_client', 'client_since': clock.today().isoformat()}


def test_CL9_a_lost_prospects_dialog_greys_convert_with_its_sentence(api, deal):
    api.post(f'/api/deals/{deal.id}/lost/', {'reason': 'Went elsewhere'}, format='json')
    moves = api.get(f'/api/clients/{deal.client_id}/').json()['moves']
    assert moves[0] == {'to': 'new_client', 'label': 'Convert to client', 'allowed': False, 'sentence': LOST}


def test_A34_a_hand_status_row_reverts_once_and_not_after_a_later_move(user, deal):
    client = deal.client

    def later():
        services.set_status(user, client.id, 'prospect')

    row = write_path_contract(
        user,
        client,
        lambda: services.set_status(user, client.id, 'new_client'),
        lambda c: (c.relationship, c.client_since, c.converted_by_sale),
        later,
    )
    assert row.area == 'client' and row.action == 'converted'


def test_A34_reverting_a_conversion_is_refused_while_a_plan_is_sold(user, deal, monkeypatch):
    services.set_status(user, deal.client_id, 'new_client')
    row = status_rows(deal.client_id).get()
    monkeypatch.setitem(providers._slots, 'client_has_sold', lambda client_id: True)
    with pytest.raises(activity.Refused) as refused:
        activity.revert(row.id, user)
    assert refused.value.sentence == SOLD


def test_CL1_a_client_with_no_deal_gets_a_firm_row_that_reverts(user, deal):
    client_id = deal.client_id
    Deal.objects.filter(pk=deal.id).delete()
    services.set_status(user, client_id, 'existing_client')
    row = Activity.objects.get(area='client')
    assert (row.deal_id, row.subject, row.summary) == (None, f'client:{client_id}', 'Marked as an existing client')
    activity.revert(row.id, user)
    assert Client.objects.get(pk=client_id).relationship == 'prospect'
