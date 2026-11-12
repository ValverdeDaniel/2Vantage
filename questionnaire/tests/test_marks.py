"""Questionnaire answers take approve, ignore, needs checking and undo (E103), and the stored flags (Q.3 #9)."""

import pytest
from rest_framework.exceptions import ValidationError

from deals import activity
from deals.stored_counts import rebuild_all
from questionnaire import services
from questionnaire.models import Questionnaire
from questionnaire.selectors.sources import source_rows

from .world import make_world

pytestmark = pytest.mark.django_db
FL = 'fl_blue_51'


def ref(slot):
    return f'questionnaire:{FL}:{slot}'


@pytest.fixture
def world(user):
    return make_world(user)


def test_E103_check_then_approve_a_typed_answer_and_the_flags_follow(user, world):
    services.set_answers(user, world.id, FL, {'txtRsnBid': 'Renewal Increase'})
    services.mark_answers(user, world.id, FL, 'check', refs=[ref('txtRsnBid')])
    row = Questionnaire.objects.get(deal=world)
    assert row.flags == 1 and row.sources['txtRsnBid']['mark']['state'] == 'check'
    assert not any(v for v in rebuild_all([world.id]).values())
    marked = services.mark_answers(user, world.id, FL, 'approve')  # no refs: the open warnings on screen
    row.refresh_from_db()
    assert marked.slots == ['txtRsnBid'] and row.flags == 0 and row.sources['txtRsnBid']['confirmed']


def test_E103_G27_approving_a_live_prefill_stores_it_and_undo_lets_it_go_live_again(user, world):
    marked = services.mark_answers(user, world.id, FL, 'approve', refs=[ref('City')])
    row = Questionnaire.objects.get(deal=world)
    assert row.answers['City'] == 'Orlando' and row.sources['City']['origin'] == 'prefill'
    activity.revert(marked.activity.id, user)
    row.refresh_from_db()
    assert 'City' not in row.answers
    rows = {r['slot']: r for r in source_rows(world, FL)['rows']}
    assert rows['City']['where'] == 'prefill' and rows['City']['value'] == 'Orlando'


def test_E103_a_blank_takes_no_mark_and_refs_name_this_form(user, world):
    assert services.mark_answers(user, world.id, FL, 'check', refs=[ref('txtAdd2')]).slots == []
    with pytest.raises(ValidationError):
        services.mark_answers(user, world.id, FL, 'approve', refs=['questionnaire:wp_lg:group_name'])
    with pytest.raises(ValidationError):
        services.mark_answers(user, world.id, FL, 'shout', refs=[ref('City')])


def test_E103_marks_are_bookkeeping(user, world):
    services.set_answers(user, world.id, FL, {'txtRsnBid': 'Renewal Increase'})
    row = Questionnaire.objects.get(deal=world)
    stamp = row.updated_at
    services.mark_answers(user, world.id, FL, 'ignore', refs=[ref('txtRsnBid')])
    row.refresh_from_db()
    assert row.updated_at == stamp
