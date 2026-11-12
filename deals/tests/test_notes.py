"""The deal's notes (plan.md §6.2, §7.3; A37, M73–M77, M.5 B12): kinds, pinned first, author or admin, 8,000
characters, a soft delete that Revert undoes, and no words in Activity."""

import pytest
from django.contrib.auth import get_user_model

from conftest import _signed_in
from contract_helpers import write_path_contract
from deals import activity, services
from deals.models import Activity, Note


@pytest.fixture
def other_api(db):
    other = get_user_model().objects.create_user('lee', 'lee@example.com', 'pw-Example-1', first_name='Lee')
    return _signed_in(other)


def add(api, deal, **body):
    return api.post(f'/api/deals/{deal.id}/notes/', {'body': 'Called the HR lead', **body}, format='json')


def test_A37_notes_list_pinned_first_then_newest_first(api, deal):
    first = add(api, deal, body='First').json()
    pinned = add(api, deal, body='Pinned one', kind='call', pinned=True).json()
    last = add(api, deal, body='Last').json()
    shown = api.get(f'/api/deals/{deal.id}/notes/').json()
    assert [note['id'] for note in shown] == [pinned['id'], last['id'], first['id']]
    assert shown[0]['kind_label'] == 'Call' and shown[0]['author']['name'] == 'Dana' and shown[0]['can_edit']


@pytest.mark.parametrize(
    'body, field',
    [
        ({'body': '   '}, 'body'),
        ({'body': 'x' * 8001}, 'body'),
        ({'kind': 'memo'}, 'kind'),
        ({'pinned': 'yes'}, 'pinned'),
    ],
)
def test_M73_a_note_needs_text_under_8000_characters_and_a_known_kind(api, deal, body, field):
    answer = add(api, deal, **body)
    assert answer.status_code == 400 and field in answer.json()


def test_M73_a_note_of_8000_characters_is_kept_whole(api, deal):
    assert len(add(api, deal, body='y' * 8000).json()['body']) == 8000


def test_M76_only_the_author_or_an_admin_edits_or_deletes_a_note(api, admin_api, other_api, deal):
    note = add(api, deal).json()
    assert other_api.patch(f'/api/notes/{note["id"]}/', {'pinned': True}, format='json').status_code == 403
    assert other_api.delete(f'/api/notes/{note["id"]}/').status_code == 403
    assert other_api.get(f'/api/deals/{deal.id}/notes/').json()[0]['can_edit'] is False
    assert admin_api.patch(f'/api/notes/{note["id"]}/', {'body': 'Edited'}, format='json').json()['body'] == 'Edited'
    assert api.patch(f'/api/notes/{note["id"]}/', {'pinned': True}, format='json').json()['pinned'] is True


def test_M77_deleting_a_pinned_note_can_be_undone(api, deal):
    note = add(api, deal, pinned=True).json()
    deleted = api.delete(f'/api/notes/{note["id"]}/')
    assert deleted.status_code == 200
    assert api.get(f'/api/deals/{deal.id}/notes/').json() == []
    assert api.patch(f'/api/notes/{note["id"]}/', {'pinned': False}, format='json').status_code == 404

    feed = api.get(f'/api/deals/{deal.id}/activity/').json()['results'][0]
    assert feed['summary'] == 'Deleted a pinned note' and feed['can_revert'] is True
    assert api.post(f'/api/activity/{deleted.json()["activity_id"]}/revert/').status_code == 200
    back = api.get(f'/api/deals/{deal.id}/notes/').json()
    assert [(row['id'], row['pinned'], row['body']) for row in back] == [(note['id'], True, 'Called the HR lead')]


def test_M77_a_second_undo_is_refused(user, deal):
    note = services.add_note(user, deal.id, body='Met the CFO', kind='meeting')
    row = services.delete_note(user, note.id)
    activity.revert(row.id, user)
    with pytest.raises(activity.Refused) as refused:
        activity.revert(row.id, user)
    assert refused.value.sentence == activity.ALREADY_UNDONE


def test_Q3_1_a_pin_reverts_once_and_not_after_a_later_pin(user, deal):
    note = services.add_note(user, deal.id, body='Chasing the census')
    write_path_contract(
        user,
        note,
        lambda: services.update_note(user, note.id, pinned=True),
        lambda row: row.pinned,
        lambda: services.update_note(user, note.id, pinned=False),
    )


def test_Q3_1_a_body_edit_records_the_key_alone(user, deal):
    note = services.add_note(user, deal.id, body='Called Rebecca')
    services.update_note(user, note.id, body='Called Rebecca again')
    row = Activity.objects.filter(deal=deal, area='notes').latest('id')
    assert row.summary == 'Edited a note' and row.changes == [{'t': f'note:{note.id}', 'k': ['body']}]
    with pytest.raises(activity.Refused) as refused:
        activity.revert(row.id, user)
    assert refused.value.sentence == activity.KEYS_ONLY


def test_Q3_1_a_notes_words_never_reach_activity(user, deal):
    note = services.add_note(user, deal.id, body='Spoke with Rebecca Smith', kind='call', pinned=True)
    services.update_note(user, note.id, body='Spoke with Rebecca Smith twice', kind='email')
    services.delete_note(user, note.id)
    for row in Activity.objects.filter(deal=deal, area='notes'):
        assert 'Rebecca' not in row.summary and 'Rebecca' not in str(row.changes)
    assert Activity.objects.filter(deal=deal, area='notes').order_by('id').first().summary == 'Logged a call'


def test_M77_an_unchanged_edit_writes_nothing(user, deal):
    note = services.add_note(user, deal.id, body='Same')
    count = Activity.objects.count()
    assert services.update_note(user, note.id, body='Same', kind='note', pinned=False)[1] == {}
    assert Activity.objects.count() == count


def test_M77_a_deleted_note_is_kept_for_its_history(user, deal):
    note = services.add_note(user, deal.id, body='Gone soon')
    services.delete_note(user, note.id)
    assert not Note.objects.filter(pk=note.id).exists() and Note.all_objects.filter(pk=note.id).exists()


def test_A37_unknown_notes_and_deals_are_404s(api, deal):
    assert api.get('/api/deals/999999/notes/').status_code == 404
    assert api.patch('/api/notes/999999/', {'pinned': True}, format='json').status_code == 404
    assert api.delete(f'/api/notes/{2**63}/').status_code == 404
