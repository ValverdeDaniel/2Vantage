"""`GET clients/{id}/activity/` (plan.md §7.3, §8.5; CL21): the client's Timeline — its deals' rows with their status
rows, and the rows about the client that sit on no deal — newest first, without downloads or views, without another
client's rows, each row with its deal and its detail. Synthetic only."""

import pytest

from conftest import make_deal
from deals import activity, lifecycle
from deals.models import Activity
from deals.services import add_note, create_client, set_status

pytestmark = pytest.mark.django_db


def feed(api, client_id, page=1):
    response = api.get(f'/api/clients/{client_id}/activity/', {'page': page})
    assert response.status_code == 200, response.content
    return response.json()


def test_CL21_the_client_feed_holds_its_deals_rows_and_its_status_rows(api, user):
    deal = make_deal(user, name='Feed Co. (synthetic)')
    other = make_deal(user, name='Other Co. (synthetic)')
    add_note(user, other.id, body='Not this client (synthetic)', kind='note')
    add_note(user, deal.id, body='Called Casey (synthetic)\nShe will send it.', kind='call')
    set_status(user, deal.client_id, lifecycle.NEW_CLIENT)
    found = feed(api, deal.client_id)
    rows = found['results']
    assert found['count'] == Activity.objects.filter(deal=deal).count()
    assert {row['deal_id'] for row in rows} == {deal.id}
    assert [row['summary'] for row in rows[:2]] == ['Converted to a client', 'Logged a call']
    assert rows[0]['area'] == 'client' and rows[1]['detail'] == 'Called Casey (synthetic)'
    assert [row['id'] for row in rows] == sorted((row['id'] for row in rows), reverse=True)


def test_CL21_downloads_and_views_are_neither_listed_nor_counted(api, user):
    deal = make_deal(user, name='Quiet Co. (synthetic)')
    before = feed(api, deal.client_id)['count']
    activity.log_access(deal, user, 'downloaded', 'a file', None)
    activity.log_access(deal, user, 'viewed', 'a file', None)
    found = feed(api, deal.client_id)
    assert found['count'] == before and not {row['action'] for row in found['results']} & {'downloaded', 'viewed'}


def test_CL21_a_client_with_no_deal_lists_the_rows_about_itself(api, user):
    client, _deal = create_client(
        user, name='Outside Co. (synthetic)', relationship='existing_client', first_deal=False
    )
    set_status(user, client.id, lifecycle.PROSPECT)
    rows = feed(api, client.id)['results']
    assert [row['summary'] for row in rows] == ['Moved back to a prospect', 'Created Outside Co. (synthetic)']
    assert {row['deal_id'] for row in rows} == {None}
