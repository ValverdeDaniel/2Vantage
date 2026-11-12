"""Archive and Restore a client, the Archived page and the 405 (plan.md §5.1, §7.3; A13, A18, M6–M9, M103–M105; OQ46,
OQ47). Archive hides the client and its deal from every list, even a sold one; their pages still open."""

from datetime import date

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import make_client
from contract_helpers import write_path_contract
from deals import activity, services
from deals.models import Activity, Client


def archive(api, client_id, archived=True):
    return api.post(f'/api/clients/{client_id}/archive/', {'archived': archived}, format='json')


def listed(api, **params):
    return [row['id'] for row in api.get('/api/clients/', params).json()['results']]


def test_A18_archiving_hides_the_client_from_every_list_and_restore_brings_it_back(api, user):
    kept, _ = make_client(user, name='Kept Co.')
    gone, gone_deal = make_client(user, name='Gone Co.')
    services.set_status(user, gone.id, 'new_client')

    answer = archive(api, gone.id)
    assert answer.status_code == 200
    assert answer.json()['archived']['by']['name'] == 'Dana' and answer.json()['client_id'] == gone.id
    for params in ({}, {'relationship': 'new_client'}, {'relationship': 'new_client,existing_client'}, {'q': 'Co.'}):
        assert gone.id not in listed(api, **params)
    assert kept.id in listed(api) and kept.id in listed(api, q='Co.')

    # Its pages still open, with the banner's block; nothing changed but the stamps.
    header = api.get(f'/api/deals/{gone_deal.id}/').json()
    assert header['archived']['by']['name'] == 'Dana'
    assert header['stage'] == 'intake' and header['client']['relationship'] == 'new_client'
    assert api.get(f'/api/clients/{gone.id}/').json()['archived'] is not None

    assert archive(api, gone.id, False).json()['archived'] is None
    assert gone.id in listed(api, relationship='new_client')
    assert api.get(f'/api/deals/{gone_deal.id}/').json()['archived'] is None


def test_M105_the_archived_page_lists_each_client_with_its_status_and_its_deals_stage(api, user):
    gone, gone_deal = make_client(user, name='Gone Co.', effective_date=date(2027, 1, 1))
    services.update_deal(user, gone_deal.id, stage='quoting')
    make_client(user, name='Live Co.')
    archive(api, gone.id)

    rows = api.get('/api/archived/').json()
    assert [row['name'] for row in rows] == ['Gone Co.']
    row = rows[0]
    assert row['relationship'] == 'prospect' and row['deal'] == {
        'id': gone_deal.id,
        'stage': 'quoting',
        'effective_date': '2027-01-01',
    }
    assert row['archived']['by']['name'] == 'Dana' and row['deal_count'] == 1


def test_OQ46_a_sold_deals_client_archives_too(api, user):
    client, deal = make_client(user)
    deal.stage = 'sold'
    deal.save(update_fields=['stage'])
    assert archive(api, client.id).status_code == 200
    assert client.id not in listed(api)


def test_M9_archive_and_restore_each_write_one_row_and_change_neither_stage_nor_status(user):
    client, deal = make_client(user)
    before = Client.objects.values('relationship', 'updated_at').get(pk=client.id)

    _, changed = services.set_archived(user, client.id, True)
    assert changed == {'archived': [False, True]}
    assert services.set_archived(user, client.id, True)[1] == {}  # again: nothing
    services.set_archived(user, client.id, False)

    rows = Activity.objects.filter(deal=deal, area='archive').order_by('id')
    assert [(row.action, row.summary) for row in rows] == [
        ('archived', 'Archived the client'),
        ('restored', 'Restored the client'),
    ]
    assert Client.objects.values('relationship', 'updated_at').get(pk=client.id) == before


def test_M9_restoring_keeps_the_rows_place_in_last_updated(api, user):
    older, _ = make_client(user, name='Older Co.')
    make_client(user, name='Newer Co.')
    archive(api, older.id)
    archive(api, older.id, False)
    assert listed(api)[-1] == older.id


def test_Q3_1_archive_reverts_once_and_not_after_a_later_restore(user):
    client, _ = make_client(user)
    write_path_contract(
        user,
        client,
        lambda: services.set_archived(user, client.id, True),
        lambda row: row.archived_at is None,
        lambda: services.set_archived(user, client.id, False),
    )


def test_M104_a_client_is_archived_never_deleted(api, admin_api, user):
    client, deal = make_client(user)
    for caller in (api, admin_api):
        answer = caller.delete(f'/api/clients/{client.id}/')
        assert answer.status_code == 405
        assert answer.json() == {'detail': 'Clients are archived, never deleted.'}
    assert Client.objects.filter(pk=client.id).exists()


@pytest.mark.parametrize('body', [{}, {'archived': 'yes'}, {'archived': None}])
def test_M103_archive_takes_true_or_false(api, user, body):
    client, _ = make_client(user)
    assert api.post(f'/api/clients/{client.id}/archive/', body, format='json').status_code == 400


def test_M103_an_unknown_client_is_a_404(api):
    assert archive(api, 999999).status_code == 404
    assert archive(api, 2**63).status_code == 404


def test_A18_a_revert_of_archive_is_offered_in_the_feed(api, user):
    client, deal = make_client(user)
    archive(api, client.id)
    row = api.get(f'/api/deals/{deal.id}/activity/').json()['results'][0]
    assert row['summary'] == 'Archived the client' and row['can_revert'] is True
    api.post(f'/api/activity/{row["id"]}/revert/')
    assert Client.objects.get(pk=client.id).archived_at is None
    with pytest.raises(activity.Refused):
        activity.revert(row['id'], user)


def test_Q3_4_the_archived_page_runs_the_same_queries_at_any_size(api, user):
    def count():
        with CaptureQueriesContext(connection) as queries:
            assert api.get('/api/archived/').status_code == 200
        return len(queries)

    def archive_some(n, start):
        for i in range(n):
            client, _ = make_client(user, name=f'Gone {start + i}', requested_lines=())
            services.set_archived(user, client.id, True)

    archive_some(1, 0)
    small = count()
    archive_some(9, 1)
    assert count() == small
