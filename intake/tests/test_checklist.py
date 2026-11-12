"""The marketing checklist's door (plan.md §5.2, §7.6; B26, B27, C25, O.6 #2): one entry per item in
`Intake.checklist`, written through intake's door (the Census tab ticks COBRA through it), recorded and reverted."""

import pytest

from conftest import write_path_contract
from deals import activity
from intake import services
from intake.models import Intake
from intake.selectors import checklist_item

pytestmark = pytest.mark.django_db


def test_Q3_1_C25_the_cobra_tick_is_recorded_and_reverted(user, deal):
    intake = Intake.objects.create(deal=deal)
    row = write_path_contract(
        user,
        intake,
        lambda: services.set_checklist_item(user, deal.id, 'cobra', checked=True),
        lambda found: found.checklist.get('cobra', {}).get('checked', False),
        lambda: services.set_checklist_item(user, deal.id, 'cobra', checked=False),
    )
    assert row.summary == 'Ticked "COBRA participants" on the marketing checklist'
    assert row.changes[0]['t'] == f'checklist:{deal.id}'


def test_Q3_1_B27_a_requirement_is_recorded_and_reverted(user, deal):
    intake = Intake.objects.create(deal=deal)
    row = write_path_contract(
        user,
        intake,
        lambda: services.set_checklist_item(user, deal.id, 'invoice', requirement='waived'),
        lambda found: found.checklist.get('invoice', {}).get('requirement', ''),
        lambda: services.set_checklist_item(user, deal.id, 'invoice', requirement='required', client_note='2027'),
    )
    assert row.summary == 'Marked "Current invoice(s)" not needed on the marketing checklist'


def test_C25_who_and_when_follow_the_tick(user, api, deal):
    url = f'/api/deals/{deal.id}/intake/checklist/'
    assert checklist_item(deal.id, 'cobra')['checked'] is False  # no Intake row yet: unchecked, nothing made
    assert not Intake.objects.filter(deal=deal).exists()
    ticked = api.patch(url, {'item': 'cobra', 'checked': True}, format='json').json()
    assert ticked['item']['checked'] is True and ticked['item']['by_name'] == (user.get_full_name() or user.username)
    assert ticked['item']['at'] and ticked['activity_id']
    again = api.patch(url, {'item': 'cobra', 'checked': True}, format='json').json()
    assert again['activity_id'] is None
    unticked = api.patch(url, {'item': 'cobra', 'checked': False}, format='json').json()['item']
    assert (unticked['checked'], unticked['by_name'], unticked['at']) == (False, '', None)


def test_B27_the_door_answers_the_card_and_the_ready_state(user, api, deal):
    url = f'/api/deals/{deal.id}/intake/checklist/'
    body = api.patch(url, {'item': 'renewal', 'checked': True}, format='json').json()
    row = next(item for item in body['checklist']['items'] if item['key'] == 'renewal')
    assert (row['attested'], row['done'], row['by_name']) == (True, True, user.get_full_name() or user.username)
    assert body['ready']['state'] == 'blocked'
    still = api.patch(
        url, {'item': 'renewal', 'requirement': 'required', 'client_note': 'This year’s, please'}, format='json'
    ).json()
    row = next(item for item in still['checklist']['items'] if item['key'] == 'renewal')
    assert (row['status'], row['forced'], row['attested']) == ('missing', True, True)  # the tick stays under it
    assert row['client_note'] == 'This year’s, please'


def test_B27_a_tick_never_clobbers_a_requirement_and_the_reverse(user, deal):
    services.set_checklist_item(user, deal.id, 'invoice', requirement='required', client_note='Send it')
    services.set_checklist_item(user, deal.id, 'invoice', checked=True)
    entry = Intake.objects.get(deal=deal).checklist['invoice']
    assert (entry['requirement'], entry['client_note'], entry['checked']) == ('required', 'Send it', True)
    services.set_checklist_item(user, deal.id, 'invoice', requirement='')
    assert Intake.objects.get(deal=deal).checklist['invoice'] == {'checked': True, 'by': user.id, 'at': entry['at']}


def test_B27_reverting_a_tick_after_a_later_change_to_the_item_is_refused(user, deal):
    first = services.set_checklist_item(user, deal.id, 'cobra', checked=True).activity
    services.set_checklist_item(user, deal.id, 'cobra', requirement='waived')
    with pytest.raises(activity.Refused):
        activity.revert(first.id, user)


def test_B27_only_an_item_a_person_ticks_and_only_true_or_false(api, deal):
    url = f'/api/deals/{deal.id}/intake/checklist/'
    for body in (
        {'item': 'census', 'checked': True},  # derived: Census OK decides it
        {'item': 'coverage_intent', 'requirement': 'waived'},  # derived: its escape is Market anyway
        {'item': 'cobra', 'checked': 'yes'},
        {'item': 'cobra', 'requirement': 'maybe'},
        {'item': 'cobra'},
        {'item': 'cobra', 'requirement': 'required', 'client_note': 'x' * 301},
    ):
        assert api.patch(url, body, format='json').status_code == 400, body
