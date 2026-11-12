"""What the RFP sends of the questionnaire (G110–G113) and the stop-loss Binding Notes' state (G117): who takes each
form, the disclosure's funding gate, which copy goes, the two-copy warning, "changed since", and `disclosure_state`."""

import pytest

from documents.models import Document
from questionnaire import forms, rfp_rules, services
from questionnaire.selectors import rfp
from quotes import providers
from synthetic_files import text_pdf

from .world import make_world

pytestmark = pytest.mark.django_db
FL, WP, SIIA = 'fl_blue_51', 'wp_lg', 'stop_loss_siia'


@pytest.mark.parametrize(
    'form, carrier, taken',
    [
        (FL, 'florida_blue', True), (FL, 'aetna', False), (FL, None, False),
        (WP, 'aetna', True), (WP, 'florida_blue', False), (WP, None, True),
        (SIIA, 'aetna', True), (SIIA, 'florida_blue', True), (SIIA, None, False),
    ],
)  # fmt: skip
def test_G112_who_takes_each_form(form, carrier, taken):
    assert rfp_rules.takes(forms.FORMS[form], carrier) is taken


def test_G112_the_disclosure_never_goes_to_an_ancillary_carrier():
    from deals.carriers import ANCILLARY, CARRIERS

    ancillary = next(c['key'] for c in CARRIERS if c['group'] == ANCILLARY)
    assert not rfp_rules.takes(forms.FORMS[SIIA], ancillary)


@pytest.mark.parametrize(
    'lines, funding, needed',
    [
        (['medical'], ['fully_insured'], False), (['medical'], ['level_funded'], True),
        (['medical'], ['fully_insured', 'aso'], True), (['medical', 'stop_loss'], ['fully_insured'], True),
        ([], [], False),
    ],
)  # fmt: skip
def test_G112_the_disclosure_rides_only_on_stop_loss_level_funded_or_aso_requests(lines, funding, needed):
    assert rfp_rules.disclosure_needed(lines, funding) is needed


def test_G110_the_signed_copy_else_an_accepted_paper_copy_else_the_draft_with_a_warning():
    paper = [{'id': 9, 'review_state': ''}, {'id': 8, 'review_state': 'accepted'}]
    assert rfp_rules.copy_to_send(41, paper) == {'copy': 'signed', 'document': 41, 'warning': ''}
    assert rfp_rules.copy_to_send(None, paper) == {'copy': 'paper', 'document': 8, 'warning': ''}
    draft = rfp_rules.copy_to_send(None, [{'id': 9, 'review_state': ''}])
    assert draft['copy'] == 'draft' and draft['document'] is None and draft['warning']


def test_G110_two_ticked_copies_of_one_form_warn():
    one = {'form': FL, 'label': 'Medical questionnaire'}
    assert rfp_rules.two_copies([one, {'form': SIIA, 'label': 'Stop-loss disclosure'}]) == []
    assert rfp_rules.two_copies([one, one]) == ['Two copies of the Medical questionnaire are ticked: send one.']


def test_G110_G111_the_cards_default_ticks_and_their_reasons(user):
    deal = make_world(user, lines=('medical', 'stop_loss'))
    services.choose_form(user, deal.id, 'stop_loss_disclosure', SIIA)
    cards = {
        c['form']: c for c in rfp.rfp_files(deal, carriers=['aetna'], lines=['medical'], funding=['fully_insured'])
    }
    assert cards[FL]['include'] is False and cards[FL]['reason'] == rfp.NOT_TAKEN
    assert cards[SIIA]['include'] is False and cards[SIIA]['reason'] == rfp.NOT_ASKED
    assert cards[FL]['copy'] == 'draft' and cards[FL]['warning']
    cards = {c['form']: c for c in rfp.rfp_files(deal, carriers=['florida_blue'], funding=['level_funded'])}
    assert (
        cards[FL]['include'] and cards[SIIA]['include'] and cards[FL]['label'] == 'Medical questionnaire — Florida Blue'
    )


def test_G110_a_wrong_paper_copy_never_goes_and_an_accepted_one_does(user):
    from documents.services import store_bytes

    deal = make_world(user)
    paper = store_bytes(user, deal, 'paper.pdf', text_pdf('A filled form'), 'questionnaire', 'Paper copy')
    Document.objects.filter(pk=paper.id).update(review_state='wrong')  # review's mark (slice 53)
    card = next(c for c in rfp.rfp_files(deal) if c['form'] == FL)
    assert card['paper'] == [] and card['copy'] == 'draft'
    Document.objects.filter(pk=paper.id).update(review_state='accepted')
    card = next(c for c in rfp.rfp_files(deal) if c['form'] == FL)
    assert (card['copy'], card['document'], card['paper']) == ('paper', paper.id, [paper.id])


def test_G113_changed_since_compares_the_printed_values_then_the_signed_copy(user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, {'txtAdd2': 'Suite 1'})
    sent = rfp.sent_with(deal, FL)
    assert 'hash' in sent and not rfp.changed_since(deal, FL, sent)
    services.set_answers(user, deal.id, FL, {'txtAdd2': 'Suite 2'})
    assert rfp.changed_since(deal, FL, sent)
    services.sign(user, deal.id, FL, 'officer', 'Pat Sample', authorized=True, sign_anyway=True)
    signed = rfp.sent_with(deal, FL)
    assert signed['document'] and not rfp.changed_since(deal, FL, signed)
    services.sign(user, deal.id, FL, 'agent', 'Dana Agent')  # a fresh copy is filed
    assert rfp.changed_since(deal, FL, signed)


def test_G117_the_disclosure_state_for_the_binding_notes(user):
    deal = make_world(user, lines=('medical', 'stop_loss'))
    assert providers.disclosure_state(deal.id) == 'not_started'
    services.choose_form(user, deal.id, 'stop_loss_disclosure', SIIA)
    services.set_answers(user, deal.id, SIIA, {'no_risks': 'Yes'})
    assert providers.DISCLOSURE_WORDS[providers.disclosure_state(deal.id)] == 'SIIA disclosure started, not signed'
    services.sign(user, deal.id, SIIA, 'officer', 'Pat Sample', authorized=True)
    assert providers.DISCLOSURE_WORDS[providers.disclosure_state(deal.id)] == 'SIIA disclosure signed'
