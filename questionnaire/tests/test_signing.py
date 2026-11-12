"""Signatures, Reopen, the choice and the checklist's provider (G2, G4, G9, G11, G27, G49–G55, G133; OQ54, OQ55)."""

import pytest
from rest_framework.exceptions import ValidationError

from deals import activity
from deals.models import Activity
from deals.services import mark_lost
from intake import providers
from intake.models import Intake
from intake.selectors import intake_payload
from questionnaire import services
from questionnaire.models import Questionnaire
from questionnaire.selectors import payload
from questionnaire.services.signing import Incomplete

from .world import make_world, set_enrolled

pytestmark = pytest.mark.django_db
FL = 'fl_blue_51'
REQUIRED = {
    'dteAnnivDate': '2027-04-01',
    'chkFBPrior': 'No',
    'txtRsnBid': 'Renewal Increase',
    'chkMedCon': 'No',
    'txtgrprepname': 'Pat Sample',
}


@pytest.fixture
def world(user):
    return make_world(user)


def sign_officer(user, deal, **kw):
    return services.sign(user, deal.id, FL, 'officer', 'Pat Sample', authorized=True, **kw)


def test_G51_staff_sign_for_the_officer_only_with_written_authorization(user, world):
    with pytest.raises(ValidationError) as refused:
        services.sign(user, world.id, FL, 'officer', 'Pat Sample')
    assert refused.value.detail['code'] == 'authorization_required'
    with pytest.raises(ValidationError):
        services.sign(user, world.id, FL, 'officer', '   ', authorized=True)


def test_G51_blank_required_answers_hold_the_signature_until_sign_anyway(user, world):
    with pytest.raises(Incomplete) as held:
        sign_officer(user, world)
    assert held.value.detail['incomplete']['total'] > held.value.detail['incomplete']['filled']
    assert not Questionnaire.objects.filter(deal=world, officer_signed_at__isnull=False).exists()
    sign_officer(user, world, sign_anyway=True)
    assert Questionnaire.objects.get(deal=world).locked


def test_G52_G27_the_officers_signature_freezes_the_prefill_and_locks_the_form(user, world):
    services.set_answers(user, world.id, FL, REQUIRED)
    signed = sign_officer(user, world)
    row = Questionnaire.objects.get(deal=world)
    assert row.locked and row.officer_name == 'Pat Sample' and row.officer_authorized
    assert row.answers['txtCoName'] == 'Example Fabrication LLC' and row.sources['txtCoName']['origin'] == 'prefill'
    assert 'Pat Sample' in signed.activity.summary and 'written authorization' in signed.activity.summary
    with pytest.raises(activity.Refused):
        services.set_answers(user, world.id, FL, {'txtAdd2': 'Suite 9'})
    with pytest.raises(activity.Refused):
        services.add_row(user, world.id, FL, 'plans')
    with pytest.raises(activity.Refused):
        sign_officer(user, world)  # already on file
    shown = payload.form_payload(world, FL)
    assert shown['locked'] and shown['officer']['name'] == 'Pat Sample'


def test_G50_the_agent_signs_before_or_after_the_lock(user, world):
    services.set_answers(user, world.id, FL, REQUIRED)
    sign_officer(user, world)
    services.sign(user, world.id, FL, 'agent', 'Dana Agent')
    row = Questionnaire.objects.get(deal=world)
    assert row.agent_name == 'Dana Agent' and row.agent_signed_at


def test_G51_a_lost_deal_refuses_a_signature(user, world):
    mark_lost(user, world.id, 'Went with another broker')
    with pytest.raises(activity.Refused) as refused:
        sign_officer(user, world, sign_anyway=True)
    assert 'lost' in refused.value.sentence


def test_G54_OQ55_reopen_needs_a_reason_and_drops_unconfirmed_prefill(user, world):
    services.set_answers(user, world.id, FL, REQUIRED)
    services.mark_answers(user, world.id, FL, 'approve', refs=['questionnaire:fl_blue_51:City'])
    sign_officer(user, world)
    with pytest.raises(ValidationError):
        services.reopen(user, world.id, FL, '  ')
    services.reopen(user, world.id, FL, 'Wrong officer typed')
    row = Questionnaire.objects.get(deal=world)
    assert not row.locked and not row.agent_signed_at and row.reopens[0]['reason'] == 'Wrong officer typed'
    assert 'txtCoName' not in row.answers and row.answers['City'] == 'Orlando'  # the confirmed one stays
    assert 'Wrong officer' not in Activity.objects.filter(action='reopened').get().summary
    with pytest.raises(activity.Refused):
        services.reopen(user, world.id, FL, 'Again')


def test_G11_the_officers_signature_completes_the_checklist_item(user, world):
    items = providers.questionnaire_items(world.id)['medical_questionnaire']
    assert (items['form'], items['source'], items['signed']) == (FL, 'band', False)
    services.set_answers(user, world.id, FL, REQUIRED)
    sign_officer(user, world)
    row = next(r for r in intake_payload(world)['checklist']['items'] if r['key'] == 'medical_questionnaire')
    assert row['done'] and row['form_key'] == FL and row['signed']


def test_G9_a_swap_away_from_a_signed_form_is_refused(user, world):
    services.set_answers(user, world.id, FL, REQUIRED)
    sign_officer(user, world)
    for choice in ('wp_lg', 'upload'):
        with pytest.raises(activity.Refused):
            services.choose_form(user, world.id, 'medical_questionnaire', choice)
    services.choose_form(user, world.id, 'medical_questionnaire', FL)  # Keep is fine
    assert Intake.objects.get(deal=world).checklist['medical_questionnaire']['form_source'] == 'producer'


def test_G2_G4_choices_and_upload_only(user, world):
    services.choose_form(user, world.id, 'medical_questionnaire', 'wp_lg')
    assert [f['key'] for f in payload.deal_forms(world)['forms']] == ['wp_lg']
    services.choose_form(user, world.id, 'medical_questionnaire', 'upload')
    assert payload.deal_forms(world)['forms'] == []
    services.choose_form(user, world.id, 'stop_loss_disclosure', 'upload')
    item = providers.questionnaire_items(world.id)['stop_loss_disclosure']
    assert item['needed'] and not item['form']
    row = next(r for r in intake_payload(world)['checklist']['items'] if r['key'] == 'stop_loss_disclosure')
    assert not row['optional'] and row['status'] == 'missing'  # needed, upload only (N12's fix)
    with pytest.raises(ValidationError):
        services.choose_form(user, world.id, 'stop_loss_disclosure', 'fl_blue_51')
    with pytest.raises(ValidationError):
        services.choose_form(user, world.id, 'nope', 'auto')


def test_G6_a_waiver_or_a_dental_only_deal_asks_for_no_medical_form(user):
    dental = make_world(user, lines=('dental',))
    assert payload.deal_forms(dental)['forms'] == []
    small = make_world(user, enrolled='40')
    assert payload.deal_forms(small)['forms'] == [] and payload.deal_forms(small)['band'] == 'small'


def test_G133_a_later_band_change_never_swaps_a_started_form_and_shows_the_notice(user, world):
    services.set_answers(user, world.id, FL, {'txtAdd2': 'Suite 4'})
    set_enrolled(user, world, 40)
    found = payload.deal_forms(world)
    assert [f['key'] for f in found['forms']] == [FL]
    notice = found['items']['medical_questionnaire']['notice']
    assert notice['text'] == 'Group size now says ≤50' and notice['keep'] == FL and notice['switch'] == 'upload'
    services.choose_form(user, world.id, 'medical_questionnaire', FL)  # Keep
    assert payload.deal_forms(world)['items']['medical_questionnaire']['notice'] is None


def test_G7_a_started_form_keeps_its_chip_after_the_choice_moves_away(user, world):
    services.set_answers(user, world.id, FL, {'txtAdd2': 'Suite 4'})
    services.choose_form(user, world.id, 'medical_questionnaire', 'wp_lg')
    forms_ = payload.deal_forms(world)['forms']
    assert [(f['key'], f['armed'], f['started']) for f in forms_] == [('wp_lg', True, False), (FL, False, True)]
