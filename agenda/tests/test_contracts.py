"""The Q.3 contracts for agenda (plan.md §12.3): GETs write nothing, the permission matrix, ids past bigint, and the
deal's Agenda in the same number of queries whatever its tasks and marks (Q.3 #4). The shell's `journey/` and the Work
queue's feed and stats (slice 61) join every table; their scaling checks are in test_shell and test_queue_golden."""

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from agenda import services
from conftest import check_permissions, make_deal, sweep_gets
from deals import clock
from review import services as review_services

from .world import sent_ask

pytestmark = pytest.mark.django_db

BIG = 2**63


def day(n):
    return (clock.today() + timedelta(days=n)).isoformat()


@pytest.fixture
def world(user, deal):
    services.set_later(user, deal.id, 'complete_intake', day(2))
    link = sent_ask(user, deal)
    review_services.set_nudge(user, link.id, day(2))
    task = services.add_task(user, deal.id, title='Send the renewal to HR', due=day(1))
    return {'deal': deal, 'task': task, 'link': link}


def samples(world):
    deal, task, link = world['deal'], world['task'], world['link']
    return {
        'api/deals/<int:pk>/agenda/': {'pk': deal.id},
        'api/deals/<int:pk>/journey/': {'pk': deal.id},
        'api/clients/<int:pk>/agenda/': {'pk': deal.client_id},
        'api/work-queue/': {'query': {'include': 'closed'}},
        'api/work-queue/stats/': {},
        'api/deals/<int:pk>/agenda/marks/': {'pk': deal.id},
        'api/deals/<int:pk>/agenda/marks/<str:step_key>/': {'pk': deal.id, 'step_key': 'complete_intake'},
        'api/deals/<int:pk>/agenda/follow-ups/': {'pk': deal.id},
        'api/deals/<int:pk>/agenda/nudges/<int:link_id>/': {'pk': deal.id, 'link_id': link.id},
        'api/deals/<int:pk>/tasks/': {'pk': deal.id},
        'api/tasks/<int:pk>/': {'pk': task.id},
    }


def test_Q3_2_agenda_gets_write_nothing(api, world):
    sweep_gets(api, ['agenda'], samples(world))


def test_Q3_3_the_permission_matrix(actors, no_csrf_api, world):
    everyone = {'signed_out': 401, 'producer': 200, 'admin': 200}
    created = {'signed_out': 401, 'producer': 201, 'admin': 201}
    gone = {'signed_out': 401, 'producer': 204, 'admin': 204}  # the producer created it
    matrix = [
        ('GET', 'api/deals/<int:pk>/agenda/', everyone),
        ('GET', 'api/deals/<int:pk>/journey/', everyone),
        ('GET', 'api/clients/<int:pk>/agenda/', everyone),
        ('GET', 'api/work-queue/', everyone),
        ('GET', 'api/work-queue/stats/', everyone),
        ('POST', 'api/deals/<int:pk>/agenda/marks/', everyone, {'step_key': 'import_census', 'kind': 'done'}),
        ('DELETE', 'api/deals/<int:pk>/agenda/marks/<str:step_key>/', everyone),
        ('POST', 'api/deals/<int:pk>/agenda/follow-ups/', everyone,
         {'step_key': 'follow_up_client', 'kind': 'email', 'body': 'Sent a reminder'}),
        ('POST', 'api/deals/<int:pk>/agenda/nudges/<int:link_id>/', everyone, {'kind': 'done'}),
        ('POST', 'api/deals/<int:pk>/tasks/', created, {'title': 'Call HR', 'due': day(0)}),
        ('PATCH', 'api/tasks/<int:pk>/', everyone, {'done': True}),
        ('DELETE', 'api/tasks/<int:pk>/', gone),
    ]  # fmt: skip
    check_permissions(actors, ['agenda'], matrix, samples(world), no_csrf_api)


@pytest.mark.parametrize(
    ('method', 'path'),
    [
        ('get', '/api/deals/{big}/agenda/'),
        ('get', '/api/deals/{big}/journey/'),
        ('get', '/api/clients/{big}/agenda/'),
        ('get', '/api/clients/999999/agenda/'),
        ('post', '/api/deals/{big}/agenda/marks/'),
        ('delete', '/api/deals/{big}/agenda/marks/import_census/'),
        ('post', '/api/deals/{big}/agenda/follow-ups/'),
        ('post', '/api/deals/{big}/agenda/nudges/1/'),
        ('post', '/api/deals/1/agenda/nudges/{big}/'),
        ('post', '/api/deals/{big}/tasks/'),
        ('patch', '/api/tasks/{big}/'),
        ('delete', '/api/tasks/{big}/'),
        ('get', '/api/deals/999999/agenda/'),
        ('patch', '/api/tasks/999999/'),
    ],
)
def test_Q3_ids_past_bigint_or_unknown_are_404_never_500(api, method, path):
    assert getattr(api, method)(path.format(big=BIG), {}, format='json').status_code == 404


def test_Q3_4_the_agenda_reads_in_the_same_queries_whatever_its_tasks_and_marks(api, user):
    small, big = make_deal(user, name='Small Co.'), make_deal(user, name='Big Co.')
    services.add_task(user, small.id, title='One', due=day(1))
    services.set_later(user, small.id, 'import_census', day(2))
    for n in range(12):
        services.add_task(user, big.id, title=f'Task {n}', due=day(n), assigned_to=user.id)
    for key in ('import_census', 'complete_intake', 'get_bor', 'add_hr_contact'):
        services.set_later(user, big.id, key, day(3))

    def queries(deal):
        with CaptureQueriesContext(connection) as found:
            assert api.get(f'/api/deals/{deal.id}/agenda/').status_code == 200
        return len(found.captured_queries)

    assert queries(small) == queries(big)
