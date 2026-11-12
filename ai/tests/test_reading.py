"""The read job (plan.md §10.4; D46, D49–D51, D53, D65, D91, D105; Q.6's request-side checks; slice 18), run inline
with the fake client and a small test reader, so these tests need no owner's reader. Synthetic files only."""

import base64
import hashlib
import io
import json

import pytest

import synthetic_files
from ai import kinds, pricing, registry, services
from ai.models import Call
from ai.registry import Reader
from documents.tests.helpers import stored

TARGET = 'commission_statement'  # no owner registers it in this build: free for a test reader
HEADER, FOOTER = 'Example Health · 2027 renewal', 'Confidential: rates are monthly.'
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['n'], 'properties': {'n': {'type': 'integer'}}}


def packet(pages=3):
    """A cover, rate pages, then a page carrying only the running header and footer."""
    body = [[HEADER, 'Dear partner, your renewal follows.', FOOTER]]
    body += [[HEADER, f'Gold PPO {n} Employee only $512.{n:02d}', FOOTER] for n in range(1, pages - 1)]
    body.append([HEADER, FOOTER])
    return synthetic_files.text_pdf(*body)


def build(deal, user, merged, files, extra):
    return {
        'items': [{'id': 'i1', 'op': 'test', 'tick': True, 'parts': merged}] if merged else [],
        'summary': f'{len(merged)} parts',
        'documents': [f.id for f in files],
        **extra,
    }


@pytest.fixture
def reader():
    entry = Reader(
        target=TARGET,
        kinds=('renewal', 'quote'),
        prompt='Read the test file.',
        schema=SCHEMA,
        version=1,
        note=lambda file, context: f'Filed as {file.kind}.',
        merge=lambda parts, files: [[part.label, data['n']] for _file, part, data in parts],
        build_changes=build,
    )
    registry.readers[TARGET] = entry
    yield entry
    registry.readers.pop(TARGET, None)


def key(raw, label):
    return (TARGET, hashlib.sha256(raw).hexdigest()[:16], label)


def read(user, deal, document, **options):
    job, _ = services.start_read(user, deal, [document.id], target=TARGET, **options)
    job.refresh_from_db()
    return job


def test_Q6_requests_are_messages_with_structured_output_and_one_cached_prompt(user, deal, reader, fake_claude):
    raw = packet()
    document = stored(user, deal, 'renewal.pdf', raw, kind='renewal')
    fake_claude.record(key(raw, 'p1-2'), {'n': 7})
    job = read(user, deal, document)
    assert job.status == kinds.DONE and job.land == 'staged' and job.result['items'][0]['parts'] == [['p1-2', 7]]
    params = fake_claude.log[0]['params']
    assert params['max_tokens'] == 128_000 and params['output_config']['format'] == {
        'type': 'json_schema',
        'schema': SCHEMA,
    }
    assert params['model'] == pricing.SONNET and 'betas' not in params
    sent = base64.b64decode(params['messages'][0]['content'][0]['source']['data'])
    from pypdf import PdfReader

    assert len(PdfReader(io.BytesIO(sent)).pages) == 2  # the header-only page is never sent
    assert job.result['left_out_pages'] == [{'doc': document.id, 'pages': [3], 'why': ['header']}]


def test_Q6_the_prompt_and_schema_are_the_same_bytes_for_every_deal(user, deal, reader, fake_claude):
    from conftest import make_deal

    other = make_deal(user, name='Other Co.')
    raw = packet()
    fake_claude.record(key(raw, 'p1-2'), {'n': 1})
    read(user, deal, stored(user, deal, 'a.pdf', raw, kind='renewal'))
    read(user, other, stored(user, other, 'b.pdf', raw, kind='renewal'))
    first, second = (entry['params'] for entry in fake_claude.log)
    assert json.dumps(first['system']) == json.dumps(second['system'])
    assert json.dumps(first['output_config']) == json.dumps(second['output_config'])


def test_Q6_OQ22_flagged_pages_are_left_out_only_with_the_screen_switch_on(user, deal, reader, fake_claude, settings):
    raw = packet(pages=4)
    document = stored(user, deal, 'renewal.pdf', raw, kind='renewal')
    document.screen = {**(document.screen or {}), 'left_out_pages': [2]}
    document.save(update_fields=['screen'])
    fake_claude.record(key(raw, 'p1-3'), {'n': 1}).record(key(raw, 'p1'), {'n': 1}).record(key(raw, 'p3'), {'n': 2})
    settings.AI_MEMBER_DATA_SCREEN = False
    assert read(user, deal, document).result['items'][0]['parts'] == [['p1-3', 1]]
    settings.AI_MEMBER_DATA_SCREEN = True
    job = read(user, deal, document)
    assert job.result['items'][0]['parts'] == [['p1', 1], ['p3', 2]]
    assert {'doc': document.id, 'pages': [2, 4], 'why': ['header', 'member_data']} in job.result['left_out_pages']


def test_D50_a_cut_off_answer_halves_its_range(user, deal, reader, fake_claude):
    raw = packet(pages=4)
    document = stored(user, deal, 'renewal.pdf', raw, kind='renewal')
    fake_claude.record(key(raw, 'p1-3'), fault='truncate').record(key(raw, 'p1'), {'n': 1})
    fake_claude.record(key(raw, 'p2-3'), {'n': 2})
    job = read(user, deal, document)
    assert job.result['items'][0]['parts'] == [['p1', 1], ['p2-3', 2]]
    assert Call.objects.filter(job=job).count() == 3  # the cut-off call is recorded and priced too


def test_D91_a_refusal_tries_opus_once_for_a_direct_person_only(user, admin_user, deal, reader, fake_claude):
    raw = packet()
    document = stored(user, deal, 'renewal.pdf', raw, kind='renewal')
    fake_claude.record(key(raw, 'p1-2'), {'n': 3}, fault='refusal', fault_on=pricing.SONNET)
    refused = read(user, deal, document)
    assert refused.status == kinds.FAILED and refused.error == 'Claude could not read these files.'
    job = read(admin_user, deal, document)
    assert job.status == kinds.DONE and [c['params']['model'] for c in fake_claude.log[-2:]] == [
        pricing.SONNET,
        pricing.OPUS,
    ]
    assert job.usage['calls'] == 2


@pytest.mark.parametrize(('fault', 'reason'), [('silent', 'error'), ('bad_json', 'error'), ('account', 'account')])
def test_D105_a_failed_part_is_named_and_the_rest_kept(user, deal, reader, fake_claude, fault, reason):
    raw = packet(pages=4)
    document = stored(user, deal, 'renewal.pdf', raw, kind='renewal')
    fake_claude.record(key(raw, 'p1-3'), {'n': 1}, fault=fault)
    job = read(user, deal, document)
    assert job.status == kinds.FAILED and job.error
    assert Call.objects.get(job=job).status == Call.FAILED


def test_D105_stop_while_the_stream_runs_records_the_call_as_stopped(user, deal, reader, fake_claude, monkeypatch):
    monkeypatch.setattr('ai.progress.BEAT_SECONDS', 0)  # every stream event looks at Stop
    raw = packet()
    document = stored(user, deal, 'renewal.pdf', raw, kind='renewal')
    holder = {}

    def press_stop():
        services.cancel(user, holder['job'].id)

    fake_claude.record(key(raw, 'p1-2'), {'n': 1}, during=press_stop)
    from ai.models import Job

    original = Job.objects.create

    def remember(**fields):
        holder['job'] = original(**fields)
        return holder['job']

    Job.objects.create = remember
    try:
        job = read(user, deal, document)
    finally:
        Job.objects.create = original
    assert job.status == kinds.CANCELLED and job.resolution == 'stopped'
    assert Call.objects.get(job=job).status == Call.STOPPED


def test_D53_a_read_estimated_past_its_cap_waits_and_calls_nothing(
    user, admin_user, deal, reader, fake_claude, settings
):
    settings.AI_READ_LIMIT_USD = '0.001'
    raw = packet()
    document = stored(user, deal, 'renewal.pdf', raw, kind='renewal')
    fake_claude.record(key(raw, 'p1-2'), {'n': 1})
    job = read(user, deal, document)
    assert job.status == kinds.DONE and job.land == 'budget' and 'run it anyway' in job.wait_reason
    assert fake_claude.log == [] and not Call.objects.exists()
    with pytest.raises(Exception) as refused:
        read(user, deal, document, budget_override=True)
    assert getattr(refused.value, 'status_code', None) == 409
    assert read(admin_user, deal, document, budget_override=True).land == 'staged'


def test_D53_the_total_cap_stops_a_read_before_its_call(user, deal, reader, fake_claude, settings):
    settings.AI_TOTAL_BUDGET_USD = '0.50'
    raw = packet()
    document = stored(user, deal, 'renewal.pdf', raw, kind='renewal')
    fake_claude.record(key(raw, 'p1-2'), {'n': 1})
    job = read(user, deal, document)
    assert job.status == kinds.FAILED and job.error.startswith('Claude was not called')
    assert fake_claude.log == [] and not Call.objects.exists()


def test_D105_steps_errors_and_the_change_set_never_name_the_file(user, deal, reader, fake_claude):
    raw = packet()
    document = stored(user, deal, 'Secret Client renewal.pdf', raw, kind='renewal')
    fake_claude.record(key(raw, 'p1-2'), {'n': 1})
    job = read(user, deal, document)
    said = json.dumps([job.steps, job.result, job.error, job.wait_reason])
    assert 'Secret Client' not in said and all(
        'Secret' not in e['params']['messages'][0]['content'][-1]['text'] for e in fake_claude.log
    )


def test_D28_D74_a_waiting_change_set_is_listed_until_discarded(user, api, deal, reader, fake_claude):
    raw = packet()
    document = stored(user, deal, 'renewal.pdf', raw, kind='renewal')
    fake_claude.record(key(raw, 'p1-2'), {'n': 4})
    job = read(user, deal, document)
    waiting = api.get(f'/api/deals/{deal.id}/ai/').json()['waiting']
    assert [(row['job_id'], row['documents'], row['summary']) for row in waiting] == [
        (job.id, [document.id], '1 parts')
    ]
    answer = api.post(f'/api/ai/jobs/{job.id}/discard/')
    assert answer.status_code == 200 and answer.json()['resolution'] == 'discarded'
    job.refresh_from_db()
    assert 'items' not in job.result and job.result['summary'] == '1 parts'
    assert api.get(f'/api/deals/{deal.id}/ai/').json()['waiting'] == []
    assert api.post(f'/api/ai/jobs/{job.id}/discard/').status_code == 200  # again: nothing changes
    job.resolution = 'applied'
    job.save(update_fields=['resolution'])
    refused = api.post(f'/api/ai/jobs/{job.id}/discard/')
    assert refused.status_code == 409 and 'Undo' in refused.json()['detail']


def test_D39_the_read_door_reads_ints_and_refuses_files_it_does_not_read(api, user, deal, reader, fake_claude):
    census = stored(user, deal, 'people.csv', b'a,b\n1,2\n', kind='census')
    assert api.post(f'/api/deals/{deal.id}/ai/reads/', {'document_ids': ['x']}, format='json').status_code == 400
    refused = api.post(
        f'/api/deals/{deal.id}/ai/reads/', {'document_ids': [census.id], 'target': TARGET}, format='json'
    )
    assert refused.status_code == 400 and 'filed as something else' in refused.json()['document_ids'][0]
    opus = api.post(
        f'/api/deals/{deal.id}/ai/reads/',
        {'document_ids': [census.id], 'target': TARGET, 'model': pricing.OPUS},
        format='json',
    )
    assert opus.status_code in (400, 409)
    assert (
        api.post(f'/api/deals/{deal.id}/ai/reads/', {'document_ids': [1], 'pages': [True]}, format='json').status_code
        == 400
    )


def test_D26_meta_serves_the_ai_section_only_when_claude_is_set_up(api, settings):
    from ai import client

    previous = client.install(None)
    try:
        assert 'ai' not in api.get('/api/meta/').json()
    finally:
        client.install(previous)


def test_D26_D91_meta_names_the_readers_and_the_models(api, fake_claude):
    section = api.get('/api/meta/').json()['ai']
    quotes = {'key': 'quotes', 'kinds': ['quote', 'renewal', 'stop_loss_quote', 'tpa_proposal'], 'waits': False}
    assert quotes in section['targets']  # `waits`: the reader's reads always wait for review (slice 51)
    assert {'key': 'census', 'kinds': ['census'], 'waits': True} in section['targets'] and section['phi_readers']
    assert [model['key'] for model in section['models']] == [pricing.SONNET, pricing.OPUS]
