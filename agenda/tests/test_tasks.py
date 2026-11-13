"""Tasks added by hand (I27–I34, I40; I.6 `test_tasks`): add (with `done: true`), tick, reopen, move, edit, the soft
delete's permissions (OQ93), and lost deals still taking tasks."""

from datetime import timedelta

import pytest

from agenda.models import Task
from deals import clock
from deals.models import Activity, Note
from deals.services import mark_lost

pytestmark = pytest.mark.django_db


def day(n):
    return (clock.today() + timedelta(days=n)).isoformat()


def add(api, deal, **body):
    return api.post(f'/api/deals/{deal.id}/tasks/', {'title': 'Send the renewal to HR', 'due': day(0), **body},
                    format='json')  # fmt: skip


def rows(api, deal):
    return {row['id']: row for row in api.get(f'/api/deals/{deal.id}/agenda/').json()['rows']}


def test_I27_a_task_lands_in_up_next_with_its_date_person_and_chip(api, user, deal):
    response = add(api, deal, assigned_to=user.id, note='Ask for the census too')
    assert response.status_code == 201
    task = response.json()
    assert task['assigned_to'] == {'id': user.id, 'name': 'Dana'} and task['chip'] == 'Task'
    assert task['section'] == 'up_next' and task['severity'] == 'warn'  # due today: within 30 days
    assert rows(api, deal)[task['id']]['label'] == 'Send the renewal to HR'


@pytest.mark.parametrize(
    ('body', 'field'),
    [
        ({'title': '  '}, 'title'),
        ({'title': 'x' * 301}, 'title'),
        ({'due': 'soon'}, 'due'),
        ({'due': ''}, 'due'),
        ({'assigned_to': 'ada'}, 'assigned_to'),
        ({'assigned_to': 10**12}, 'assigned_to'),
        ({'done': 'yes'}, 'done'),
        ({'note': 'n' * 2001}, 'note'),
    ],
)
def test_I28_what_a_task_needs(api, deal, body, field):
    response = add(api, deal, **body)
    assert response.status_code == 400 and field in response.json()


def test_I40_log_a_call_is_a_task_done_at_once(api, user, deal):
    task = add(api, deal, title='Called Riley (synthetic)', done=True).json()
    assert task['done'] and task['done_by'] == 'Dana' and task['section'] == 'done'


def test_I31_tick_stamps_who_and_when_and_reopen_clears_both(api, deal):
    task = add(api, deal).json()
    ticked = api.patch(f'/api/tasks/{task["task_id"]}/', {'done': True}, format='json').json()
    assert ticked['done'] and ticked['done_by'] == 'Dana' and ticked['done_at']
    reopened = api.patch(f'/api/tasks/{task["task_id"]}/', {'done': False}, format='json').json()
    assert not reopened['done'] and reopened['done_by'] == '' and reopened['done_at'] is None


def test_I32_later_moves_the_date_and_keeps_the_note_on_the_deal(api, deal):
    task = add(api, deal).json()
    moved = api.patch(f'/api/tasks/{task["task_id"]}/', {'due': day(5), 'move_note': 'HR is out this week'},
                      format='json').json()  # fmt: skip
    assert moved['due'] == day(5)
    assert Note.objects.get(deal=deal).body.endswith(': HR is out this week')
    row = Activity.objects.filter(deal=deal, area='agenda').latest('id')
    assert row.changes == [{'t': f'task:{task["task_id"]}', 'k': {'due': [day(0), day(5)]}}]


def test_I33_edit_title_note_and_person(api, admin_user, deal):
    task = add(api, deal).json()
    edited = api.patch(
        f'/api/tasks/{task["task_id"]}/',
        {'title': 'Send the renewal to Riley', 'note': 'Use the new template', 'assigned_to': admin_user.id},
        format='json',
    ).json()
    assert (edited['title'], edited['note'], edited['assigned_to']['id']) == (
        'Send the renewal to Riley',
        'Use the new template',
        admin_user.id,
    )


def test_OQ93_the_creator_or_an_admin_deletes_a_task_and_no_one_else(api, admin_api, user, deal):
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    other = APIClient()
    other.force_login(get_user_model().objects.create_user('sam', 'sam@example.com', 'pw-Example-1'))
    mine = add(api, deal).json()
    assert other.delete(f'/api/tasks/{mine["task_id"]}/').status_code == 403
    assert rows(other, deal)[mine['id']]['can']['delete'] is False
    assert api.delete(f'/api/tasks/{mine["task_id"]}/').status_code == 204
    assert api.delete(f'/api/tasks/{mine["task_id"]}/').status_code == 404
    assert Task.all_objects.get(pk=mine['task_id']).deleted_at is not None
    theirs = add(other, deal).json()
    assert admin_api.delete(f'/api/tasks/{theirs["task_id"]}/').status_code == 204


def test_I34_a_lost_deal_still_takes_tasks(api, user, deal):
    mark_lost(user, deal.id, 'Went with another broker')
    assert add(api, deal, title='Check back in six months', due=day(180)).status_code == 201
    payload = api.get(f'/api/deals/{deal.id}/agenda/').json()
    assert [row['kind'] for row in payload['rows']] == ['task']
    assert payload['next_step']['label'] == 'Deal lost — Went with another broker'


def test_I6_up_next_lists_open_tasks_by_date_then_open_steps(api, deal):
    later_task = add(api, deal, title='Second', due=day(3)).json()
    first_task = add(api, deal, title='First', due=day(1)).json()
    order = [row['id'] for row in api.get(f'/api/deals/{deal.id}/agenda/').json()['rows']]
    assert order[:2] == [first_task['id'], later_task['id']]
    assert order[2].startswith('step:')
