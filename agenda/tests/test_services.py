"""Agenda's writes (I.6 `test_services`; Q.3 #1): the write-path contract for marks and tasks, `log_follow_up` all or
nothing, Activity without titles or notes, and Revert restoring a date and a deleted task."""

from datetime import timedelta
from unittest import mock

import pytest

from agenda import services
from agenda.models import StepMark, Task
from agenda.services import marks as mark_services
from conftest import write_path_contract
from deals import activity, clock
from deals.models import Activity, Note

from .world import sent_ask

pytestmark = pytest.mark.django_db


def day(n):
    return (clock.today() + timedelta(days=n)).isoformat()


def test_Q3_1_I22_a_later_mark_follows_the_write_path(user, deal):
    services.set_later(user, deal.id, 'import_census', day(2))
    mark = StepMark.objects.get(deal=deal, step_key='import_census')
    write_path_contract(
        user,
        mark,
        lambda: services.set_later(user, deal.id, 'import_census', day(5)),
        lambda row: row.until,
        lambda: services.set_later(user, deal.id, 'import_census', day(9)),
    )


def test_Q3_1_I32_a_task_date_follows_the_write_path_and_revert_restores_it(user, deal):
    task = services.add_task(user, deal.id, title='Send the renewal to HR', due=day(1))
    write_path_contract(
        user,
        task,
        lambda: services.move_task(user, task.id, day(4)),
        lambda row: row.due,
        lambda: services.move_task(user, task.id, day(8)),
    )


def test_I33_revert_restores_a_deleted_task(user, deal):
    task = services.add_task(user, deal.id, title='Call the carrier rep', due=day(1))
    row = services.delete_task(user, task.id)
    assert not Task.objects.filter(pk=task.id).exists()
    activity.revert(row.id, user)
    assert Task.objects.filter(pk=task.id).exists()


def test_I24_log_follow_up_is_all_or_nothing(user, deal):
    sent_ask(user, deal)
    notes = Note.objects.filter(deal=deal).count()
    with mock.patch.object(mark_services, '_write', side_effect=RuntimeError('the mark failed')):
        with pytest.raises(RuntimeError):
            services.log_follow_up(user, deal.id, 'follow_up_client', 'call', 'Left a voicemail')
    assert Note.objects.filter(deal=deal).count() == notes
    assert not StepMark.objects.filter(deal=deal).exists()


def test_I24_a_logged_follow_up_is_a_call_note_and_waits_its_interval_again(user, deal):
    sent_ask(user, deal)
    answer = services.log_follow_up(user, deal.id, 'follow_up_client', 'call', 'Left a voicemail')
    note = answer['note']
    assert (note.kind, note.body) == ('call', 'Left a voicemail')
    assert answer['step']['section'] == 'later' and answer['step']['later_until'] == day(3)
    assert answer['next_step']['key'] != 'follow_up_client'
    with pytest.raises(Exception) as refused:
        services.log_follow_up(user, deal.id, 'import_census', 'call', 'Hello')
    assert 'Only a follow-up is logged' in str(refused.value.detail)


def test_I32_I33_activity_holds_no_titles_or_notes(user, deal):
    task = services.add_task(user, deal.id, title='Ask Riley about COBRA', due=day(1), note='Riley prefers email')
    services.update_task(user, task.id, title='Ask Riley about the COBRA count', note='Call after 2 pm')
    services.set_later(user, deal.id, 'import_census', day(3), 'Waiting for the HR system export')
    rows = Activity.objects.filter(deal=deal, area='agenda')
    text = ' '.join(f'{row.summary} {row.changes}' for row in rows)
    for words in ('Riley', 'COBRA', 'email', '2 pm', 'HR system'):
        assert words not in text
    edited = rows.filter(summary='Edited a task').get()
    assert edited.changes == [{'t': f'task:{task.id}', 'k': ['note', 'title']}] and not edited.revertible


def test_I31_ticks_coalesce_into_one_row(user, deal):
    first = services.add_task(user, deal.id, title='One', due=day(1))
    second = services.add_task(user, deal.id, title='Two', due=day(1))
    services.update_task(user, first.id, done=True)
    services.update_task(user, second.id, done=True)
    row = Activity.objects.filter(deal=deal, area='agenda').latest('id')
    assert row.summary == 'Ticked 2 tasks' and row.count == 2
    activity.revert(row.id, user)
    assert not Task.objects.filter(deal=deal, done_at__isnull=False).exists()
