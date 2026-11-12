"""`ready` and `checks` as table cases (plan.md §5.4, §8.14; J23, J28, J52, J.5 B36; Q.9 row 25). Pure."""

import pytest

from proposals import checks, ready

PARTS = {'comparison': True, 'cost': True, 'recommendation': True}


def sheet(**over):
    """A shopped medical line with one current plan and two quotes, priced, nothing missing."""
    base = {
        'line': 'medical',
        'label': 'Medical',
        'off': None,
        'off_words': '',
        'kept': False,
        'options': 2,
        'presented': 3,
        'starred': True,
        'several': False,
        'missing': [],
        'sold': False,
        'composite': True,
        'no_people': False,
        'cost_or_pick': True,
        'parts': dict(PARTS),
        'priced': True,
        'unrated': 0,
        'currents': 1,
        'loose': 0,
        'uncounted': [],
        'reasons': True,
        'blank_rows': [],
    }
    return {**base, **over}


@pytest.mark.parametrize(
    ('over', 'missing'),
    [
        ({}, []),
        ({'missing': ['PPO']}, ['Medical']),
        ({'missing': ['PPO'], 'kept': True}, []),  # a kept line never blocks (B36)
        ({'missing': ['PPO'], 'off': 'left_off'}, []),
        ({'missing': ['PPO'], 'options': 0}, []),  # nothing to choose from
        ({'missing': ['PPO'], 'sold': True}, []),  # the sold plan is the pick
        ({'missing': ['PPO', 'HMO'], 'several': True}, ['Medical, for PPO', 'Medical, for HMO']),
    ],
)
def test_J28_B36_what_needs_a_pick(over, missing):
    found = ready.ready([sheet(**over)])
    assert found['missing'] == missing
    assert found['ok'] is (not missing and not over.get('off'))
    assert (found['sentence'] is None) is (not missing)


def test_J28_nothing_on_the_proposal_is_not_ready():
    assert ready.ready([sheet(off='not_in_intent')])['ok'] is False


def _codes(lines, **kwargs):
    return [(item['code'], item['level']) for item in checks.checks(lines, cap=16, **kwargs)]


@pytest.mark.parametrize(
    ('over', 'code', 'level'),
    [
        ({'off': 'left_off', 'off_words': 'Left off in Coverage & marketing intent'}, 'line_off', 'warn'),
        ({'presented': 17}, 'oversize', 'stop'),
        ({'options': 9, 'starred': False}, 'unstarred', 'warn'),
        ({'no_people': True}, 'no_enrollment', 'warn'),
        ({'priced': False}, 'no_prices', 'warn'),
        ({'unrated': 1}, 'current_unrated', 'warn'),
        ({'several': True, 'currents': 2, 'loose': 2}, 'not_linked', 'warn'),
        ({'several': True, 'currents': 2, 'uncounted': ['Aetna PPO']}, 'link_needs_enrollment', 'warn'),
        ({'missing': ['PPO']}, 'no_recommendation', 'stop'),
        ({'reasons': False}, 'no_reasons', 'warn'),
        ({'blank_rows': ['Coinsurance', 'PCP copay', 'ER copay', 'Rx tier 1']}, 'missing_values', 'warn'),
    ],
)
def test_J23_each_check_fires_on_its_fact(over, code, level):
    assert (code, level) in _codes([sheet(**over)])


def test_J23_a_clean_line_has_nothing_to_check_and_stops_come_first():
    assert _codes([sheet()]) == []
    found = _codes([sheet(reasons=False), sheet(line='dental', label='Dental', missing=['DPPO'])])
    assert found[0] == ('no_recommendation', 'stop')


def test_J23_J57_deal_wide_words_answer_for_a_line_only_when_no_line_has_its_own():
    assert ('no_reasons', 'warn') not in _codes([sheet(reasons=False)], deal_words='Our view')
    lines = [sheet(reasons=False), sheet(line='dental', label='Dental', reasons=True)]
    assert ('no_reasons', 'warn') in _codes(lines, deal_words='Our view')


def test_J23_nothing_presented_stops_and_names_the_blank_rows():
    assert ('nothing_presented', 'stop') in _codes([sheet(off='left_off', off_words='Left off')])
    item = checks.checks([sheet(blank_rows=['A', 'B', 'C', 'D', 'E'])], cap=16)[0]
    assert item['text'] == 'Medical: 5 benefit rows print blank for some plans (A, B, C, and 2 more).'
    assert item['fix'] == {'card': 'rows'}
