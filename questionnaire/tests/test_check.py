"""The check before a download (G64–G66): every problem code, the texts naming rows and labels but never an answer,
and a download with a stale `ack` answering 409 with the fresh report."""

import pytest

from questionnaire import services
from questionnaire.check import report
from questionnaire.models import Questionnaire
from questionnaire.selectors import payload

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


def codes(deal, form=FL):
    return [p['code'] for p in report.report(deal, form)['problems']]


def test_G64_an_unstarted_form_says_only_that(user):
    deal = make_world(user)
    found = report.report(deal, FL)
    assert [p['code'] for p in found['problems']] == ['questionnaire_empty'] and not found['ok']
    assert found['problems'][0]['fix'] == {'tab': 'questionnaire', 'form': FL}


def test_G64_blanks_and_the_missing_signature_then_nothing_once_signed(user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, {'txtAdd2': 'Suite 1'})
    found = report.report(deal, FL)['problems']
    assert [p['code'] for p in found] == ['questionnaire_incomplete', 'unsigned']
    blanks = payload.form_payload(deal, FL)['blanks']
    assert found[0]['count'] == len(blanks) > 0 and 'still blank' in found[0]['text']
    services.set_answers(user, deal.id, FL, REQUIRED)
    assert codes(deal) == ['unsigned']
    services.sign(user, deal.id, FL, 'officer', 'Pat Sample', authorized=True)
    assert report.report(deal, FL) | {'ack': ''} == {'form': FL, 'label': 'Florida Blue Underwriting Questionnaire',
                                                     'ok': True, 'problems': [], 'ack': ''}  # fmt: skip


def test_G64_what_the_page_cannot_print(user):
    deal = make_world(user, plans=3, answers={'legal_name': 'Example ' * 24 + 'Fabrication LLC'})
    services.set_answers(user, deal.id, FL, {**REQUIRED, 'drpEEContMethod': 'Percentage',
                                             'numERConPercent': '1234567890123456789012345'})  # fmt: skip
    found = {p['code']: p for p in report.report(deal, FL)['problems']}
    assert found['on_attachment']['count'] == 1 and '1. Name of Business' in found['on_attachment']['text']
    assert found['rows_on_attachment']['count'] == 2 and 'Current plan' in found['rows_on_attachment']['text']
    assert found['clipped']['count'] == 1 and 'Employee %' in found['clipped']['text']
    assert 'Example Example' not in ' '.join(p['text'] for p in found.values())  # never an answer


def test_G64_a_claimant_named_not_identified(user):
    deal = make_world(user, lines=('medical', 'stop_loss'))
    services.choose_form(user, deal.id, 'stop_loss_disclosure', SIIA)
    services.set_answers(user, deal.id, SIIA, {'no_risks': 'No'})
    row = Questionnaire.objects.get(deal=deal, form=SIIA).rows['risks'][0]['id']
    services.set_answers(user, deal.id, SIIA, {f'risks.{row}.risk_identifier': 'Jordan Example'})
    named = next(p for p in report.report(deal, SIIA)['problems'] if p['code'] == 'claimant_name')
    assert 'Risk 1' in named['text'] and 'Jordan' not in named['text'] and named['fix']['view'] == 'review'
    services.set_answers(user, deal.id, SIIA, {f'risks.{row}.risk_identifier': 'J.E. M-10442'})
    assert 'claimant_name' not in codes(deal, SIIA)


def test_G64_what_waits_on_a_person_before_the_signature(user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, REQUIRED)
    row = Questionnaire.objects.get(deal=deal, form=FL)
    sources = {**row.sources, 'txtAdd2': {'origin': 'ai', 'doc': 4, 'page': 1, 'low': 'faint'}}
    pending = {'txtTitleOfficer': {'value': 'Owner', 'link': 7, 'at': '2026-11-12T09:00:00Z', 'status': 'pending'}}
    Questionnaire.objects.filter(pk=row.pk).update(answers={**row.answers, 'txtAdd2': 'Suite 9'}, sources=sources,
                                                   client=pending)  # fmt: skip
    found = {p['code']: p for p in report.report(deal, FL)['problems']}
    assert found['questionnaire_ai_open']['count'] == 1 and found['questionnaire_client_waiting']['count'] == 1


def test_G66_a_download_with_a_stale_ack_answers_409_with_the_fresh_report(api, user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, {'txtAdd2': 'Suite 1'})
    base = f'/api/deals/{deal.id}/questionnaires/{FL}/'
    checked = api.get(base + 'check/').json()
    assert checked['problems'] and checked['ack']
    assert api.get(base + 'pdf/', {'ack': checked['ack']}).status_code == 200
    services.set_answers(user, deal.id, FL, REQUIRED)  # the blanks fill in: the check changed
    stale = api.get(base + 'pdf/', {'ack': checked['ack']})
    assert stale.status_code == 409 and stale.json()['report']['problems'] != checked['problems']
    assert stale.json()['report']['ack'] != checked['ack'] and 'Something changed' in stale.json()['detail']
    fresh = stale.json()['report']['ack']
    assert api.get(base + 'pdf/', {'ack': fresh}).status_code == 200
    assert api.get(base + 'pdf/').status_code == 200  # no ack, no check: the preview's door
