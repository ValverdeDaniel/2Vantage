"""Saved board setups, Mine and Shared (plan.md §6.7, §7.8; F28, OQ7; Q.9 row 10): the services, the endpoints, who
sees and changes what, and the Q.3 contracts a setup owes as a firm row (its Activity row has no deal)."""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from conftest import write_path_contract
from deals import activity
from deals.models import Activity
from quotes.models import SavedView
from quotes.services import saved_views

pytestmark = pytest.mark.django_db

URL = '/api/saved-views/'
CONFIG = {'find': 'UHC', 'rules': [{'key': 'total', 'op': '<=', 'value': 45000, 'line': 'medical'}]}


@pytest.fixture
def other(db):
    return get_user_model().objects.create_user('omar', 'omar@example.com', 'pw-Example-1', first_name='Omar')


def signed_in(user):
    client = APIClient()
    client.force_login(user)
    return client


def setup(user, name='Budget-conscious medical', **data):
    return saved_views.create(user, {'name': name, 'config': CONFIG, **data})


def test_F28_save_current_stores_the_cleaned_config_privately(api, user):
    response = api.post(URL, {'name': ' Under $45k ', 'line': 'medical', 'config': CONFIG}, format='json')
    assert response.status_code == 201
    body = response.json()
    assert body['name'] == 'Under $45k' and body['line'] == 'medical' and body['shared'] is False
    assert body['config']['find'] == 'UHC' and body['config']['preset'] == 'primary'
    assert body['is_mine'] and body['can_edit'] and body['owner_name'] == 'Dana'
    row = Activity.objects.get(subject=f'saved_view:{body["id"]}')
    assert row.deal_id is None and row.action == 'created' and not row.revertible


def test_F28_a_bad_setup_answers_400_naming_each_field(api):
    body = {'name': '', 'line': 'boats', 'config': {'budget_pct': 12, 'pick': []}}
    response = api.post(URL, body, format='json')
    assert response.status_code == 400
    errors = response.json()
    assert set(errors) == {'name', 'line', 'config'}
    assert set(errors['config']) == {'budget_pct', 'pick'}
    assert not SavedView.objects.exists()


def test_F28_one_name_per_person_and_board(api, user, other):
    setup(user)
    response = api.post(URL, {'name': 'Budget-conscious medical', 'config': {}}, format='json')
    assert response.status_code == 400 and 'already have' in response.json()['name']
    setup(other)  # another person may use the same name


def test_F28_the_list_is_mine_then_shared_offered_on_the_line(api, user, other):
    mine = setup(user, 'Mine on medical', line='medical')
    anywhere = setup(user, 'Mine anywhere')
    dental = setup(user, 'Mine on dental', line='dental')
    shared = setup(other, 'Omar shared', shared=True)
    setup(other, 'Omar private')
    names = {row['id']: row for row in api.get(URL, {'view': 'quotes', 'line': 'medical'}).json()}
    assert set(names) == {mine.id, anywhere.id, shared.id}  # not dental's, not Omar's private one
    assert names[shared.id]['is_mine'] is False and names[shared.id]['can_edit'] is False
    assert names[shared.id]['owner_name'] == 'Omar'
    assert {row['id'] for row in api.get(URL).json()} == {mine.id, anywhere.id, dental.id, shared.id}


def test_F28_another_persons_private_setup_answers_404(api, other):
    private = setup(other, 'Omar private')
    path = f'{URL}{private.id}/'
    assert api.get(path).status_code == 404
    assert api.patch(path, {'name': 'Mine now'}, format='json').status_code == 404
    assert api.delete(path).status_code == 404
    private.refresh_from_db()
    assert private.name == 'Omar private'


def test_F28_a_shared_setup_is_used_by_all_and_changed_by_its_owner_or_an_admin(api, admin_api, other):
    shared = setup(other, 'Omar shared', shared=True)
    path = f'{URL}{shared.id}/'
    assert api.get(path).status_code == 200
    refused = api.patch(path, {'name': 'Taken over'}, format='json')
    assert refused.status_code == 403 and 'belongs to someone else' in refused.json()['detail']
    assert api.delete(path).status_code == 403
    assert admin_api.patch(path, {'description': 'Checked by the admin'}, format='json').status_code == 200
    assert admin_api.delete(path).status_code == 204
    assert not SavedView.objects.filter(pk=shared.id).exists()


def test_F28_an_admin_does_not_see_another_persons_private_setup(admin_api, other):
    private = setup(other, 'Omar private')
    assert admin_api.get(f'{URL}{private.id}/').status_code == 404
    assert admin_api.get(URL).json() == []


def test_F28_update_overwrites_with_what_is_on_screen_and_an_unchanged_save_writes_nothing(api, user):
    row = setup(user)
    path = f'{URL}{row.id}/'
    config = {**CONFIG, 'preset': 'rates', 'sort': {'key': 'total', 'dir': -1}}
    answer = api.patch(path, {'config': config, 'shared': True}, format='json').json()
    assert answer['shared'] is True and answer['config']['preset'] == 'rates' and answer['activity_id']
    rows = Activity.objects.count()
    again = api.patch(path, {'config': config, 'shared': True}, format='json').json()
    assert again['activity_id'] is None and Activity.objects.count() == rows


def test_F28_Q3_update_write_path(user):
    row = setup(user)
    write_path_contract(
        user,
        row,
        call=lambda: saved_views.update(user, row.id, {'name': 'Renamed', 'config': {'find': 'Cigna'}}),
        read=lambda view: (view.name, view.config),
        later=lambda: saved_views.update(user, row.id, {'name': 'Renamed again'}),
    )


def test_F28_delete_is_recorded_and_not_reverted(api, user):
    row = setup(user)
    assert api.delete(f'{URL}{row.id}/').status_code == 204
    entry = Activity.objects.get(subject=f'saved_view:{row.id}', action='deleted')
    assert entry.changes[0]['k']['name'] == ['Budget-conscious medical', None]
    with pytest.raises(activity.Refused):
        activity.revert(entry.id, user)


def test_F28_revert_of_an_update_refuses_once_the_setup_is_gone(user):
    row = setup(user)
    _, entry = saved_views.update(user, row.id, {'description': 'Within 10%'})
    saved_views.delete(user, row.id)
    with pytest.raises(activity.Refused) as refused:
        activity.revert(entry.id, user)
    assert refused.value.sentence == saved_views.GONE


def test_F28_ids_are_numbers(api):
    assert api.get(f'{URL}abc/').status_code == 404
    response = api.post(URL, {'name': 'x', 'view': 'census-review', 'config': {}}, format='json')
    assert response.status_code == 400 and set(response.json()) == {'view'}


def test_Q3_4_the_saved_views_list_runs_the_same_queries_at_1_and_10_setups(api, user, other):
    def count():
        with CaptureQueriesContext(connection) as captured:
            assert api.get(URL, {'view': 'quotes'}).status_code == 200
        return len(captured.captured_queries)

    setup(user, 'One')
    small = count()
    for n in range(9):
        setup(other if n % 2 else user, f'Setup {n}', shared=True)
    assert count() == small
