"""Card 1's pure rules (plan.md §8.6; M42–M60, M67, M108–M110; `overview.gtm`): the badge and "N of M requirements
met", the groups in the old order and when each is met, the counts the old card printed (891f1b3
`GetToMarketCard.jsx`), the census ask, and the client's questionnaire answers waiting (slice 58, through the
overview read)."""

import pytest

from overview import gtm
from questionnaire.selectors import portal
from questionnaire.services import client as questionnaire_client
from questionnaire.tests.world import make_world
from review import services as review_services

LABELS = {'cobra': 'COBRA', 'renewal': 'Renewal', 'invoice': 'Invoice', 'claims': 'Claims'}


def row(key, **over):
    base = {
        'key': key, 'label': LABELS.get(key, key), 'detail': '', 'satisfy': 'document', 'kind': key,
        'has_document': False, 'attested': False, 'note': '', 'done': False, 'waived': False, 'auto_waived': False,
        'forced': False, 'optional': False, 'client_note': '', 'status': 'missing', 'form_key': '', 'form_source': '',
        'signed': False, 'needed': True,
    }  # fmt: skip
    return {**base, **over}


def intake(items, *, state='blocked', gaps=(), contacts_ok=True, bor=True, census_ok=False, answered=0, needed=0,
           intent=None, lines=('medical',)):  # fmt: skip
    return {
        'checklist': {'items': items, 'tier': 'small', 'tier_label': '11–50 enrolled'},
        'ready': {
            'state': state,
            'gaps': [{'kind': 'question', 'key': key, 'label': label} for key, label in gaps],
            'contacts_ok': contacts_ok,
            'bor_on_file': bor,
            'census_ok': census_ok,
        },
        'readiness': {'answered': answered, 'needed': needed},
        'intent': intent or {'rows': [], 'stale': False, 'confirmed_by': ''},
        'marketed': None,
        'requested_lines': list(lines),
    }


def facts(found, **over):
    base = gtm.Facts(
        intake=found, census={}, pending={}, forms={}, form_labels={}, headcount={}, check={}, quotes=0, refusal=None
    )
    return base._replace(**over)


def group(card, key):
    return next(found for found in card['groups'] if found['key'] == key)


def test_M42_the_badge_and_the_rollup_count_the_groups_met_in_the_old_order():
    items = [row('coverage_intent', satisfy='auto', done=True), row('cobra', satisfy='attest'), row('renewal')]
    card = gtm.card(facts(intake(items, state='ready')))
    assert (card['badge'], card['badge_label']) == ('ready', 'Ready to market')
    assert [found['key'] for found in card['groups']] == ['coverage', 'intake', 'census', 'documents', 'confirmations']
    assert [found['title'] for found in card['groups']][:3] == [
        'Coverage & marketing intent',
        'Intake answers',
        'Census',
    ]
    assert (card['met'], card['required']) == (2, 5)  # coverage confirmed; intake has nothing missing
    assert card['tier_label'] == '11–50 enrolled'
    assert gtm.card(facts(intake(items, state='blocked')))['badge_label'] == 'Blocked'


def test_M43_quotes_first_shows_only_while_the_deal_is_blocked():
    items = [row('renewal')]
    assert gtm.card(facts(intake(items), quotes=3))['quotes_first'] == gtm.QUOTES_FIRST
    assert gtm.card(facts(intake(items), quotes=0))['quotes_first'] is None
    assert gtm.card(facts(intake(items, state='ready'), quotes=3))['quotes_first'] is None


def test_M45_the_coverage_group_reads_the_intent_rows_and_who_confirmed_them():
    rows = [
        {'line': 'medical', 'label': 'Medical', 'shopping': True, 'in_force': True, 'on_proposal': True,
         'rate_guarantee_through': None},
        {'line': 'dental', 'label': 'Dental', 'shopping': False, 'in_force': False, 'on_proposal': True,
         'rate_guarantee_through': '2027-06-30'},
    ]  # fmt: skip
    item = row('coverage_intent', satisfy='auto', done=True)
    found = group(gtm.card(facts(intake([item], intent={'rows': rows, 'confirmed_by': 'Dana'}))), 'coverage')
    assert found['count'] == '1 of 2 shopping' and found['met'] is True and found['confirmed_by'] == 'Dana'
    assert found['lines'][1] == {'line': 'dental', 'label': 'Dental', 'shopping': False, 'in_force': False,
                                 'on_proposal': True, 'guaranteed_to': '2027-06-30'}  # fmt: skip


def test_M46_the_intake_group_is_met_by_the_answers_the_hr_contact_and_the_bor():
    gaps = [('fein', 'FEIN')]
    found = group(gtm.card(facts(intake([], gaps=gaps, answered=7, needed=8), pending={'intake': 2})), 'intake')
    assert (found['met'], found['count'], found['missing']) == (False, '7/8 answered', ['FEIN'])
    assert found['pending_client'] == 2 and found['lines'] == 1
    assert group(gtm.card(facts(intake([], contacts_ok=False))), 'intake')['met'] is False
    assert group(gtm.card(facts(intake([], bor=False))), 'intake')['met'] is False
    assert group(gtm.card(facts(intake([], answered=8, needed=8))), 'intake')['met'] is True


def test_M48_M67_M110_the_census_group_counts_the_roster_and_says_when_typed_counts_price_it():
    stored = {'employees': 12, 'dependents': 5, 'required_total': 40, 'required_filled': 31, 'errors': 2}
    check = {'warning': 'Enrolled: intake 42 · census 12 · Advisor 41 — the band uses the Advisor, 41.'}
    found = group(gtm.card(facts(intake([], census_ok=True), census=stored, check=check, pending={'census': 3})),
                  'census')  # fmt: skip
    assert found['met'] is True and found['count'] == '12 EEs + 5 deps'
    assert (found['required_filled'], found['required_total'], found['errors']) == (31, 40, 2)
    assert found['pending_client'] == 3 and found['enrollment_warning'] == check['warning']
    assert found['typed_counts'] is None
    typed = group(gtm.card(facts(intake([]), headcount={'count': 41, 'source': 'advisor'})), 'census')
    assert typed['typed_counts'] == gtm.TYPED_COUNTS


def test_M49_the_census_ask_is_the_roster_lane_or_the_file_and_closes_with_the_deals_asks():
    assert group(gtm.card(facts(intake([]), census={'employees': 4})), 'census')['ask'] == 'roster'
    assert group(gtm.card(facts(intake([]))), 'census')['ask'] == 'file'
    assert group(gtm.card(facts(intake([]), refusal='This deal is lost.')), 'census')['ask'] is None


def test_M50_M108_the_questionnaire_group_counts_the_answers_and_names_its_form():
    item = row('medical_questionnaire', form_key='fl_blue_51', form_source='band')
    forms = {'medical_questionnaire': {'started': True, 'progress': {'filled': 4, 'total': 10}}}
    found = group(gtm.card(facts(intake([item]), forms=forms, form_labels={'fl_blue_51': 'Florida Blue 51+'})),
                  'questionnaire')  # fmt: skip
    assert found['count'] == '4/10 answered' and found['met'] is False
    assert found['item']['form_detail'] == 'Florida Blue 51+ · auto by group size · 4/10 answered'
    unstarted = group(gtm.card(facts(intake([{**item, 'form_source': 'producer'}]))), 'questionnaire')
    assert unstarted['count'] == 'Not started'
    assert unstarted['item']['form_detail'] == 'fl_blue_51 · chosen by you · not started'
    assert group(gtm.card(facts(intake([row('medical_questionnaire')]))), 'questionnaire')['count'] == 'Upload only'
    waived = row('medical_questionnaire', waived=True)
    assert group(gtm.card(facts(intake([waived]))), 'questionnaire')['count'] == 'Not needed'
    assert group(gtm.card(facts(intake([waived]))), 'questionnaire')['met'] is True


def test_M56_the_stop_loss_offer_is_optional_and_never_holds_the_card_back():
    offer = row('stop_loss_disclosure', optional=True, status='offer', needed=False)
    found = group(gtm.card(facts(intake([offer]))), 'stop_loss')
    assert (found['count'], found['offer'], found['met']) == ('Optional', True, True)
    picked = row('stop_loss_disclosure', form_key='stop_loss_siia', form_source='producer')
    armed = group(gtm.card(facts(intake([picked]), form_labels={'stop_loss_siia': 'SIIA'})), 'stop_loss')
    assert (armed['count'], armed['offer'], armed['met']) == ('Not started', False, False)
    assert armed['item']['form_detail'] == 'SIIA · chosen by you · not started'


def test_M57_M60_documents_and_confirmations_count_what_is_not_waived():
    items = [
        row('renewal', done=True, has_document=True, status='done'),
        row('invoice', waived=True, auto_waived=True, status='waived'),
        row('claims'),
        row('cobra', satisfy='attest', done=True, attested=True, status='done'),
    ]
    card = gtm.card(facts(intake(items)))
    documents, confirmations = group(card, 'documents'), group(card, 'confirmations')
    assert (documents['count'], documents['met']) == ('1/2 received', False)
    assert [item['key'] for item in documents['items']] == ['renewal', 'invoice', 'claims']
    assert (confirmations['count'], confirmations['met']) == ('1/1', True)
    assert 'confirmations' not in [found['key'] for found in gtm.card(facts(intake(items[:3])))['groups']]


@pytest.mark.django_db
def test_S58_M50_the_questionnaire_group_counts_the_clients_answers_waiting_for_review(api, user):
    """A real client answer: the form asked online on a link, two answers saved through it (slice 58), and Card 1's
    questionnaire group reads them from review's `pending.questionnaire`; intake's own count is not theirs."""
    form = 'fl_blue_51'
    deal = make_world(user)
    body = {'asks': {'questionnaires': [{'form': form, 'mode': 'online'}]}, 'people': [{'name': 'Casey (synthetic)'}]}
    link = review_services.create(user, deal.id, body).links[0][0]

    def card():
        found = api.get(f'/api/deals/{deal.id}/overview/').json()['get_to_market']
        return group(found, 'questionnaire'), group(found, 'intake')

    assert card()[0]['pending_client'] == 0
    lv = portal.link_view(deal, form, link.id)
    answers = {'txtRsnBid': 'Renewal Increase', 'chkFBPrior': 'No'}
    sent = {slot: {'value': value, 'base': portal.base_of(lv, slot)} for slot, value in answers.items()}
    assert not questionnaire_client.save_client(deal.id, link.id, form, sent).conflicts
    questionnaire, intake_group = card()
    assert questionnaire['pending_client'] == 2 and intake_group['pending_client'] == 0
