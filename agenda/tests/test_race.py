"""Q.3 #8 for Agenda's marks and tasks: two people marking different steps of one deal at once both keep their mark
(the Deal row serializes them), and a tick beside a move of the same task both land."""

import threading
from datetime import timedelta

import pytest
from django.db import close_old_connections

from agenda import services
from agenda.models import StepMark, Task
from conftest import make_deal
from deals import clock

pytestmark = pytest.mark.django_db(transaction=True)


def _together(*calls):
    barrier = threading.Barrier(len(calls))
    errors = []

    def run(call):
        try:
            barrier.wait(timeout=5)
            call()
        except Exception as exc:  # noqa: BLE001 (reported below)
            errors.append(exc)
        finally:
            close_old_connections()

    threads = [threading.Thread(target=run, args=(call,)) for call in calls]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return errors


def test_Q3_8_I23_marks_on_two_steps_at_once_both_survive(user):
    deal = make_deal(user)
    until = (clock.today() + timedelta(days=3)).isoformat()
    errors = _together(
        lambda: services.set_later(user, deal.id, 'import_census', until),
        lambda: services.set_done_anyway(user, deal.id, 'complete_intake'),
    )
    assert errors == []
    assert set(StepMark.objects.filter(deal=deal).values_list('step_key', 'kind')) == {
        ('import_census', 'later'),
        ('complete_intake', 'done'),
    }


def test_Q3_8_I31_a_tick_beside_a_move_both_land(user):
    deal = make_deal(user)
    task = services.add_task(user, deal.id, title='Send the renewal to HR', due=clock.today())
    moved = clock.today() + timedelta(days=4)
    errors = _together(
        lambda: services.update_task(user, task.id, done=True),
        lambda: services.move_task(user, task.id, moved.isoformat()),
    )
    assert errors == []
    task = Task.objects.get(pk=task.id)
    assert task.done and task.due == moved
