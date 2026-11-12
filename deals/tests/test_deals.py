from datetime import timedelta
from unittest import mock

from conftest import make_client, make_deal
from deals import activity, clock, stages
from deals.models import Activity, Deal


def test_create_client_makes_the_client_and_its_first_deal(api):
    response = api.post('/api/clients/', {'name': ' Example Co. ', 'effective_date': '2027-01-01'}, format='json')
    assert response.status_code == 201
    deal = Deal.objects.get(pk=response.json()['deal']['id'])
    assert deal.client.name == 'Example Co.'
    assert deal.requested_lines == []  # the lines to quote come through intake's intent door (B17)
    assert deal.stage == 'intake'
    assert deal.activity.filter(action='created').exists()


def test_B17_lines_are_refused_here_and_named_to_their_door(api, deal):
    response = api.post('/api/clients/', {'name': 'X', 'requested_lines': ['medical']}, format='json')
    assert response.status_code == 400
    assert response.json() == {'requested_lines': ['Change the lines to quote through deals/<id>/intake/intent/.']}
    response = api.patch(f'/api/deals/{deal.id}/', {'requested_lines': ['medical']}, format='json')
    door = f'Change the lines to quote through deals/{deal.id}/intake/intent/.'
    assert response.status_code == 400 and response.json() == {'requested_lines': [door]}


def test_search_type_filter_and_pagination(api, user):
    for i in range(27):
        make_client(user, name=f'Acme {i:02d}')
    make_client(user, name='Other Ltd', relationship='existing_client')
    page1 = api.get('/api/clients/?q=acme').json()
    assert page1['count'] == 27 and len(page1['results']) == 25 and page1['next']
    assert api.get('/api/clients/?q=acme&page=2').json()['results']
    existing = api.get('/api/clients/?relationship=existing_client').json()
    assert [row['name'] for row in existing['results']] == ['Other Ltd']


def test_last_activity_follows_the_activity_log(api, user):
    old = make_deal(user, name='Old')
    make_deal(user, name='New')
    later = clock.now() + timedelta(minutes=30)
    with mock.patch.object(clock, 'now', return_value=later):
        activity.record(old, user, 'quotes', 'updated', 'Edited plan values')
    names = [row['name'] for row in api.get('/api/clients/').json()['results']]
    assert names[0] == 'Old'


def test_manual_stage_changes_and_refusals(api, deal):
    assert api.patch(f'/api/deals/{deal.id}/', {'stage': 'quoting'}, format='json').json()['stage'] == 'quoting'
    for stage in ('sold', 'lost'):
        response = api.patch(f'/api/deals/{deal.id}/', {'stage': stage}, format='json')
        assert response.status_code == 400
        assert response.json() == {'stage': ['Mark a plan sold or use Mark lost.']}


def test_lost_and_reopen_and_a_lost_deal_stays_editable(api, deal):
    assert api.post(f'/api/deals/{deal.id}/lost/', {'reason': ''}, format='json').status_code == 400
    lost = api.post(f'/api/deals/{deal.id}/lost/', {'reason': 'Went with another broker'}, format='json').json()
    assert lost['stage'] == 'lost'
    edited = api.patch(f'/api/deals/{deal.id}/', {'effective_date': '2027-02-01'}, format='json')
    assert edited.status_code == 200 and edited.json()['effective_date'] == '2027-02-01'
    reopened = api.post(f'/api/deals/{deal.id}/reopen/').json()
    assert reopened['stage'] == 'intake' and reopened['lost_reason'] == ''


def test_a_sold_deal_cannot_be_marked_lost(api, deal):
    Deal.objects.filter(pk=deal.pk).update(stage='sold')
    assert api.post(f'/api/deals/{deal.id}/lost/', {'reason': 'x'}, format='json').status_code == 409


def test_automatic_moves_only_go_forward():
    assert stages.forward('quoting', 'proposal') == 'proposal'
    assert stages.forward('proposal', 'quoting') == 'proposal'
    assert stages.forward('lost', 'proposal') == 'lost'


def test_consecutive_writes_coalesce_within_ten_minutes_and_not_after(deal, user):
    start = clock.now()
    with mock.patch.object(clock, 'now', return_value=start):
        activity.record(deal, user, 'quotes', 'updated', 'Edited', coalesce_key='quotes:values', noun='plan value')
    with mock.patch.object(clock, 'now', return_value=start + timedelta(minutes=5)):
        row = activity.record(deal, user, 'quotes', 'updated', 'Edited', 3, 'quotes:values', 'plan value')
    assert row.count == 4 and row.summary == 'Edited 4 plan values'
    with mock.patch.object(clock, 'now', return_value=start + timedelta(minutes=16)):
        activity.record(deal, user, 'quotes', 'updated', 'Edited', coalesce_key='quotes:values', noun='plan value')
    assert Activity.objects.filter(deal=deal, coalesce_key='quotes:values').count() == 2


def test_activity_list_is_paginated(api, deal):
    body = api.get(f'/api/deals/{deal.id}/activity/').json()
    assert body['results'][-1]['summary'] == 'Created Example Co.' and 'next' in body


def test_only_an_admin_deletes_a_client(api, admin_api, deal):
    assert api.delete(f'/api/clients/{deal.client_id}/').status_code == 403
    assert admin_api.delete(f'/api/clients/{deal.client_id}/').status_code == 204
    assert not Deal.objects.filter(pk=deal.pk).exists()
