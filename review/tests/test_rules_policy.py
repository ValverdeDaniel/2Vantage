"""`review.rules.policy`, table by table (plan.md §5.8; L60–L64, L69; OQ80 the narrowed rule, OQ81 the sliding rule,
Q.3 #7 the clock at 21:00 Eastern)."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from review.rules import policy

EASTERN = ZoneInfo('America/New_York')
NOW = datetime(2026, 11, 12, 2, 0, tzinfo=UTC)  # 21:00 Eastern on Nov 11: UTC is already the next day


def link(**fields):
    base = {
        'slides': True,
        'revoked_at': None,
        'expires_at': NOW + timedelta(days=7),
        'ceiling_at': NOW + timedelta(days=30),
        'submitted_at': None,
    }
    return SimpleNamespace(**{**base, **fields})


CENSUS_CELLS = {'census': {'scope': 'selected', 'cells': [[1, 'dob']]}}


@pytest.mark.parametrize(
    ('asks', 'sensitive', 'level', 'because'),
    [
        ({'intake': {'scope': 'missing'}}, False, 'link', []),  # intake opens with the link alone
        ({'census': {'scope': 'none', 'file': True}}, False, 'link', []),  # the census file is upload-only
        ({'documents': {'slots': ['claims'], 'missing': True}}, False, 'link', []),
        ({'questionnaires': [{'form': 'fl_blue_51', 'mode': 'upload'}]}, False, 'link', []),
        (CENSUS_CELLS, False, 'pin', ['Census']),  # the page shows census people
        ({'census': {'scope': 'missing'}}, False, 'pin', ['Census']),
        ({'census': {'scope': 'all', 'file': True}}, False, 'pin', ['Census']),
        ({'questionnaires': [{'form': 'fl_blue_51', 'mode': 'online'}]}, False, 'pin', ['Questionnaire answers']),
        ({'intake': {'scope': 'all'}}, True, 'pin', ['Medical and claimant questions']),  # a medical send-back
        ({}, False, 'link', []),
    ],
)
def test_L64_OQ80_the_floor_follows_what_the_page_shows(asks, sensitive, level, because):
    assert policy.floor(asks, sensitive=sensitive) == {'level': level, 'because': because}


def test_L64_a_new_link_rises_to_its_floor_and_never_drops_below_a_pick():
    assert policy.stricter('link', 'pin') == 'pin'
    assert policy.stricter('pin', 'link') == 'pin'
    assert policy.stricter('link', 'link') == 'link'


def test_OQ81_a_new_link_lives_seven_days_under_a_thirty_day_ceiling():
    assert policy.first_life(NOW) == (NOW + timedelta(days=7), NOW + timedelta(days=30))


def test_L61_Q3_7_a_picked_day_ends_at_midnight_agency_time_even_at_9pm_eastern():
    ceiling = NOW + timedelta(days=30)
    picked = policy.picked_expiry(date(2026, 11, 20), ceiling, EASTERN)
    assert picked == datetime(2026, 11, 20, 23, 59, 59, tzinfo=EASTERN)
    # The ceiling's own day is the last one a person may pick, in the agency's zone, and it caps the time.
    assert policy.latest_day(ceiling, EASTERN) == date(2026, 12, 11)
    assert policy.picked_expiry(date(2026, 12, 11), ceiling, EASTERN) == ceiling


@pytest.mark.parametrize(
    ('expires_in', 'ceiling_in', 'expected_in'),
    [
        (timedelta(days=-3), timedelta(days=20), timedelta(days=7)),  # ran out: its life again from now
        (timedelta(days=2), timedelta(days=20), timedelta(days=7)),
        (timedelta(days=10), timedelta(days=20), timedelta(days=10)),  # never shorter than it is
        (timedelta(days=2), timedelta(days=4), timedelta(days=4)),  # never past the ceiling
    ],
)
def test_L60_renewal_gives_its_life_again_within_the_ceiling(expires_in, ceiling_in, expected_in):
    assert policy.renewed(NOW + expires_in, NOW + ceiling_in, NOW) == NOW + expected_in


@pytest.mark.parametrize(
    ('fields', 'moves_to'),
    [
        ({'expires_at': NOW + timedelta(days=3)}, NOW + timedelta(days=7)),  # a save slides it
        ({'expires_at': NOW + timedelta(days=6, hours=12)}, None),  # at most once a day
        ({'expires_at': NOW + timedelta(days=3), 'slides': False}, None),  # a picked date holds
        ({'expires_at': NOW + timedelta(days=3), 'revoked_at': NOW}, None),  # turned off never slides
        ({'expires_at': NOW + timedelta(days=3), 'ceiling_at': NOW + timedelta(days=5)}, NOW + timedelta(days=5)),
        ({'expires_at': NOW + timedelta(days=3), 'ceiling_at': NOW + timedelta(days=3, hours=6)}, None),
    ],
)
def test_L62_OQ81_a_save_slides_the_expiry_once_a_day_never_past_the_ceiling(fields, moves_to):
    assert policy.slid_on_save(link(**fields), NOW) == moves_to


@pytest.mark.parametrize(
    ('fields', 'closed', 'opens'),
    [
        ({}, False, True),
        ({}, True, False),
        ({'revoked_at': NOW}, False, False),
        ({'expires_at': NOW}, False, False),
    ],
)
def test_L60_L70_a_link_opens_until_it_runs_out_is_turned_off_or_its_request_closes(fields, closed, opens):
    assert policy.opens(link(**fields), NOW, closed=closed) is opens


def test_L8_days_left_counts_whole_days_and_never_below_zero():
    assert policy.days_left(NOW + timedelta(days=2, hours=23), NOW) == 2
    assert policy.days_left(NOW - timedelta(days=1), NOW) == 0


@pytest.mark.parametrize(
    ('nudge', 'fields', 'lost', 'due'),
    [
        ({'on': '2026-11-11'}, {}, False, True),
        ({'on': '2026-11-12'}, {}, False, False),  # tomorrow, in the agency's day
        ({'on': '2026-11-10', 'done_at': '2026-11-11T10:00:00'}, {}, False, False),
        ({'on': '2026-11-11'}, {'revoked_at': NOW}, False, False),
        ({'on': '2026-11-11'}, {'submitted_at': NOW}, False, False),
        ({'on': '2026-11-11'}, {}, True, False),  # it lapses when the deal is lost
        ({}, {}, False, False),
    ],
)
def test_L69_a_nudge_is_due_on_its_day_while_the_link_still_waits(nudge, fields, lost, due):
    today = NOW.astimezone(EASTERN).date()
    assert policy.nudge_open(nudge, link(**fields), NOW, today, lost=lost) is due
