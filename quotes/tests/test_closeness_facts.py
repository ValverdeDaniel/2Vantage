"""`closeness` (F51, F121) and `facts` (F62, F122), table-driven over plain plans."""

import pytest

from quotes import closeness, facts
from quotes.shapes import PlanData


def medical(pid, role='alternate', **values):
    return PlanData(id=pid, role=role, values={k: str(v) for k, v in values.items()})


HDHP = medical(1, 'current', deductible_single=3300, oop_max_single=6000, coinsurance=20, rate_ee=512.34)
PPO = medical(2, 'current', deductible_single=1500, oop_max_single=4000, coinsurance=10, rate_ee=700)


@pytest.mark.parametrize(
    'case, quote, nearest',
    [
        ('an HDHP-like quote', medical(3, deductible_single=3000, oop_max_single=6500, coinsurance=20, rate_ee=480), 1),
        ('a PPO-like quote', medical(4, deductible_single=1000, oop_max_single=3500, coinsurance=10, rate_ee=690), 2),
        ('a quote with no numbers scores 1.0 against both: the first slot wins', medical(5), 1),
    ],
)
def test_F51_nearest_current_plan(case, quote, nearest):
    assert closeness.nearest(quote, [HDHP, PPO], 'medical') == nearest, case


def test_F121_score_and_closest():
    same = medical(3, deductible_single=3300, oop_max_single=6000, coinsurance=20, rate_ee=512.34)
    assert closeness.score(same, HDHP, 'medical') == 0
    assert closeness.score(medical(4), HDHP, 'medical') == 1.0  # every anchored axis missing
    assert closeness.closest(same, [HDHP, PPO], 'medical') == 0
    assert closeness.closest(HDHP, [HDHP, PPO], 'medical') is None  # current plans score nothing
    assert closeness.nearest(same, [HDHP], 'medical') is None  # one current plan: no link to suggest
    assert closeness.score(same, medical(9, 'current', network='Open Access'), 'medical') is None


@pytest.mark.parametrize(
    'case, values, sources, status',
    [
        ('required and blank', {}, {}, {'deductible_single': 'missing', 'oop_max_single': 'missing'}),
        (
            'read by Claude, not approved',
            {'deductible_single': '3300'},
            {'deductible_single': {'origin': 'ai'}},
            {'deductible_single': 'to_check'},
        ),
        (
            'approved',
            {'deductible_single': '3300'},
            {'deductible_single': {'origin': 'ai', 'confirmed': {'by': 1}}},
            {},
        ),
        (
            'marked ⚑ Needs checking',
            {'pcp_copay': '25'},
            {'pcp_copay': {'origin': 'typed', 'mark': {'state': 'check'}}},
            {'pcp_copay': 'to_check'},
        ),
        ('ignored', {'pcp_copay': '25'}, {'pcp_copay': {'origin': 'ai', 'mark': {'state': 'ignored'}}}, {}),
    ],
)
def test_F122_statuses(case, values, sources, status):
    got = facts.statuses('medical', values, sources)
    assert {k: v for k, v in got.items() if k in status or v == 'to_check'} == status, case


def test_F122_quoted_premium_only_plans_do_not_miss_tier_rates():
    status = facts.statuses('medical', {'group_premium_monthly': '15000'}, {})
    assert 'rate_ee' not in status and status['deductible_single'] == 'missing'


def test_F122_F22_plan_facts():
    complete = {'deductible_single': '3300', 'oop_max_single': '6000', 'network': 'OA', 'plan_type': 'HDHP'}
    numbers = {'deductible_single': 3300, 'oop_max_single': 6000}
    # F22: a plan with no total yet is not incomplete (the filter card names it instead, F140).
    assert facts.plan_facts('medical', complete, {}) == {
        'incomplete': False,
        'flags': 0,
        'compliance': [],
        'numbers': numbers,
    }
    doubted = facts.plan_facts('medical', {**complete, 'minimum_value': 'No'}, {'network': 'to_check'})
    assert doubted == {'incomplete': True, 'flags': 1, 'compliance': ['minimum_value'], 'numbers': numbers}
    dental = {'den_annual_max': '1500', 'den_deductible': '50', 'network': 'PPO', 'plan_type': 'PPO'}
    assert facts.plan_facts('dental', dental, {})['incomplete'] is False  # judged on the line's own fields


@pytest.mark.parametrize(
    'value, percent, number',
    [
        ('3300', False, 3300),
        ('$1,500', False, 1500),
        ('612.50', False, 612.5),
        ('-5', False, -5),
        ('20%', True, 20),
        ('20%', False, None),  # a percent is no copay amount (F21's strict reading)
        ('$25 – $135', False, None),
        ('Deductible, then 20%', False, None),
        ('', False, None),
        (None, False, None),
        ('1,50', False, None),
    ],
)
def test_F21_numbers_are_read_strictly(value, percent, number):
    assert facts.number(value, percent) == number


def test_F21_numbers_cover_the_lines_numeric_fields_only():
    values = {'rate_ee': '512.34', 'pcp_copay': 'Deductible, then 20%', 'coinsurance': '20%', 'network': '1500'}
    assert facts.numbers('medical', values) == {'rate_ee': 512.34, 'coinsurance': 20}
    assert 'deductible_single' not in facts.numbers('dental', {'deductible_single': '500'})
