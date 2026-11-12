"""Attaching files to Claude and trying a read again (plan.md §8.17, §10.5; D16, D17, D23, D24, D76; Q.9 row 20:
mixed-send order, cost cap and Run anyway), with test readers run by the fake client. Synthetic files only."""

import hashlib

import pytest

import synthetic_files
from ai import kinds, land, pricing, registry, services
from ai.models import Job
from ai.registry import Reader
from ai.testing import run_jobs
from documents.tests.helpers import stored

SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['n'], 'properties': {'n': {'type': 'integer'}}}
RAW = synthetic_files.text_pdf(['Example Health 2027 renewal', 'Gold PPO Employee only $512.34'])
SHEET = synthetic_files.text_pdf(['Example census', 'Employee count 12'])


def build(deal, user, merged, files, extra):
    return {'items': [{'id': 'i1', 'op': 'test', 'tick': True}], 'summary': 'read', 'documents': [f.id for f in files]}


def reader(target, file_kinds, **more):
    return Reader(
        target=target,
        kinds=file_kinds,
        prompt=f'Read the {target} file.',
        schema=SCHEMA,
        version=1,
        note=lambda file, context: 'A test file.',
        merge=lambda parts, files: [data['n'] for _file, _part, data in parts],
        build_changes=build,
        **more,
    )


@pytest.fixture
def readers():
    """Test readers for the census, intake and the plans (only quotes' is real in this build)."""
    saved = dict(registry.readers)
    registry.readers.update(
        census=reader('census', ('census',), must_review=True),
        intake=reader('intake', ('plan_doc',), must_review=True),
        quotes=reader('quotes', ('quote', 'renewal')),
    )
    yield registry.readers
    registry.readers.clear()
    registry.readers.update(saved)


def key(target, raw):
    return (target, hashlib.sha256(raw).hexdigest()[:16], 'p1')


@pytest.fixture
def files(user, deal, fake_claude):
    fake_claude.record(key('quotes', RAW), {'n': 1}).record(key('census', SHEET), {'n': 2})
    fake_claude.record(key('intake', RAW), {'n': 3})
    return {
        'quote': stored(user, deal, 'quote.pdf', RAW, kind='quote'),
        'census': stored(user, deal, 'census.pdf', SHEET, kind='census'),
        'plan_doc': stored(user, deal, 'spd.pdf', RAW, kind='plan_doc'),
        'invoice': stored(user, deal, 'invoice.pdf', RAW, kind='invoice'),
    }


def test_D17_one_send_reads_each_reader_once_census_then_intake_then_the_plans(user, deal, readers, files, settings):
    settings.AI_JOBS_INLINE = False
    ids = [files[kind].id for kind in ('quote', 'invoice', 'plan_doc', 'census')]
    started, not_read = services.start_send(user, deal, ids)
    assert [job.target for job, _created in started] == ['census', 'intake', 'quotes']
    assert not_read == [files['invoice'].id]
    assert [job.documents for job, _ in started] == [[files['census'].id], [files['plan_doc'].id], [files['quote'].id]]
    ran = run_jobs()  # the worker takes them oldest first, one at a time on the deal
    assert [job.target for job in ran] == ['census', 'intake', 'quotes']
    assert all(job.status == kinds.DONE for job in Job.objects.filter(deal=deal))


def test_D16_a_send_while_a_read_runs_queues_behind_it(user, deal, readers, files, settings):
    settings.AI_JOBS_INLINE = False
    first, _ = services.start_read(user, deal, [files['quote'].id])
    Job.objects.filter(pk=first.pk).update(status=kinds.RUNNING)
    job, created = services.start_send(user, deal, [files['census'].id])[0][0]
    assert created and job.status == kinds.QUEUED


def test_D17_the_send_door_reads_ints_and_only_this_deals_files(api, user, deal, readers, files):
    url = f'/api/deals/{deal.id}/ai/sends/'
    answer = api.post(url, {'document_ids': [files['quote'].id]}, format='json')
    assert answer.status_code == 201 and [job['target'] for job in answer.json()['jobs']] == ['quotes']
    from conftest import make_deal

    other = stored(user, make_deal(user, name='Other Co.'), 'other.pdf', RAW, kind='quote')
    assert api.post(url, {'document_ids': [other.id]}, format='json').status_code == 400
    assert api.post(url, {'document_ids': ['x']}, format='json').status_code == 400
    assert api.post(url, {'document_ids': [files['invoice'].id]}, format='json').json() == {
        'jobs': [],
        'not_read': [files['invoice'].id],
    }


def test_D26_a_send_without_a_key_is_refused(api, deal, readers, user):
    document = stored(user, deal, 'quote.pdf', RAW, kind='quote')
    answer = api.post(f'/api/deals/{deal.id}/ai/sends/', {'document_ids': [document.id]}, format='json')
    assert answer.status_code == 409 and answer.json()['detail']


def test_D76_try_again_reads_on_the_next_model_for_admins_and_the_same_for_producers(
    user, admin_user, deal, readers, files, fake_claude
):
    waiting, _ = services.start_read(user, deal, [files['quote'].id])
    again, created = services.retry(user, waiting.id)
    assert created and again.params['retry_of'] == waiting.id and again.params.get('model') == pricing.SONNET
    waiting.refresh_from_db()
    assert waiting.resolution == 'discarded'  # the read it replaces no longer waits
    with pytest.raises(Exception) as refused:
        services.retry(user, again.id, model=pricing.OPUS)
    assert getattr(refused.value, 'status_code', None) == 409
    stepped, _ = services.retry(admin_user, again.id)
    assert stepped.params['model'] == pricing.OPUS and fake_claude.log[-1]['params']['model'] == pricing.OPUS


def test_D76_D73_try_again_on_a_used_read_undoes_it_first(admin_user, deal, files, fake_claude):
    landed = {}

    def apply(user, deal, job, select=None, picks=None):
        from deals import activity

        row = activity.record(deal, user, 'test_read', 'read', 'Used the test read')
        landed[job.id] = row.id
        return {'activity_id': row.id, 'activity_ids': [row.id], 'plan_ids': [], 'areas': [], 'summary': '1'}

    def undo(user, deal, job, force=False):
        landed.pop(job.id)
        return {'reverted': [], 'kept': [], 'skipped': []}

    saved = registry.readers['quotes']
    registry.readers['quotes'] = reader('quotes', ('quote',), apply=apply, undo=undo)
    fake_claude.record(key('quotes', RAW), {'n': 1})
    try:
        first, _ = services.start_read(admin_user, deal, [files['quote'].id])
        first.refresh_from_db()
        assert first.land == land.AUTO and first.id in landed
        again, _ = services.retry(admin_user, first.id)
        first.refresh_from_db()
        assert first.resolution == 'undone' and again.params['retry_of'] == first.id
    finally:
        registry.readers['quotes'] = saved


def test_D24_run_anyway_reads_past_the_cap_for_admins_only(api, admin_api, user, deal, readers, files, settings):
    settings.AI_READ_LIMIT_USD = '0.001'
    over, _ = services.start_read(user, deal, [files['quote'].id])
    over.refresh_from_db()
    assert over.land == 'budget' and 'run it anyway' in over.wait_reason
    state = api.get(f'/api/deals/{deal.id}/ai/').json()
    assert state['recent'][0]['over'] == 'run' and state['can']['opus'] is False
    assert api.post(f'/api/ai/jobs/{over.id}/retry/', {'budget_override': True}, format='json').status_code == 409
    answer = admin_api.post(f'/api/ai/jobs/{over.id}/retry/', {'budget_override': True}, format='json')
    assert answer.status_code == 201 and answer.json()['params']['budget_override'] is True
    assert answer.json()['status'] == kinds.DONE and answer.json()['land'] != 'budget'


def test_D76_a_read_still_going_or_a_job_that_is_no_read_is_not_tried_again(user, deal, readers, files, settings):
    settings.AI_JOBS_INLINE = False
    going, _ = services.start_read(user, deal, [files['quote'].id])
    rank = Job.objects.create(deal=deal, lane=kinds.WORK, kind=kinds.RANK, status=kinds.DONE)
    for job in (going, rank):
        with pytest.raises(Exception) as refused:
            services.retry(user, job.id)
        assert getattr(refused.value, 'status_code', None) == 409


def test_D8_D13_the_state_says_the_budget_the_files_read_and_each_jobs_cost(api, user, deal, readers, files, settings):
    settings.AI_DEAL_BUDGET_USD = 25
    services.start_read(user, deal, [files['quote'].id])
    state = api.get(f'/api/deals/{deal.id}/ai/').json()
    assert state['spend']['budget_usd'] == '25.00' and state['spend']['own_budget'] is False
    assert state['read_documents'] == [files['quote'].id]
    job = state['recent'][0]
    assert (job['model'], job['recent_steps'][-1] != '') == (pricing.SONNET, True) and 'cost_usd' in job
