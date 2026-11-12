"""deals.rules.is_past and client_asks_open (plan.md §5.1; O.6 #31; M9, M49, L56, K64): when the client may still be
asked for anything and write through its links. Pure rules, plus the 21:00 Eastern clock (Q.3 #7)."""

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest import mock
from zoneinfo import ZoneInfo

import pytest

from conftest import make_deal
from deals import clock, rules, services

TODAY = date(2027, 6, 1)


def deal(stage='quoting', effective_date=None, archived=False):
    client = SimpleNamespace(archived_at=datetime(2027, 1, 1) if archived else None)
    return SimpleNamespace(stage=stage, effective_date=effective_date, client=client)


@pytest.mark.parametrize(
    'stage, effective_date, past',
    [
        ('quoting', None, False),
        ('quoting', TODAY, False),
        ('sold', TODAY - timedelta(days=365), False),  # exactly a year after: still the year in flight
        ('sold', TODAY - timedelta(days=366), True),
        ('lost', TODAY + timedelta(days=30), True),
    ],
)
def test_O6_31_a_deal_is_past_when_lost_or_more_than_a_year_after_its_effective_date(stage, effective_date, past):
    assert rules.is_past(deal(stage, effective_date), TODAY) is past


@pytest.mark.parametrize(
    'shape, reason',
    [
        ({'stage': 'lost'}, 'lost'),
        ({'archived': True}, 'archived'),
        ({'effective_date': TODAY - timedelta(days=400)}, 'past'),
        ({'stage': 'lost', 'archived': True}, 'lost'),  # one sentence, the first that applies
    ],
)
def test_M9_client_asks_open_refuses_lost_archived_and_past_deals_with_their_sentences(shape, reason):
    assert rules.client_asks_open(deal(**shape), TODAY) == rules.ASKS_CLOSED[reason]


def test_M9_an_open_deal_takes_asks():
    assert rules.client_asks_open(deal(effective_date=TODAY + timedelta(days=60)), TODAY) is None


def test_M9_an_archived_client_closes_its_deals_asks_and_restore_reopens_them(user):
    built = make_deal(user)
    services.set_archived(user, built.client_id, True)
    built.refresh_from_db()
    built.client.refresh_from_db()
    assert rules.client_asks_open(built) == rules.ASKS_CLOSED['archived']
    services.set_archived(user, built.client_id, False)
    built.client.refresh_from_db()
    assert rules.client_asks_open(built) is None


def test_Q3_7_the_past_rule_counts_agency_days_at_21_00_eastern():
    # 31 May 2027, 9 pm in New York, is already 1 June in UTC: the agency's date decides.
    late = datetime(2027, 5, 31, 21, 0, tzinfo=ZoneInfo('America/New_York'))
    edge = deal('sold', date(2026, 5, 31))  # 365 days before 31 May 2027, 366 before 1 June
    with mock.patch.object(clock, 'now', return_value=late):
        assert rules.is_past(edge) is False
