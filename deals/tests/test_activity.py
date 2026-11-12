"""Activity with before and after, Revert and access logging (plan.md §3.7, §3.8, O.3.2; A34, E54, E99).

deals registers no reverter of its own yet, so these tests lend the 'deal' area one that puts a client's notes back,
the way an owner app does: lock its row, refuse on a later write, write the "before" back, return what it wrote.
"""

import json
from datetime import timedelta
from unittest import mock

import pytest

from conftest import make_deal
from deals import activity, clock, services
from deals.models import Activity, Client


@pytest.fixture
def notes_reverter(monkeypatch):
    def revert(row, user):
        (entry,) = row.changes
        client = Client.objects.select_for_update().get(pk=int(entry['t'].removeprefix('client:')))
        before, after = entry['k']['notes']
        if activity.later_keys(row) or client.notes != after:
            raise activity.changed_since(['Notes'], ['notes'])
        Client.objects.filter(pk=client.pk).update(notes=before)
        return [activity.change(entry['t'], {'notes': [after, before]})]

    monkeypatch.setitem(activity.reverters, 'deal', revert)


def edit_notes(user, deal, text):
    services.update_client(user, deal.client_id, notes=text)
    return Activity.objects.filter(deal=deal).latest('updated_at', 'id')


def notes(deal):
    return Client.objects.get(pk=deal.client_id).notes


def test_A34_every_write_records_before_and_after_per_key(user, deal):
    row = edit_notes(user, deal, 'Renews with a broker change')
    assert row.changes == [{'t': f'client:{deal.client_id}', 'k': {'notes': ['', 'Renews with a broker change']}}]
    assert row.revertible and row.actor_kind == 'user'
    services.update_deal(user, deal.id, effective_date=None, stage='quoting')
    stage = Activity.objects.filter(deal=deal).latest('id')
    assert stage.changes == [{'t': f'deal:{deal.id}', 'k': {'stage': ['intake', 'quoting']}}]


def test_A34_unchanged_writes_save_nothing_and_record_nothing(user, deal):
    services.update_client(user, deal.client_id, notes='Same')
    client = Client.objects.get(pk=deal.client_id)
    rows = Activity.objects.count()
    services.update_client(user, deal.client_id, notes='Same', name=client.name)
    services.update_deal(user, deal.id, stage=deal.stage, effective_date=deal.effective_date)
    assert Client.objects.get(pk=deal.client_id).updated_at == client.updated_at
    assert Activity.objects.count() == rows


def test_A34_a_burst_keeps_each_keys_first_before_and_last_after(user, deal):
    start = clock.now()
    writes = [
        [activity.change('plan:41', {'rate_ee': ['612.50', '640'], 'rate_es': ['900', '950']})],
        [activity.change('plan:41', {'rate_ee': ['640', '650']}), activity.change('plan:42', {'rate_ee': [None, '5']})],
        [activity.change('plan:41', {'rate_es': ['950', '900']})],  # back where it began: the key goes
    ]
    for minutes, changes in zip((0, 4, 8), writes, strict=True):
        with mock.patch.object(clock, 'now', return_value=start + timedelta(minutes=minutes)):
            row = activity.record(
                deal, user, 'quotes', 'updated', 'Edited', 1, 'quotes:values', 'plan value', changes=changes
            )
    assert row.count == 3 and row.summary == 'Edited 3 plan values'
    assert row.changes == [
        {'t': 'plan:41', 'k': {'rate_ee': ['612.50', '650']}},
        {'t': 'plan:42', 'k': {'rate_ee': [None, '5']}},
    ]
    assert Activity.objects.filter(deal=deal, coalesce_key='quotes:values').count() == 1


@pytest.mark.parametrize('action', ['marked', 'imported', 'issued', 'sold', 'stage', 'status'])
def test_A34_marks_imports_issues_sales_stages_and_statuses_never_merge(user, deal, action):
    for _ in range(2):
        activity.record(deal, user, 'quotes', action, 'Did it', coalesce_key='quotes:values', noun='plan value')
    assert Activity.objects.filter(deal=deal, action=action).count() == 2


def test_A34_revert_puts_the_value_back_once(api, user, deal, notes_reverter):
    edit_notes(user, deal, 'First')
    row = edit_notes(user, deal, 'Second')  # its own row: an unkeyed write never merges
    response = api.post(f'/api/activity/{row.id}/revert/')
    assert response.status_code == 200, response.json()
    body = response.json()
    assert notes(deal) == 'First'
    assert body['reverted_id'] == row.id and body['changes'][0]['k'] == {'notes': ['Second', 'First']}
    new = Activity.objects.get(pk=body['activity_id'])
    assert new.reverts_id == row.id and new.action == 'reverted' and not new.revertible
    again = api.post(f'/api/activity/{row.id}/revert/')
    assert again.status_code == 409 and again.json() == {'detail': activity.ALREADY_UNDONE}
    assert api.post(f'/api/activity/{new.id}/revert/').status_code == 409  # a revert is not reverted


def test_A34_revert_after_a_later_write_is_refused_naming_the_keys(api, user, deal, notes_reverter):
    row = edit_notes(user, deal, 'First')
    edit_notes(user, deal, 'Second')
    response = api.post(f'/api/activity/{row.id}/revert/')
    assert response.status_code == 409
    assert response.json() == {
        'detail': 'Notes was changed after this, so this change cannot be reverted.',
        'keys': ['notes'],
    }
    assert notes(deal) == 'Second' and Activity.objects.get(pk=row.id).reverted_at is None


def test_A34_a_burst_never_merges_into_a_reverted_row(user, deal):
    def write(before, after):
        changes = [activity.change('plan:1', {'rate_ee': [before, after]})]
        return activity.record(
            deal, user, 'quotes', 'updated', 'Edited', 1, 'quotes:values', 'plan value', changes=changes
        )

    first = write('1', '2')
    Activity.objects.filter(pk=first.pk).update(reverted_at=clock.now())
    assert write('2', '3').pk != first.pk


def test_A34_key_only_rows_refuse_revert_and_hold_no_values(api, user, deal, monkeypatch):
    monkeypatch.setitem(activity.reverters, 'census', lambda row, user: [])
    canary = 'Zzcanary Person'
    changes = [activity.change('member:7', {'last_name': [canary, 'Other'], 'dob': ['1970-01-01', '1971-01-01']})]
    row = activity.record(deal, user, 'census', 'updated', 'Edited 2 census values', changes=changes, keys_only=True)
    assert row.changes == [{'t': 'member:7', 'k': ['dob', 'last_name']}]
    assert canary not in json.dumps(row.changes) and '1970' not in json.dumps(row.changes)
    assert not row.revertible
    response = api.post(f'/api/activity/{row.id}/revert/')
    assert response.status_code == 409 and response.json()['detail'] == activity.KEYS_ONLY


def test_A34_rows_without_earlier_values_or_an_owner_refuse_with_a_sentence(api, user, deal):
    created = Activity.objects.get(deal=deal, action='created')
    assert api.post(f'/api/activity/{created.id}/revert/').json() == {'detail': activity.NOTHING_TO_PUT_BACK}
    row = edit_notes(user, deal, 'Text')  # the 'deal' area has no reverter in this test
    assert api.post(f'/api/activity/{row.id}/revert/').json() == {'detail': activity.NO_REVERTER}


@pytest.mark.parametrize('url, status', [('999999/', 404), ('99999999999999999999/', 404), ('abc/', 404)])
def test_A34_a_bad_activity_id_answers_404_never_500(api, url, status):
    assert api.post(f'/api/activity/{url}revert/').status_code == status


def test_A34_the_feed_says_what_can_be_reverted_and_what_was(api, user, deal, notes_reverter):
    row = edit_notes(user, deal, 'Text')
    feed = {r['id']: r for r in api.get(f'/api/deals/{deal.id}/activity/').json()['results']}
    assert feed[row.id]['can_revert'] is True and feed[row.id]['reverted'] is None
    assert not any(r['can_revert'] for r in feed.values() if r['id'] != row.id)
    api.post(f'/api/activity/{row.id}/revert/')
    feed = {r['id']: r for r in api.get(f'/api/deals/{deal.id}/activity/').json()['results']}
    assert feed[row.id]['can_revert'] is False and feed[row.id]['reverted']['by']['name'] == 'Dana'
    assert any(r['reverts_id'] == row.id for r in feed.values())


def test_E99_access_rows_name_the_file_by_id_views_coalesce_and_downloads_do_not(user, deal):
    for _ in range(2):
        activity.log_access(deal, user, 'viewed', 'a census document', 5)
        activity.log_access(deal, user, 'downloaded', 'a census document', 5)
    activity.log_access(deal, user, 'viewed', 'a census document', 6)
    views = Activity.objects.filter(deal=deal, action='viewed')
    assert sorted(views.values_list('document_id', 'count')) == [(5, 2), (6, 1)]
    assert Activity.objects.filter(deal=deal, action='downloaded', document_id=5).count() == 2
    with pytest.raises(ValueError):
        activity.log_access(deal, user, 'edited', 'a census document', 5)


def test_E99_access_rows_never_move_last_updated_nor_show_in_the_feed(api, user):
    old, new = make_deal(user, name='Old'), make_deal(user, name='New')
    later = clock.now() + timedelta(minutes=30)
    with mock.patch.object(clock, 'now', return_value=later):
        activity.log_access(old, user, 'downloaded', 'a census document', 5)
        activity.log_access(old, user, 'viewed', 'a census document', 5)
    rows = api.get('/api/clients/').json()['results']
    assert [row['name'] for row in rows][:2] == ['New', 'Old']
    feed = api.get(f'/api/deals/{old.id}/activity/').json()['results']
    assert {row['action'] for row in feed} == {'created'}
    del new
