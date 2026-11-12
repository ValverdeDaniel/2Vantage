"""`review.rules.requests`, table by table (plan.md §5.8; L7, L8, L55, L70): request and link states, `carries`
(the one "what a link asks" rule) and the Waiting lane's order."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from review.rules import requests

NOW = datetime(2026, 11, 12, 15, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=5)


def link(**fields):
    base = {
        'sent_at': None,
        'opened_at': None,
        'submitted_at': None,
        'revoked_at': None,
        'last_saved_at': None,
        'expires_at': LATER,
    }
    return SimpleNamespace(**{**base, **fields})


SENT = {'sent_at': NOW - timedelta(days=1)}


@pytest.mark.parametrize(
    ('links', 'closed_at', 'state'),
    [
        ([link(), link()], None, 'draft'),
        ([link(**SENT), link()], None, 'partly_sent'),
        ([link(**SENT), link(**SENT)], None, 'waiting'),
        ([link(**SENT), link(submitted_at=NOW)], None, 'answered'),  # anyone submitting answers it
        ([link(**SENT, expires_at=NOW - timedelta(hours=1))], None, 'expired'),
        ([link(**SENT, revoked_at=NOW)], None, 'expired'),  # turned off counts as run out
        ([link(**SENT, submitted_at=NOW)], NOW, 'closed'),
    ],
)
def test_L55_a_request_state_comes_from_its_links(links, closed_at, state):
    assert requests.request_state(links, closed_at, NOW) == state


@pytest.mark.parametrize(
    ('fields', 'closed', 'covered', 'state'),
    [
        ({}, False, False, 'draft'),
        ({'expires_at': NOW}, False, False, 'lapsed_draft'),
        (SENT, False, False, 'waiting'),
        ({**SENT, 'opened_at': NOW}, False, False, 'opened'),
        ({**SENT, 'expires_at': NOW}, False, False, 'expired'),
        ({**SENT, 'revoked_at': NOW}, False, False, 'off'),
        (SENT, True, False, 'closed'),
        (SENT, False, True, 'covered'),
        ({**SENT, 'submitted_at': NOW, 'revoked_at': NOW}, True, False, 'answered'),
    ],
)
def test_L8_one_vocabulary_for_a_link(fields, closed, covered, state):
    assert requests.link_state(link(**fields), NOW, closed=closed, covered=covered) == state


@pytest.mark.parametrize(
    ('fields', 'typing'),
    [
        ({'last_saved_at': NOW}, True),
        ({'last_saved_at': NOW, 'submitted_at': NOW - timedelta(hours=1)}, True),  # saved again after submitting
        ({'last_saved_at': NOW - timedelta(hours=1), 'submitted_at': NOW}, False),
        ({'last_saved_at': NOW, 'revoked_at': NOW}, False),
        ({'last_saved_at': NOW - timedelta(hours=25)}, False),  # idle a day: ready for review instead
        ({}, False),
    ],
)
def test_L7_a_link_is_still_being_answered_while_saved_and_not_submitted_since(fields, typing):
    assert requests.in_progress(link(**fields), NOW) is typing


@pytest.mark.parametrize(
    ('fields', 'is_ready'),
    [
        ({'submitted_at': NOW}, True),
        ({'submitted_at': NOW, 'last_saved_at': NOW - timedelta(minutes=5)}, True),
        ({'submitted_at': NOW - timedelta(hours=2), 'last_saved_at': NOW - timedelta(hours=1)}, False),  # a resave
        ({'last_saved_at': NOW - timedelta(hours=24)}, True),  # idle 24 h
        ({'last_saved_at': NOW - timedelta(hours=23)}, False),
        ({}, False),
    ],
)
def test_L14_answers_are_ready_after_submit_or_a_day_idle(fields, is_ready):
    assert requests.ready(link(**fields), NOW) is is_ready


def test_L7_the_waiting_lane_runs_out_soonest_first_then_newest():
    rows = [
        {'id': 1, 'soonest_days': None, 'created_at': '2026-11-01'},
        {'id': 2, 'soonest_days': 5, 'created_at': '2026-11-02'},
        {'id': 3, 'soonest_days': 1, 'created_at': '2026-11-03'},
        {'id': 4, 'soonest_days': 5, 'created_at': '2026-11-04'},
    ]
    assert [row['id'] for row in requests.soonest_first(rows)] == [3, 4, 2, 1]


ASKS = {
    'intake': {'scope': 'selected', 'keys': ['industry'], 'blocks': ['contacts']},
    'census': {'scope': 'selected', 'columns': [], 'cells': [[41, 'dob']], 'file': True},
    'questionnaires': [
        {'form': 'fl_blue_51', 'mode': 'online', 'picks': {'fields': ['q1'], 'blocks': []}},
        {'form': 'stop_loss_siia', 'mode': 'upload', 'picks': {'fields': [], 'blocks': []}},
    ],
    'documents': {'slots': ['invoice@medical'], 'missing': True},
}


@pytest.mark.parametrize(
    ('asks', 'ref', 'carried'),
    [
        (ASKS, 'intake:industry', True),
        (ASKS, 'intake:sic_code', False),
        (ASKS, 'intake:block:contacts', True),
        (ASKS, 'intake:block:bor', False),
        (ASKS, 'census:41:dob', True),
        (ASKS, 'census:41:zip', False),
        (ASKS, 'census:42:dob', False),
        (ASKS, 'census:file', True),
        (ASKS, 'q:fl_blue_51:q1', True),
        (ASKS, 'q:fl_blue_51:q2', False),  # a narrowed form asks only its picks
        (ASKS, 'q:fl_blue_51:file', False),
        (ASKS, 'q:stop_loss_siia:file', True),  # upload mode asks the file, never the answers
        (ASKS, 'q:stop_loss_siia:q1', False),
        (ASKS, 'doc:invoice@medical', True),
        (ASKS, 'doc:claims', True),  # documents `missing`: in the missing set below
        (ASKS, 'doc:renewal@dental', False),
        ({'intake': {'scope': 'all'}}, 'intake:anything', True),
        ({'intake': {'scope': 'missing'}}, 'intake:industry', True),  # blank now
        ({'intake': {'scope': 'missing'}}, 'intake:sic_code', False),
        ({'intake': {'scope': 'required'}}, 'intake:industry', False),  # blank, but not needed to market
        ({'intake': {'scope': 'required'}}, 'intake:zip', True),
        ({'census': {'scope': 'all', 'columns': ['dob']}}, 'census:7:dob', True),
        ({'census': {'scope': 'all', 'columns': ['dob']}}, 'census:7:zip', False),
        ({'census': {'scope': 'missing', 'columns': []}}, 'census:7:zip', True),
        ({'census': {'scope': 'missing', 'columns': []}}, 'census:7:dob', False),
        ({'census': {'scope': 'blank', 'columns': []}}, 'census:7:dob', True),
        ({'census': {'scope': 'none', 'file': True}}, 'census:7:dob', False),
        ({}, 'intake:industry', False),
        (ASKS, 'nonsense', False),
    ],
)
def test_L59_carries_is_the_one_rule_for_what_a_link_asks(asks, ref, carried):
    missing = {'intake:zip', 'census:7:zip', 'doc:claims'}
    blank = {'intake:industry', 'intake:zip', 'census:7:dob', 'census:7:zip'}
    assert requests.carries(asks, ref, missing=missing, blank=blank) is carried
