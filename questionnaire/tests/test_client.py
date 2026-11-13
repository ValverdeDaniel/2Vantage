"""The client's side of a questionnaire through a portal link (G51, G55, G86–G88, G93, G136; OQ84, OQ85; slice 58):
answers wait as pending entries, bases guard a stale page, broker fields refuse, rows the link added come off, and the
officer signs on the link. Links are plain ids here (review owns them); every value is synthetic."""

import pytest
from rest_framework.exceptions import ValidationError

from deals import activity
from deals.models import Activity
from questionnaire import services
from questionnaire.models import Questionnaire
from questionnaire.pdf import build
from questionnaire.selectors import portal
from questionnaire.services import client
from questionnaire.services.signing import Incomplete

from .world import make_world

pytestmark = pytest.mark.django_db
FL = 'fl_blue_51'
LINK, OTHER = 9001, 9002
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


def view(deal, link=LINK, **kw):
    return portal.link_view(deal, FL, link, **kw)


def send(deal, answers, link=LINK, **kw):
    """The client's answers {slot: value} with the bases the page read them under."""
    lv = view(deal, link, **kw)
    return client.save_client(
        deal.id, link, FL, {slot: {'value': v, 'base': portal.base_of(lv, slot)} for slot, v in answers.items()}, **kw
    )


def row_of(deal):
    return Questionnaire.objects.get(deal_id=deal.id, form=FL)


def test_G88_OQ84_a_client_answer_waits_and_never_touches_the_form(world):
    saved = send(world, {'txtRsnBid': 'Renewal Increase', 'chkMedCon': 'No'})
    assert set(saved.changed) == {'txtRsnBid', 'chkMedCon'}
    row = row_of(world)
    assert 'txtRsnBid' not in row.answers
    assert row.client['txtRsnBid']['status'] == 'pending' and row.client['txtRsnBid']['link'] == LINK
    # The link shows its own answer; the staff form shows it violet (G136); nothing prints it (OQ85).
    assert portal.state(view(world))['values']['txtRsnBid'] == 'Renewal Increase'
    printed = build.printed_of(world, FL)
    assert 'txtRsnBid' not in printed.scalars


def test_G88_a_newer_answer_from_any_link_replaces_the_waiting_one(world):
    send(world, {'txtRsnBid': 'Renewal Increase'})
    send(world, {'txtRsnBid': 'Dissatisfaction with Service'}, link=OTHER)
    entry = row_of(world).client['txtRsnBid']
    assert entry['value'] == 'Dissatisfaction with Service' and entry['link'] == OTHER


def test_G88_an_answer_equal_to_what_we_hold_drops_the_waiting_one(world):
    lv = view(world)
    shown = portal.shown_value(lv, 'txtCoName')
    assert shown  # the live prefill (the legal name)
    send(world, {'txtCoName': 'Example Fab (synthetic)'})
    send(world, {'txtCoName': shown})
    assert 'txtCoName' not in row_of(world).client


def test_G88_a_stale_base_is_a_conflict_and_nothing_saves(world):
    stale = portal.base_of(view(world), 'txtRsnBid')
    send(world, {'txtRsnBid': 'Renewal Increase'}, link=OTHER)
    found = client.save_client(
        world.id, LINK, FL,
        {
            'txtRsnBid': {'value': 'Dissatisfaction with Service', 'base': stale},
            'chkMedCon': {'value': 'No', 'base': stale},
        },
    )  # fmt: skip
    assert found.changed == [] and [c['slot'] for c in found.conflicts] == ['txtRsnBid']
    assert 'chkMedCon' not in row_of(world).client


def test_G88_every_refusal_is_named_and_nothing_saves(world):
    with pytest.raises(ValidationError) as refused:
        send(world, {'txtRsnBid': 'Renewal Increase', 'numTAP': 'many', 'chkMedCon': 'Maybe'})
    errors = refused.value.detail['answers']
    assert set(errors) == {'numTAP', 'chkMedCon'}
    assert not Questionnaire.objects.filter(deal_id=world.id, form=FL).exclude(client={}).exists()


def test_G86_a_broker_field_refuses_the_client_and_the_officer_name_takes_it(world):
    with pytest.raises(ValidationError) as refused:
        send(world, {'txtagentname': 'Someone Else'})
    assert refused.value.detail['answers']['txtagentname'] == client.BROKER
    send(world, {'txtgrprepname': 'Robin Example'})
    assert row_of(world).client['txtgrprepname']['status'] == 'pending'
    assert 'txtagentname' in portal.state(view(world))['broker']


def test_G79_a_staff_edit_closes_a_waiting_answer_as_replaced(user, world):
    send(world, {'txtRsnBid': 'Renewal Increase'})
    services.set_answers(user, world.id, FL, {'txtRsnBid': 'Dissatisfaction with Service'}, relay=True)
    assert row_of(world).client['txtRsnBid']['status'] == 'replaced'


def test_G87_a_client_removes_only_a_row_its_link_added(user, world):
    made = client.add_row(world.id, LINK, FL, 'plans')
    row = row_of(world)
    entry = row.rows['plans'][-1]
    assert entry == {**entry, 'id': made.row_id, 'origin': 'client', 'link': LINK}
    with pytest.raises(activity.Refused):
        client.remove_row(world.id, OTHER, FL, 'plans', made.row_id)
    first = row.rows['plans'][0]['id']
    with pytest.raises(activity.Refused):
        client.remove_row(world.id, LINK, FL, 'plans', first)  # the deal's own plan row
    slot = f'plans.{made.row_id}.txtCurrPlanName'
    send(world, {slot: 'Synthetic PPO'})
    client.remove_row(world.id, LINK, FL, 'plans', made.row_id)
    row = row_of(world)
    assert made.row_id not in [r['id'] for r in row.rows['plans']] and slot not in row.client


def test_G87_a_row_holding_an_approved_answer_stays(user, world):
    from questionnaire.services import approvals

    made = client.add_row(world.id, LINK, FL, 'plans')
    slot = f'plans.{made.row_id}.txtCurrPlanName'
    send(world, {slot: 'Synthetic PPO'})
    approvals.approve_client(user, world.id, [(FL, slot)])
    with pytest.raises(activity.Refused):
        client.remove_row(world.id, LINK, FL, 'plans', made.row_id)


def test_G93_the_officer_signs_on_the_link_held_only_by_blanks(world):
    with pytest.raises(Incomplete) as held:
        services.sign_from_link(world.id, LINK, FL, 'Pat Sample')
    assert held.value.detail['incomplete']['filled'] < held.value.detail['incomplete']['total']
    services.sign_from_link(world.id, LINK, FL, 'Pat Sample', sign_anyway=True)
    row = row_of(world)
    assert row.locked and row.officer_link == LINK and row.officer_signed_by is None and not row.officer_authorized
    signed = Activity.objects.filter(deal=world, area='questionnaire', action='signed').latest('id')
    assert signed.actor_kind == 'client' and 'on their link' in signed.summary


def test_G51_G93_signing_counts_the_clients_own_answers_and_they_still_wait(world):
    send(world, REQUIRED)
    signed = services.sign_from_link(world.id, LINK, FL, 'Pat Sample')
    row = signed.row
    assert row.locked and row.client and all(entry['status'] == 'pending' for entry in row.client.values())
    assert row.signed_document_id is None  # OQ85: the copy waits for the answers it attests
    with pytest.raises(activity.Refused):
        send(world, {'txtRsnBid': 'Dissatisfaction with Service'})  # a signed form takes nothing


def test_G93_a_narrowed_ask_takes_no_signature(world):
    with pytest.raises(ValidationError):
        services.sign_from_link(world.id, LINK, FL, 'Pat Sample', picks={'fields': ['txtRsnBid'], 'blocks': []})


def test_G22_a_narrowed_link_writes_only_what_it_asks(world):
    picks = {'fields': ['txtRsnBid'], 'blocks': []}
    with pytest.raises(ValidationError):
        send(world, {'chkMedCon': 'No'}, picks=picks)
    assert send(world, {'txtRsnBid': 'Renewal Increase'}, picks=picks).changed == ['txtRsnBid']
    assert 'txtRsnBid' in portal.state(view(world, picks=picks))['order']
