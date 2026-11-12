"""Florida Blue's stamped copy (G57, G19, G53; OQ85): values sit inside their boxes, the first filled row prints when
row 1 is blank (B1), overflow goes to the attachment with real row numbers, hidden answers never print, DRAFT until
signed and then the caption, the officer box falls back to the signed name (B3)."""

import pytest

from questionnaire import services
from questionnaire.forms import fl_blue_51_layout as layout
from questionnaire.models import Questionnaire
from questionnaire.pdf import build, fonts, stamp_place

from .pdfs import drawn, inside, placed, reader
from .world import make_world

pytestmark = pytest.mark.django_db
FL = 'fl_blue_51'
REQUIRED = {
    'dteAnnivDate': '2027-04-01',
    'chkFBPrior': 'No',
    'txtRsnBid': 'Renewal Increase',
    'chkMedCon': 'No',
    'txtgrprepname': 'Pat Sample',
}


def plan_rows(deal):
    return [row['id'] for row in Questionnaire.objects.get(deal=deal, form=FL).rows['plans']]


def test_G57_stamped_values_sit_inside_their_boxes(user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, REQUIRED)
    first = plan_rows(deal)[0]
    services.set_answers(user, deal.id, FL, {f'plans.{first}.numCurrRatePrem': '48200'})
    data = build.build(deal, FL)
    assert len(reader(data).pages) == layout.PAGE_COUNT  # nothing overflows: no attachment
    boxes = layout.FIELD_BOXES
    assert inside(data, boxes['txtCoName'], 'Example Fabrication LLC')
    assert inside(data, boxes['dteAnnivDate'], '04/01/2027')
    assert inside(data, boxes['City'], 'Orlando')
    assert inside(data, boxes['State'], 'Florida')  # the state's full name, as the carrier's own box reads
    assert inside(data, boxes['txtRsnBid'], 'Renewal Increase')
    assert inside(data, boxes['TextField2'], '00-7654321')
    assert inside(data, layout.BLOCK_BOXES['plans']['txtCurrPlanName'], 'BlueOptions 1')
    assert inside(data, layout.BLOCK_BOXES['plans']['numCurrRatePrem'], '$48,200.00')
    assert inside(data, layout.CHECKBOXES['chkFBPrior']['No'], 'X')
    assert not inside(data, layout.CHECKBOXES['chkFBPrior']['Yes'], 'X')


def test_G57_the_stamped_face_is_the_bundled_one_embedded(user):
    deal = make_world(user)
    page = reader(build.build(deal, FL)).pages[0]
    assert any('Arimo' in font for _x, _y, text, font in placed(page) if text == 'Example Fabrication LLC')
    faces = [ref.get_object() for ref in page['/Resources']['/Font'].values()]
    arimo = next(face for face in faces if 'Arimo' in str(face.get('/BaseFont')))
    assert '/FontFile2' in arimo['/FontDescriptor'].get_object()


def test_G57_B1_row_two_prints_when_row_one_is_blank_and_more_rows_go_to_the_attachment(user):
    deal = make_world(user, plans=0)
    services.set_answers(user, deal.id, FL, REQUIRED)
    services.add_row(user, deal.id, FL, 'plans')
    services.add_row(user, deal.id, FL, 'plans')
    _blank, second, third = plan_rows(deal)
    services.set_answers(user, deal.id, FL, {f'plans.{second}.txtCurrPlanName': 'Second Example PPO'})
    data = build.build(deal, FL)
    assert inside(data, layout.BLOCK_BOXES['plans']['txtCurrPlanName'], 'Second Example PPO')
    assert len(reader(data).pages) == layout.PAGE_COUNT
    services.set_answers(user, deal.id, FL, {f'plans.{third}.txtCurrPlanName': 'Third Example HMO'})
    data = build.build(deal, FL)
    attachment = reader(data).pages[layout.PAGE_COUNT :]
    assert attachment and 'Plan 3' in attachment[0].extract_text()  # its number on our form, not "Plan 2"
    assert 'Third Example HMO' in attachment[0].extract_text()


def test_G57_an_answer_too_long_for_its_box_points_to_the_attachment(user):
    long_name = 'Example ' * 24 + 'Fabrication LLC'
    deal = make_world(user, answers={'legal_name': long_name})
    data = build.build(deal, FL)
    assert inside(data, layout.FIELD_BOXES['txtCoName'], stamp_place.SEE_ATTACHMENT)
    assert len(reader(data).pages) > layout.PAGE_COUNT
    assert 'Example Example Example' in reader(data).pages[layout.PAGE_COUNT].extract_text()


def test_G57_question_12s_explanation_rides_its_reason_box(user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, {'txtRsnBid': 'Other', 'txtRsnBidComments': 'Broker change'})
    data = build.build(deal, FL)
    assert inside(data, layout.FIELD_BOXES['txtRsnBid'], 'Other — Broker change')


def test_G57_a_category_swaps_the_cancer_counts_for_its_own_lines(user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, {'chkMedCon': 'Yes'})
    services.add_row(user, deal.id, FL, 'conditions')
    row = Questionnaire.objects.get(deal=deal, form=FL).rows['conditions'][0]['id']
    services.set_answers(user, deal.id, FL, {f'conditions.{row}.drpMedCat': 'Transplants'})
    data = build.build(deal, FL)
    assert drawn(data, 'Number of individuals with planned transplants:', page=1)
    assert inside(data, layout.BLOCK_BOXES['conditions']['drpMedCat'], 'Transplants')


def test_G19_hidden_answers_never_print(user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, {'txtCurrentCarrier': 'Example Health'})
    assert inside(build.build(deal, FL), layout.FIELD_BOXES['txtCurrentCarrier'], 'Example Health')
    services.set_answers(user, deal.id, FL, {'chkVirgin': 'No'})  # not replacing coverage: Q13's follow-ups hide
    data = build.build(deal, FL)
    assert not drawn(data, 'Example Health') and not drawn(data, 'BlueOptions 1')


def test_OQ85_a_clients_waiting_answer_never_prints(user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, {'txtAdd2': 'Suite 1'})
    pending = {'value': 'Suite 99', 'link': 7, 'at': '2026-11-12T09:00:00Z', 'status': 'pending'}
    Questionnaire.objects.filter(deal=deal, form=FL).update(client={'txtAdd2': pending})
    data = build.build(deal, FL)
    assert inside(data, layout.FIELD_BOXES['txtAdd2'], 'Suite 1') and not drawn(data, 'Suite 99')


def test_G53_DRAFT_until_the_officer_signs_then_the_typed_name_caption(user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, REQUIRED)
    unsigned = build.build(deal, FL)
    assert drawn(unsigned, fonts.DRAFT_NOTE, page=0) and drawn(unsigned, fonts.DRAFT_NOTE, page=1)
    services.sign(user, deal.id, FL, 'officer', 'Pat Sample', authorized=True)
    signed = build.build(deal, FL)
    assert not drawn(signed, fonts.DRAFT_NOTE)
    assert inside(signed, layout.SIGNATURE_BOXES['officer_sign'], 'Pat Sample')
    caption = next(text for _x, _y, text, _f in placed(reader(signed).pages[1]) if text.startswith(fonts.SIGNED_NOTE))
    assert 'Pat Sample, company officer' in caption


def test_G57_B3_the_officer_box_falls_back_to_the_signed_name(user):
    deal = make_world(user, contact=False)  # no contact: no officer to prefill
    services.set_answers(user, deal.id, FL, {key: v for key, v in REQUIRED.items() if key != 'txtgrprepname'})
    services.sign(user, deal.id, FL, 'officer', 'Riley Officer', authorized=True, sign_anyway=True)
    assert inside(build.build(deal, FL), layout.FIELD_BOXES['txtgrprepname'], 'Riley Officer')


def test_Q3_G53_a_signature_at_9pm_eastern_prints_that_days_date():
    from datetime import UTC, datetime

    assert fonts.signed_on(datetime(2026, 11, 13, 2, 0, tzinfo=UTC)) == '11/12/2026'  # 21:00 EST on the 12th
