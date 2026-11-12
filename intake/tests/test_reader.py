"""The intake reader (plan.md §5.2, §10.4, §10.5, §10.8; B39's rule, B40, D60, D61, D72–D74, D112; slice 51), run inline
with the fake client on a synthetic company document: it waits in Intake's review, lands answers as Claude's with their
file and page, never writes over what a person stands behind, and ↶ Undo this run puts it all back."""

import hashlib

import pytest
from rest_framework.exceptions import ValidationError

import synthetic_files
from ai import kinds, registry, services
from ai.services.jobs import PHI_OFF
from deals.models import Activity, Contact
from documents.tests.helpers import stored
from intake import reader as intake_reader
from intake.models import CurrentCoverage, Intake
from intake.reader import merge
from intake.services import create_coverage, update_answers

PAGE = [
    'Example Holdings LLC (synthetic) - company profile',
    'FEIN 12-3456789   Employees: 48',
    'Medical: Example Health Plan, fully insured, renews 01/01/2027',
    'Benefits contact: Jordan Example, HR Manager, jordan@example.com',
]


def field(key, value, page=1, unsure=False):
    return {'key': key, 'value': value, 'page': page, 'cell': '', 'unsure': unsure}


ANSWER = {
    'fields': [
        field('legal_name', 'Example Holdings LLC'),
        field('fein', '12-3456789'),
        field('total_employees', '48', unsure=True),
    ],
    'coverage': [
        {
            'line': 'medical',
            'carrier': 'Example Health Plan',
            'funding': 'fully_insured',
            'renewal_date': '01/01/2027',
            'page': 1,
        }
    ],
    'contacts': [
        {
            'name': 'Jordan Example',
            'title': 'HR Manager',
            'email': 'jordan@example.com',
            'phone': '',
            'role': 'hr_admin',
        }
    ],
}


def _read(user, deal, fake, answer=ANSWER, kind='other'):
    raw = synthetic_files.text_pdf(PAGE)
    document = stored(user, deal, 'company profile (synthetic).pdf', raw, kind=kind)
    fake.record(('intake', hashlib.sha256(raw).hexdigest()[:16], 'p1'), answer)
    job, _ = services.start_read(user, deal, [document.id], target='intake')
    job.refresh_from_db()
    return job, document


def _items(job):
    return {item['id']: item for item in job.result['items']}


def test_B40_D112_a_company_document_waits_in_intakes_review(user, deal, fake_claude):
    job, _document = _read(user, deal, fake_claude)
    assert job.status == kinds.DONE and job.land == 'staged' and services.landing.waiting(job)
    items = _items(job)
    assert items['answer:legal_name']['new'] == 'Example Holdings LLC' and items['answer:legal_name']['tick']
    assert not items['answer:total_employees']['tick'] and 'not sure' in items['answer:total_employees']['why']
    assert items['coverage:medical']['coverage'] is None and items['contact:1']['role'] == 'hr_admin'
    assert not Intake.objects.filter(deal=deal).exists() and not Contact.objects.filter(client=deal.client).exists()
    assert job.result['summary'] == '3 intake answers · 1 coverage line · 1 contact'


def test_B40_use_this_scan_lands_answers_as_claudes_with_their_file_and_page(user, deal, fake_claude):
    job, document = _read(user, deal, fake_claude)
    job, landed = services.apply(user, job.id)
    intake = Intake.objects.get(deal=deal)
    assert intake.answers['legal_name'] == 'Example Holdings LLC' and 'total_employees' not in intake.answers
    entry = intake.sources['fein']
    assert entry['origin'] == 'ai' and entry['doc'] == document.id and entry['page'] == 1
    assert entry['read_value'] == '12-3456789'
    row = CurrentCoverage.objects.get(deal=deal, line='medical')
    assert row.carrier == 'Example Health Plan' and row.renewal_date.isoformat() == '2027-01-01'
    assert Contact.objects.get(client=deal.client).email == 'jordan@example.com'
    assert 'items' not in job.result and landed['summary'] == '2 intake answers · 1 coverage line · 1 contact'
    read_row = Activity.objects.get(pk=landed['activity_id'])
    assert read_row.area == 'intake' and read_row.action == 'read'


def test_B39_an_answer_a_person_typed_is_left_alone_unless_ticked(user, deal, fake_claude):
    update_answers(user, deal.id, {'legal_name': 'Example Holdings, Inc.'})
    job, _document = _read(user, deal, fake_claude)
    item = _items(job)['answer:legal_name']
    assert not item['tick'] and 'typed by a person' in item['why'] and item['old'] == 'Example Holdings, Inc.'
    services.apply(user, job.id)
    assert Intake.objects.get(deal=deal).answers['legal_name'] == 'Example Holdings, Inc.'
    second, _document = _read(user, deal, fake_claude)
    services.apply(user, second.id, select=['answer:legal_name'])
    assert Intake.objects.get(deal=deal).answers['legal_name'] == 'Example Holdings LLC'


def test_D60_an_answer_already_on_the_deal_is_not_listed(user, deal, fake_claude):
    update_answers(user, deal.id, {'fein': '12-3456789'})
    job, _document = _read(user, deal, fake_claude)
    assert 'answer:fein' not in _items(job)


def test_B40_an_existing_coverage_line_takes_only_what_it_lacks(user, deal, fake_claude):
    create_coverage(user, deal.id, {'line': 'medical', 'carrier': 'Typed Carrier'})
    job, _document = _read(user, deal, fake_claude)
    item = _items(job)['coverage:medical']
    assert [value['key'] for value in item['values']] == ['funding', 'renewal_date'] and item['coverage']
    services.apply(user, job.id)
    row = CurrentCoverage.objects.get(deal=deal, line='medical')
    assert row.carrier == 'Typed Carrier' and row.funding == 'fully_insured'


def test_D73_undo_this_run_puts_back_answers_coverage_and_contacts(user, deal, fake_claude):
    job, _document = _read(user, deal, fake_claude)
    services.apply(user, job.id)
    job, changed = services.undo(user, job.id)
    assert changed and job.resolution == 'undone'
    intake = Intake.objects.get(deal=deal)
    assert 'legal_name' not in intake.answers and 'fein' not in intake.sources
    assert not CurrentCoverage.objects.filter(deal=deal).exists()
    assert not Contact.objects.filter(client=deal.client).exists()


def test_D73_undo_is_refused_after_a_later_edit_and_undo_anyway_keeps_it(user, deal, fake_claude):
    job, _document = _read(user, deal, fake_claude)
    services.apply(user, job.id)
    update_answers(user, deal.id, {'fein': '98-7654321'})
    with pytest.raises(services.landing.UndoRefused):
        services.undo(user, job.id)
    job, _changed = services.undo(user, job.id, force=True)
    assert Intake.objects.get(deal=deal).answers['fein'] == '98-7654321'
    assert job.result['landed']['undone']['skipped']


def test_B40_a_later_reading_that_differs_flags_the_first():
    class File:
        id, order = 3, 0

    class Part:
        pages = (1,)

    merged = merge.merge(
        [
            (File, Part, {'fields': [field('fein', '12-3456789')]}),
            (File, Part, {'fields': [field('fein', '12-0000000')]}),
        ],
        [File],
    )
    assert merged['fields']['fein']['value'] == '12-3456789' and merged['fields']['fein']['low'] == merge.CONFLICT


def test_D17_intake_files_are_read_only_from_the_intake_tab(user, deal, fake_claude, settings):
    settings.ANTHROPIC_API_KEY = ''
    document = stored(user, deal, 'invoice (synthetic).pdf', synthetic_files.text_pdf(PAGE), kind='invoice')
    sent, not_read = services.start_send(user, deal, [document.id], tab='documents')
    assert sent == [] and not_read == [document.id]
    fake_claude.record(('intake', hashlib.sha256(synthetic_files.text_pdf(PAGE)).hexdigest()[:16], 'p1'), ANSWER)
    sent, not_read = services.start_send(user, deal, [document.id], tab='intake')
    assert [job.target for job, _made in sent] == ['intake'] and not not_read


@pytest.fixture
def switch_off(settings):
    settings.AI_PHI_READERS = False
    registry.readers.pop('intake', None)
    yield
    settings.AI_PHI_READERS = True
    intake_reader.register()


def test_PHI7_the_intake_reader_waits_for_the_phi_gate_switch(user, deal, fake_claude, switch_off):
    assert intake_reader.register() is False and 'intake' not in registry.readers
    document = stored(user, deal, 'profile (synthetic).pdf', synthetic_files.text_pdf(PAGE), kind='other')
    with pytest.raises(ValidationError) as refused:
        services.start_read(user, deal, [document.id], target='intake')
    assert refused.value.detail['target'] == [PHI_OFF]
    assert services.start_send(user, deal, [document.id], tab='intake') == ([], [document.id])


def test_PHI7_with_the_switch_on_the_intake_reader_is_registered(settings):
    settings.AI_PHI_READERS = True
    assert intake_reader.register() is True and registry.readers['intake'].must_review
