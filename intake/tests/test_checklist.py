"""The marketing checklist's ticks (plan.md §5.2, §7.6; B26, B27, C25, O.6 #2): slice 41 brings the COBRA tick, which
the Census tab shows; one entry in `Intake.checklist`, written through intake's door, recorded and reverted."""

import pytest

from conftest import write_path_contract
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


def test_B27_only_an_item_a_person_ticks_and_only_true_or_false(api, deal):
    url = f'/api/deals/{deal.id}/intake/checklist/'
    assert api.patch(url, {'item': 'census', 'checked': True}, format='json').status_code == 400
    assert api.patch(url, {'item': 'cobra', 'checked': 'yes'}, format='json').status_code == 400
