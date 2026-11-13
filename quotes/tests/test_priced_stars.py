"""A priced version's star (plan.md §5.4; F83; Q.9 row 35: no auto star on an unstarred line): starred while its line
has stars and room, added unstarred with a warning past the room, and two versions racing for the last star leave the
cap. Synthetic deals, on test_priced.py's line."""

import threading
import time
from unittest import mock

import pytest
from django.db import connection

from conftest import make_deal
from quotes import services
from quotes.models import Plan
from quotes.services import priced
from quotes.tests.test_priced import FIVE_OFF, make_line

pytestmark = pytest.mark.django_db


@pytest.fixture
def line(user, deal):
    return make_line(user, deal)


def test_F83_Q9_no_auto_star_on_a_line_with_no_stars(user, deal, line):
    result = priced.price(user, deal, [line['cigna'].id], FIVE_OFF)
    assert not result.plans[0].starred and result.warning == ''


def test_F83_a_new_version_is_starred_while_its_starred_line_has_room(user, deal, line):
    services.star(user, deal, [line['uhc'].id], True)
    result = priced.price(user, deal, [line['cigna'].id], FIVE_OFF)
    version = Plan.objects.get(pk=result.plans[0].id)
    assert (version.starred, version.star_reason) == (True, '5% concession')
    assert not Plan.objects.get(pk=line['cigna'].id).starred  # the original's star is its own


def test_F83_past_the_room_a_version_is_added_unstarred_with_a_warning(user, deal, line):
    a = line['a']
    for n in range(14):
        services.create_plan(
            user, deal, line='medical', role='alternate', carrier='Oscar', name=f'Q{n}', replaces_ids=[a.id]
        )
    quotes = Plan.objects.filter(deal=deal, line='medical', role='alternate').exclude(pk=line['cigna'].id)
    services.star(user, deal, list(quotes.values_list('id', flat=True))[:15], True)
    result = priced.price(user, deal, [line['cigna'].id], FIVE_OFF)
    assert not result.plans[0].starred
    assert result.warning == 'The Medical shortlist is full — the 5% concession was added unstarred.'


@pytest.mark.django_db(transaction=True)
def test_F83_Q3_two_versions_racing_for_the_last_star_leave_the_cap(user):
    deal = make_deal(user)
    made = make_line(user, deal)
    for n in range(13):
        services.create_plan(user, deal, line='medical', role='alternate', carrier='Oscar', name=f'Q{n}')
    others = Plan.objects.filter(deal=deal, line='medical', carrier='Oscar').values_list('id', flat=True)
    services.star(user, deal, [*others, made['uhc'].id], True)  # 1 current + 14 starred: room for one more column
    real_line = priced.locks.line
    results = []

    def slow_line(*args):
        found = real_line(*args)
        time.sleep(0.15)  # hold the room check open while the other request arrives
        return found

    def race(plan_id):
        try:
            results.append(priced.price(user, deal, [plan_id], FIVE_OFF).plans[0].starred)
        finally:
            connection.close()

    with mock.patch.object(priced.locks, 'line', slow_line):
        threads = [threading.Thread(target=race, args=(made[key].id,)) for key in ('cigna', 'uhc')]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert sorted(results) == [False, True]
    held = Plan.objects.filter(deal=deal, line='medical', starred=True).count() + 1
    assert held == 16
