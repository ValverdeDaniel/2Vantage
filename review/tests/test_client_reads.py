"""Reads started by a client's upload (plan.md §7.14, §10.4; D44, D45, L111, L125, L135; OQ89; Q.9 row 59): a census
or intake file a client uploads is read with no person ("Client portal") and staged for a person; the Board's To review
lane shows a row per staged read until staff apply it; a paper questionnaire and every other file are only filed; the
upload never fails because of its read; the portal never sees a read. All data is synthetic; Claude is the fake."""

import hashlib
import json
import logging
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

import synthetic_files
from ai import kinds, registry
from ai.models import Job
from ai.services.jobs import CLIENT_PORTAL
from ai.services.landing import waiting
from census import reader as census_reader
from census import services as census
from census.models import CensusImport, Member
from deals import clock
from deals.models import Activity
from documents.models import Document
from intake.models import Intake
from review.portal import payload as portal_payload
from review.services import client_adds, client_reads

from .portal_world import client, make_request, url

pytestmark = pytest.mark.django_db

ROSTER = (
    b'First Name,Last Name,Relationship,Date of Birth,Gender,Zip Code,Medical Tier\r\n'
    b'Quillanova,Synthwright,Employee,01/02/1980,F,33601,Employee Only\r\n'
    b'Avery,Example,Employee,03/04/1975,M,33602,Family\r\n'
    b'Kit,Example,Spouse,05/06/1977,F,,\r\n'
)
CANARIES = ('Quillanova', 'Synthwright', '01/02/1980', '1980-01-02')
INVOICE = ['Example Holdings LLC (synthetic) - medical invoice', 'FEIN 12-3456789   Employees: 48']
INVOICE_ANSWER = {
    'fields': [{'key': 'fein', 'value': '12-3456789', 'page': 1, 'cell': '', 'unsure': False}],
    'coverage': [],
    'contacts': [],
}


def _send(token, slot, name, content):
    return client().post(url(token, 'files/'), {'slot': slot, 'file': SimpleUploadedFile(name, content)})


def _census_upload(user, deal, capture, name='Synthwright Quillanova census.csv'):  # named after its people
    _link, token, _pin = make_request(user, deal, {'census': {'file': True}})
    with capture(execute=True):
        answer = _send(token, 'census_file', name, ROSTER)
    assert answer.status_code == 201, answer.content
    return token, Document.objects.get(deal=deal, slot='census_file')


def _board(api, deal):
    answer = api.get(f'/api/deals/{deal.id}/review/board/')
    assert answer.status_code == 200, answer.content
    return answer.json()


def _read_rows(board):
    return [row for row in board['lanes']['to_review'] if row['key'].startswith('read:')]


def test_D44_L111_a_clients_census_file_is_read_by_no_one_and_staged_for_a_person(
    user, deal, fake_claude, django_capture_on_commit_callbacks
):
    _token, document = _census_upload(user, deal, django_capture_on_commit_callbacks)
    job = Job.objects.get(deal=deal)
    assert (job.kind, job.target, job.lane, job.documents) == (kinds.READ, 'census', kinds.WORK, [document.id])
    assert job.created_by is None and job.actor_label == CLIENT_PORTAL
    assert job.status == kinds.DONE and job.land == 'staged' and waiting(job)
    imp = CensusImport.objects.get(job=job)
    assert imp.status == CensusImport.PROPOSED and imp.document_id == document.id
    assert Member.all_objects.filter(deal=deal).count() == 0  # the roster waits for a person (B16 fixed)
    assert fake_claude.log == []  # a spreadsheet in our columns is mapped here: nothing went to Claude


def test_L135_the_board_shows_the_staged_read_until_staff_apply_its_import(
    api, user, deal, fake_claude, django_capture_on_commit_callbacks
):
    _token, _document = _census_upload(user, deal, django_capture_on_commit_callbacks)
    job = Job.objects.get(deal=deal)
    imp = CensusImport.objects.get(job=job)
    board = _board(api, deal)
    [row] = _read_rows(board)
    assert row['key'] == f'read:{job.id}' and row['section'] == 'Census'
    assert row['label'] == 'Their census file was read' and row['action'] == 'Review and apply ▸'
    assert row['fix'] == {'tab': 'census', 'params': {'import': imp.id}}
    files = next(row for row in board['lanes']['to_review'] if row['key'] == 'documents')
    assert board['counts']['to_review'] == files['count'] + 1  # the file to check and the read to apply
    census.apply_import(user, imp.id)
    assert Member.objects.filter(deal=deal).count() == 3
    job.refresh_from_db()
    assert job.resolution == 'applied'
    after = _board(api, deal)
    assert _read_rows(after) == [] and after['counts']['to_review'] == files['count']


def test_OQ89_an_intake_file_from_the_client_is_read_and_waits_for_intake_review(
    api, user, deal, fake_claude, django_capture_on_commit_callbacks
):
    raw = synthetic_files.text_pdf(INVOICE)
    fake_claude.record(('intake', hashlib.sha256(raw).hexdigest()[:16], 'p1'), INVOICE_ANSWER)
    _link, token, _pin = make_request(user, deal, {'documents': {'slots': ['invoice@medical']}})
    with django_capture_on_commit_callbacks(execute=True):
        assert _send(token, 'invoice@medical', 'invoice (synthetic).pdf', raw).status_code == 201
    job = Job.objects.get(deal=deal)
    assert (job.target, job.actor_label, job.created_by) == ('intake', CLIENT_PORTAL, None) and waiting(job)
    assert not Intake.objects.filter(deal=deal).exclude(answers={}).exists()  # nothing lands until a person uses it
    [row] = _read_rows(_board(api, deal))
    assert row['section'] == 'Intake' and row['label'] == 'Their current invoice was read'
    assert row['fix'] == {'tab': 'intake', 'params': {'claude': '1'}}


def test_OQ89_a_paper_questionnaire_and_a_renewal_are_only_filed(user, deal, fake_claude):
    def filed(kind, slot):
        return Document(deal=deal, kind=kind, slot=slot, source='client')

    assert client_reads.target_of(filed('census', 'census_file')) == 'census'
    assert client_reads.target_of(filed('invoice', 'invoice@medical')) == 'intake'
    assert client_reads.target_of(filed('questionnaire', 'qform:fl_blue_51')) == ''  # filed, read on a click (G101)
    assert client_reads.target_of(filed('renewal', 'renewal@medical')) == ''  # the quote reader waits for a person
    assert client_reads.target_of(filed('claims', 'claims')) == ''
    assert client_reads.target_of(Document(deal=deal, kind='census', source='staff')) == ''


@pytest.fixture
def switch_off(settings):
    settings.AI_PHI_READERS = False
    registry.readers.pop('census', None)
    yield
    settings.AI_PHI_READERS = True
    census_reader.register()


def test_PHI7_with_the_phi_gate_switch_off_a_clients_census_file_is_only_filed(
    user, deal, fake_claude, switch_off, django_capture_on_commit_callbacks
):
    _census_upload(user, deal, django_capture_on_commit_callbacks)
    assert not Job.objects.filter(deal=deal).exists()


def test_D44_the_upload_stands_whatever_its_read_does(
    user, deal, fake_claude, monkeypatch, caplog, django_capture_on_commit_callbacks
):
    def broken(*_args, **_kwargs):
        raise RuntimeError('census (synthetic).csv could not be read')

    monkeypatch.setattr(client_reads, 'start_client_read', broken)
    with caplog.at_level(logging.WARNING):
        _token, document = _census_upload(user, deal, django_capture_on_commit_callbacks)
    assert document.source == 'client' and not Job.objects.filter(deal=deal).exists()
    assert 'RuntimeError' in caplog.text and 'synthetic' not in caplog.text  # the class only, never a name (rule 10)


def test_D44_without_claude_set_up_a_clients_file_is_only_filed(user, deal, django_capture_on_commit_callbacks):
    _census_upload(user, deal, django_capture_on_commit_callbacks)
    assert not Job.objects.filter(deal=deal).exists()


def test_L111_B17_files_of_a_kind_join_the_read_waiting_to_start_and_one_running_starts_the_next(
    settings, user, deal, fake_claude, django_capture_on_commit_callbacks
):
    settings.AI_JOBS_INLINE = False  # the worker's queue, as on the server
    link, _token, _pin = make_request(user, deal, {'census': {'file': True}})

    def upload(name):
        with django_capture_on_commit_callbacks(execute=True):
            return client_adds.upload(link.id, 'census_file', SimpleUploadedFile(name, ROSTER))

    first, second = upload('first.csv'), upload('second.csv')
    [job] = Job.objects.filter(deal=deal)
    assert job.status == kinds.QUEUED and job.documents == [first.id, second.id]  # one read per kind
    Job.objects.filter(pk=job.pk).update(status=kinds.RUNNING, started_at=clock.now(), heartbeat_at=clock.now())
    third = upload('third.csv')
    queued = Job.objects.get(deal=deal, status=kinds.QUEUED)
    assert queued.documents == [third.id] and queued.actor_label == CLIENT_PORTAL  # never left unread (old B17)


def test_D45_the_portal_shows_no_read_and_never_reaps_one(user, deal):
    _link, token, _pin = make_request(user, deal, {'census': {'file': True}})
    silent = clock.now() - timedelta(hours=1)
    job = Job.objects.create(
        deal=deal, lane=kinds.WORK, kind=kinds.READ, target='census', status=kinds.RUNNING,
        actor_label=CLIENT_PORTAL, started_at=silent, heartbeat_at=silent,
    )  # fmt: skip
    api = client()
    body = api.get(url(token)).json()
    stamp = api.get(url(token, 'stamp/'))
    assert stamp.status_code == 200 and set(stamp.json()) == {'form_stamp', 'days_left'}
    assert tuple(body) == portal_payload.KEYS and CLIENT_PORTAL not in json.dumps(body)
    job.refresh_from_db()
    assert job.status == kinds.RUNNING and job.resolution == ''  # only the worker's reaper ends a silent job


def test_L125_the_board_lists_the_clients_files_with_the_reader_each_would_start(
    api, user, deal, fake_claude, django_capture_on_commit_callbacks
):
    slots = ['renewal@medical', 'claims']
    _link, token, _pin = make_request(user, deal, {'census': {'file': True}, 'documents': {'slots': slots}})
    with django_capture_on_commit_callbacks(execute=True):
        _send(token, 'census_file', 'census (synthetic).csv', ROSTER)
    _send(token, 'renewal@medical', 'renewal (synthetic).pdf', synthetic_files.text_pdf(['Renewal (synthetic)']))
    _send(token, 'claims', 'claims (synthetic).pdf', synthetic_files.text_pdf(['Claims (synthetic)']))
    row = next(row for row in _board(api, deal)['lanes']['to_review'] if row['key'] == 'documents')
    assert row['count'] == 3 and row['files_more'] == 0
    labels = [file['label'] for file in row['files']]
    assert labels == ['Claims experience report', 'Renewal / rates — Medical', 'Census file']  # newest first
    files = {file['label']: file for file in row['files']}
    assert (files['Renewal / rates — Medical']['reader'], files['Renewal / rates — Medical']['read']) == ('quotes', '')
    assert (files['Claims experience report']['reader'], files['Claims experience report']['read']) == ('', '')
    assert (files['Census file']['reader'], files['Census file']['read']) == ('census', 'waiting')
    assert 'synthetic' not in json.dumps(row)  # never a file's name: often the people's (§3.8)
    census.apply_import(user, CensusImport.objects.get(deal=deal).id)
    row = next(row for row in _board(api, deal)['lanes']['to_review'] if row['key'] == 'documents')
    assert {file['label']: file['read'] for file in row['files']}['Census file'] == 'used'


def test_Q8_a_clients_census_read_names_no_one_outside_the_census(
    api, user, deal, fake_claude, django_capture_on_commit_callbacks
):
    _census_upload(user, deal, django_capture_on_commit_callbacks)
    job = Job.objects.get(deal=deal)
    said = json.dumps([job.result, job.steps, job.error, _board(api, deal)], default=str)
    said += json.dumps(list(Activity.objects.filter(deal=deal).values('summary', 'changes')), default=str)
    assert not [canary for canary in CANARIES if canary.lower() in said.lower()]
