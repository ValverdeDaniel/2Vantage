"""The ai API (plan.md §7.5) and its Q.3 contracts: the state GET writes nothing and runs the same queries however many
jobs a deal has; every endpoint has a permission row; ids are read as ints."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from ai import kinds
from ai.models import DealAi, Job
from conftest import check_permissions, sweep_gets
from documents.tests.helpers import stored


@pytest.fixture
def world(user, deal):
    document = stored(user, deal, name='renewal.pdf', kind='renewal')
    waiting = Job.objects.create(deal=deal, lane=kinds.WORK, kind=kinds.RANK, created_by=user)
    return {'deal': deal, 'document': document, 'job': waiting}


def samples(world):
    deal, job = world['deal'], world['job']
    return {
        'api/deals/<int:pk>/ai/': {'pk': deal.id},
        'api/deals/<int:pk>/ai/locate/': {'pk': deal.id},
        'api/ai/jobs/<int:job_id>/': {'job_id': job.id},
        'api/ai/jobs/<int:job_id>/cancel/': {'job_id': job.id},
    }


ALL = {'signed_out': 401, 'producer': 200, 'admin': 200}


def matrix(world):
    started = {'signed_out': 401, 'producer': 201, 'admin': 201}
    return [
        ('GET', 'api/deals/<int:pk>/ai/', ALL),
        ('POST', 'api/deals/<int:pk>/ai/locate/', started, {'document_ids': [world['document'].id]}),
        ('GET', 'api/ai/jobs/<int:job_id>/', ALL),
        ('POST', 'api/ai/jobs/<int:job_id>/cancel/', ALL),
    ]


def test_Q3_ai_gets_write_nothing(admin_api, world):
    sweep_gets(admin_api, ('ai',), samples(world))
    assert not DealAi.objects.exists()  # the state's defaults come without a row


def test_Q3_ai_permission_matrix(actors, no_csrf_api, world):
    check_permissions(actors, ('ai',), matrix(world), samples(world), no_csrf_api)


def _state_queries(api, deal):
    with CaptureQueriesContext(connection) as queries:
        assert api.get(f'/api/deals/{deal.id}/ai/').status_code == 200
    return len(queries.captured_queries)


def test_Q3_D105_the_state_runs_the_same_queries_for_one_job_or_ten(api, user, deal):
    Job.objects.create(deal=deal, lane=kinds.WORK, kind=kinds.RANK, created_by=user)
    one = _state_queries(api, deal)
    for n in range(9):
        Job.objects.create(deal=deal, lane=kinds.SYSTEM, kind=kinds.LOCATE, created_by=user, params={'n': n})
    assert _state_queries(api, deal) == one


def test_D105_the_state_lists_jobs_waiting_running_and_just_finished(api, user, deal, world):
    other = Job.objects.create(deal=deal, lane=kinds.WORK, kind=kinds.RANK, created_by=user, params={'n': 2})
    body = api.get(f'/api/deals/{deal.id}/ai/').json()
    assert [(job['id'], job['status'], job['queue_position']) for job in body['jobs']] == [
        (world['job'].id, kinds.QUEUED, 1),
        (other.id, kinds.QUEUED, 2),
    ]
    assert body['jobs'][0]['created_by']['id'] == user.id and body['recent'] == []
    assert (body['lock'], body['waiting'], body['spend']['usd'], body['claude']) == (None, [], '0.00', False)
    api.post(f'/api/ai/jobs/{other.id}/cancel/')
    body = api.get(f'/api/deals/{deal.id}/ai/').json()
    assert [job['id'] for job in body['jobs']] == [world['job'].id]
    assert [(job['id'], job['status']) for job in body['recent']] == [(other.id, kinds.CANCELLED)]


def test_E59_check_this_file_answers_the_job(api, deal, world, settings):
    url = f'/api/deals/{deal.id}/ai/locate/'
    body = {'document_ids': [world['document'].id]}
    done = api.post(url, body, format='json')
    assert done.status_code == 201
    assert (done.json()['kind'], done.json()['status'], done.json()['lane']) == ('locate', 'done', 'system')
    settings.AI_JOBS_INLINE = False
    queued = api.post(url, body, format='json')
    again = api.post(url, body, format='json')
    assert (queued.status_code, again.status_code) == (201, 200)
    assert again.json()['id'] == queued.json()['id']  # the same check, already waiting


@pytest.mark.parametrize('ids', ['5', [True], ['x'], [0], [2**64], None])
def test_E59_check_this_file_reads_ids_as_ints(api, deal, ids):
    assert api.post(f'/api/deals/{deal.id}/ai/locate/', {'document_ids': ids}, format='json').status_code == 400


def test_D105_one_job_answers_with_an_etag(api, world):
    url = f'/api/ai/jobs/{world["job"].id}/'
    first = api.get(url)
    assert first.status_code == 200 and first.json()['steps'] == []
    assert api.get(url, HTTP_IF_NONE_MATCH=first['ETag']).status_code == 304
    api.post(f'{url}cancel/')
    assert api.get(url, HTTP_IF_NONE_MATCH=first['ETag']).status_code == 200


def test_D105_stop_on_a_finished_job_answers_409_with_a_sentence(api, user, deal):
    finished = Job.objects.create(deal=deal, lane=kinds.WORK, kind=kinds.RANK, status=kinds.DONE)
    answer = api.post(f'/api/ai/jobs/{finished.id}/cancel/')
    assert answer.status_code == 409 and 'already finished' in answer.json()['detail']


def test_Q3_ids_past_bigint_answer_404(api):
    assert api.get(f'/api/deals/{2**64}/ai/').status_code == 404
    assert api.get(f'/api/ai/jobs/{2**64}/').status_code == 404
    assert api.post(f'/api/ai/jobs/{2**64}/cancel/').status_code == 404
