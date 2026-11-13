"""The client box on the golden deals (plan.md §13.2 row 62, §5.1; M21, M23 as changed by OQ2; CL4, CL26; OQ101 a):
a prospect's box offers Convert to client, which the status door refuses on a lost deal; a client's box links to its
client (the client dialog until slice 67). Convert goes through deals' status door only (rule 6)."""

import pytest

from deals import lifecycle
from deals.models import Activity
from deals.services import mark_lost, reopen
from quotes.math import round_money

pytestmark = pytest.mark.django_db

LOST = 'This deal is marked lost — reopen it before converting the client.'


def box(api, deal):
    response = api.get(f'/api/deals/{deal.id}/overview/')
    assert response.status_code == 200
    return response.json()['client']


def test_CL4_GD2s_box_offers_convert_to_client(api, gd2):
    found = box(api, gd2.deal)
    assert found['relationship'] == lifecycle.PROSPECT and found['on_book'] is False
    assert found['convert'] == {'allowed': True, 'sentence': ''}
    assert found['name'] == gd2.spec['client']


def test_CL4_a_lost_GD2_refuses_convert_and_reopened_it_converts_with_one_activity_row(api, user, fresh_gd2):
    deal = fresh_gd2.deal
    mark_lost(user, deal.id, 'Went with another broker (synthetic)')
    assert box(api, deal)['convert'] == {'allowed': False, 'sentence': LOST}
    refused = api.post(f'/api/clients/{deal.client_id}/status/', {'to': lifecycle.NEW_CLIENT}, format='json')
    assert refused.status_code == 409 and refused.json()['detail'] == LOST
    reopen(user, deal.id)
    assert box(api, deal)['convert'] == {'allowed': True, 'sentence': ''}
    before = Activity.objects.filter(area='client', action='converted').count()
    converted = api.post(f'/api/clients/{deal.client_id}/status/', {'to': lifecycle.NEW_CLIENT}, format='json')
    assert converted.status_code == 200
    found = box(api, deal)
    assert found['relationship'] == lifecycle.NEW_CLIENT and found['on_book'] is True and found['convert'] is None
    assert Activity.objects.filter(area='client', action='converted').count() == before + 1


def test_M21_GD1_solds_box_links_to_its_new_client(api, gd1_sold):
    found = box(api, gd1_sold.deal)
    assert found['relationship'] == lifecycle.NEW_CLIENT and found['on_book'] is True
    assert found['convert'] is None
    assert (found['id'], found['name']) == (gd1_sold.deal.client_id, gd1_sold.spec['client'])
    assert found['client_since']


def test_M38_GD1_solds_expected_revenue_is_its_key_in_whole_dollars_half_up(api, gd1_sold, golden_keys):
    tiles = api.get(f'/api/deals/{gd1_sold.deal.id}/overview/').json()['tiles']
    assert tiles['expected_revenue'] == round_money(golden_keys['GD1-sold']['expected_total'])
