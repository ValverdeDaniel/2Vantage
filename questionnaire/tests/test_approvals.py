"""A person's decision on the client's questionnaire answers (G69, G70, G73, G81, G135; OQ84, OQ85; slice 58):
approval lands with the client as its source, Keep ours changes nothing but the entry, Undo puts back the value it
replaced, a medical answer reaches Activity as its key only, and a signed form files its copy once the officer's
answers are approved. Links are plain ids; every value is synthetic."""

import pytest

from deals import activity
from deals.models import Activity
from documents.models import Document
from questionnaire import services
from questionnaire.models import Questionnaire
from questionnaire.pdf import build
from questionnaire.selectors import portal
from questionnaire.services import approvals, client

from .test_client import FL, LINK, REQUIRED, send
from .world import make_world

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(user):
    return make_world(user)


def row_of(deal):
    return Questionnaire.objects.get(deal_id=deal.id, form=FL)


def test_G70_approve_lands_the_answer_with_the_client_as_its_source(user, world):
    send(world, {'txtRsnBid': 'Renewal Increase'})
    decided = approvals.approve_client(user, world.id, [(FL, 'txtRsnBid')])
    assert decided.slots == [(FL, 'txtRsnBid')]
    row = row_of(world)
    assert row.answers['txtRsnBid'] == 'Renewal Increase'
    assert row.sources['txtRsnBid']['origin'] == 'client' and row.sources['txtRsnBid']['link'] == LINK
    assert row.client['txtRsnBid']['status'] == 'approved'
    assert build.printed_of(world, FL).scalars['txtRsnBid'] == 'Renewal Increase'  # OQ85: now it prints
    again = approvals.approve_client(user, world.id, [(FL, 'txtRsnBid')])
    assert again.slots == [] and again.activity == []


def test_G70_keep_ours_changes_nothing_but_the_entry(user, world):
    send(world, {'txtRsnBid': 'Renewal Increase'})
    approvals.reject_client(user, world.id, [(FL, 'txtRsnBid')])
    row = row_of(world)
    assert 'txtRsnBid' not in row.answers and row.client['txtRsnBid']['status'] == 'rejected'


def test_G70_undo_puts_back_the_value_the_approval_replaced(user, world):
    services.set_answers(user, world.id, FL, {'txtRsnBid': 'Dissatisfaction with Service'})
    send(world, {'txtRsnBid': 'Renewal Increase'})
    approvals.approve_client(user, world.id, [(FL, 'txtRsnBid')])
    approvals.revert_approval(user, world.id, [(FL, 'txtRsnBid')])
    row = row_of(world)
    assert row.answers['txtRsnBid'] == 'Dissatisfaction with Service' and row.sources['txtRsnBid']['origin'] == 'typed'
    assert row.client['txtRsnBid']['status'] == 'pending'


def test_G70_undo_refuses_after_a_later_edit(user, world):
    send(world, {'txtRsnBid': 'Renewal Increase'})
    approvals.approve_client(user, world.id, [(FL, 'txtRsnBid')])
    services.set_answers(user, world.id, FL, {'txtRsnBid': 'Dissatisfaction with Service'})
    with pytest.raises(activity.Refused):
        approvals.revert_approval(user, world.id, [(FL, 'txtRsnBid')])


def test_G33_an_answer_that_empties_a_prefilled_box_hides_the_prefill_once_approved(user, world):
    shown = portal.shown_value(portal.link_view(world, FL, LINK), 'TextField2')
    assert shown  # the FEIN, live from intake
    send(world, {'TextField2': ''})
    approvals.approve_client(user, world.id, [(FL, 'TextField2')])
    assert 'TextField2' in row_of(world).cleared
    assert not build.printed_of(world, FL).scalars.get('TextField2')


def test_G23_rule4_a_medical_answer_reaches_activity_as_its_key_only(user, world):
    send(world, {'chkMedCon': 'Yes', 'txtRsnBid': 'Renewal Increase'})
    decided = approvals.approve_client(user, world.id, [(FL, 'chkMedCon'), (FL, 'txtRsnBid')])
    rows = Activity.objects.filter(pk__in=[row.id for row in decided.activity])
    text = ' '.join(str(row.changes) + row.summary for row in rows)
    assert 'Renewal Increase' in text  # an ordinary answer keeps before and after
    hidden = [row for row in rows if any(isinstance(entry['k'], list) for entry in row.changes)]
    assert hidden and all('Yes' not in str(row.changes) for row in hidden)


def test_G81_a_changed_answer_takes_the_approval_off_and_waits_again(user, world):
    send(world, {'txtRsnBid': 'Renewal Increase'})
    approvals.approve_client(user, world.id, [(FL, 'txtRsnBid')])
    send(world, {'txtRsnBid': 'Dissatisfaction with Service'})
    row = row_of(world)
    assert row.answers['txtRsnBid'] == 'Renewal Increase'  # stored underneath until reviewed
    entry = row.client['txtRsnBid']
    assert entry['status'] == 'pending' and entry['value'] == 'Dissatisfaction with Service'


def test_G135_OQ85_a_form_signed_on_the_link_files_its_copy_once_its_answers_are_approved(user, world):
    send(world, REQUIRED)
    services.sign_from_link(world.id, LINK, FL, 'Pat Sample')
    waiting = [(FL, slot) for slot in row_of(world).client]
    assert row_of(world).signed_document_id is None
    with pytest.raises(activity.Refused):
        approvals.reject_client(user, world.id, waiting[:1])  # the officer attested them: reopen first
    approvals.approve_client(user, world.id, waiting[:1])
    assert row_of(world).signed_document_id is None or len(waiting) == 1
    approvals.approve_client(user, world.id, waiting)
    row = row_of(world)
    filed = Document.objects.get(pk=row.signed_document_id)
    assert filed.protected and row.locked
    with pytest.raises(activity.Refused):
        approvals.revert_approval(user, world.id, waiting[:1])


def test_G87_approve_lands_an_answer_in_a_row_the_client_added(user, world):
    made = client.add_row(world.id, LINK, FL, 'plans')
    slot = f'plans.{made.row_id}.txtCurrPlanName'
    send(world, {slot: 'Synthetic PPO'})
    approvals.approve_client(user, world.id, [(FL, slot)])
    printed = build.printed_of(world, FL)
    assert any(values.get('txtCurrPlanName') == 'Synthetic PPO' for _n, values in printed.rows['plans'])
