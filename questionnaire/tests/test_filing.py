"""The signed copy and the downloads (G135, G50, G56, G61–G63): the officer's signature files a protected copy that
refuses Remove, downloads that copy, keeps it through a reopen; an agent signature after the lock files a fresh one;
every download of the filled form is logged and the blank is not; the server names the files."""

import pytest

from deals import activity
from deals.models import Activity
from documents import services as documents
from documents.models import Document
from questionnaire import services
from questionnaire.models import Questionnaire
from questionnaire.pdf import fonts

from .pdfs import drawn
from .world import make_world

pytestmark = pytest.mark.django_db
FL, SIIA = 'fl_blue_51', 'stop_loss_siia'
REQUIRED = {
    'dteAnnivDate': '2027-04-01',
    'chkFBPrior': 'No',
    'txtRsnBid': 'Renewal Increase',
    'chkMedCon': 'No',
    'txtgrprepname': 'Pat Sample',
}


@pytest.fixture
def signed(user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, REQUIRED)
    services.sign(user, deal.id, FL, 'officer', 'Pat Sample', authorized=True)
    return deal


def test_G135_the_officers_signature_files_a_protected_copy_that_refuses_remove(user, api, signed):
    row = Questionnaire.objects.get(deal=signed, form=FL)
    document = row.signed_document
    assert document.protected and document.kind == 'questionnaire' and document.deal_id == signed.id
    assert row.signed_copies == [{'document': document.id, 'who': 'officer', 'at': row.signed_copies[0]['at'],
                                  'by': user.id}]  # fmt: skip
    with document.file.open('rb') as handle:
        assert drawn(handle.read(), 'Pat Sample')
    with pytest.raises(activity.Refused):
        documents.archive(user, document.id)
    assert api.post(f'/api/documents/{document.id}/archive/').status_code == 409
    signing = Activity.objects.get(deal=signed, area='questionnaire', action='signed')
    assert signing.document_id == document.id and 'filed in Documents' in signing.summary


def test_G135_signed_downloads_are_the_filed_copy_and_it_survives_a_reopen(user, api, signed):
    document = Questionnaire.objects.get(deal=signed, form=FL).signed_document
    with document.file.open('rb') as handle:
        filed = handle.read()
    answer = api.get(f'/api/deals/{signed.id}/questionnaires/{FL}/pdf/')
    assert answer.status_code == 200 and b''.join(answer.streaming_content) == filed
    services.reopen(user, signed.id, FL, 'A typo in the address')
    row = Questionnaire.objects.get(deal=signed, form=FL)
    assert row.signed_document is None and Document.objects.filter(pk=document.id, protected=True).exists()
    again = api.get(f'/api/deals/{signed.id}/questionnaires/{FL}/pdf/')
    assert drawn(b''.join(again.streaming_content), fonts.DRAFT_NOTE)  # open again: a draft


def test_G50_an_agent_signature_after_the_officers_files_a_fresh_copy(user, signed):
    first = Questionnaire.objects.get(deal=signed, form=FL).signed_document
    services.sign(user, signed.id, FL, 'agent', 'Dana Agent')
    row = Questionnaire.objects.get(deal=signed, form=FL)
    assert row.signed_document != first and [c['who'] for c in row.signed_copies] == ['officer', 'agent']
    with row.signed_document.file.open('rb') as handle:
        assert drawn(handle.read(), 'Dana Agent')


def test_G135_an_agent_signing_first_files_nothing(user):
    deal = make_world(user)
    services.sign(user, deal.id, FL, 'agent', 'Dana Agent')
    assert not Document.objects.filter(deal=deal).exists()


def test_G135_the_disclosure_files_as_a_stop_loss_document(user):
    deal = make_world(user, lines=('medical', 'stop_loss'))
    services.choose_form(user, deal.id, 'stop_loss_disclosure', SIIA)
    services.set_answers(user, deal.id, SIIA, {'no_risks': 'Yes'})
    services.sign(user, deal.id, SIIA, 'officer', 'Pat Sample', authorized=True)
    document = Questionnaire.objects.get(deal=deal, form=SIIA).signed_document
    assert document.kind == 'stop_loss' and document.protected


def test_G63_G62_downloads_are_logged_and_named_by_the_server(user, api):
    deal = make_world(user)
    base = f'/api/deals/{deal.id}/questionnaires/{FL}/'
    answer = api.get(base + 'pdf/')
    assert answer.status_code == 200 and answer['Content-Type'] == 'application/pdf'
    assert (
        answer['Content-Disposition']
        == 'attachment; filename="example-fabrication-synthetic-medical-questionnaire.pdf"'
    )
    logged = Activity.objects.get(deal=deal, action='downloaded')
    assert logged.area == 'questionnaire' and logged.summary == 'Downloaded the Florida Blue 51+ PDF (draft)'
    preview = api.get(base + 'pdf/', {'inline': '1'})
    assert preview['Content-Disposition'].startswith('inline') and 'sandbox' in preview['Content-Security-Policy']
    assert Activity.objects.filter(deal=deal, action='viewed').count() == 1
    before = Activity.objects.filter(deal=deal).count()
    blank = api.get(base + 'blank/')
    assert (
        blank.status_code == 200 and blank['Content-Disposition'] == 'attachment; filename="florida-blue-51-blank.pdf"'
    )
    assert b''.join(blank.streaming_content).startswith(b'%PDF')
    assert Activity.objects.filter(deal=deal).count() == before  # the blank carries nobody's data


def test_G61_every_form_downloads_its_blank(api, user):
    deal = make_world(user)
    for form, name in ((FL, 'florida-blue-51'), ('wp_lg', 'warner-pacific-51'), (SIIA, 'stop-loss-disclosure-siia')):
        answer = api.get(f'/api/deals/{deal.id}/questionnaires/{form}/blank/')
        assert answer.status_code == 200 and answer['Content-Disposition'] == f'attachment; filename="{name}-blank.pdf"'


def test_G135_G11_a_reopened_form_is_not_done_by_its_earlier_filed_copy(user, signed):
    from intake.selectors import intake_payload

    def item():
        rows = intake_payload(signed)['checklist']['items']
        return next(r for r in rows if r['key'] == 'medical_questionnaire')

    assert item()['done']
    services.reopen(user, signed.id, FL, 'A typo in the address')
    assert Document.objects.filter(deal=signed, protected=True).exists() and not item()['done']
