"""The census rollups by line and by plan name (plan.md §4.1, §5.3.6, §5.3.7; C39–C46). Pure."""

import datetime

import pytest

from census import rollup


def emp(**values):
    return {'kind': 'employee', 'values': values}


def dep(**values):
    return {'kind': 'dependent', 'values': values}


PEOPLE = [
    emp(medical_tier='EE', medical_plan='Gold PPO', dental_tier='EE', basic_life_amount='25000', hours_per_week='40'),
    emp(
        medical_tier='Waived', dental_tier='ES', basic_life_amount='$50,000', annual_salary='60000', hours_per_week='30'
    ),
    emp(medical_tier='FAM', medical_plan='Gold PPO', hours_per_week='29', dob='1960-03-01'),
    emp(medical_tier='', medical_plan='HDHP 3300', hours_per_week=''),
    emp(medical_tier='Gold', medical_plan='HDHP 3300'),
    dep(medical_tier='FAM', medical_plan='Gold PPO', dob='1962-01-01', basic_life_amount='10000'),  # never counted
]
STORED = rollup.compute(PEOPLE)


def test_C39_tier_counts_by_line_count_employees_only():
    assert STORED['employees'] == 5
    assert STORED['tiers']['medical_tier'] == {
        'EE': 1,
        'ES': 0,
        'EC': 0,
        'FAM': 1,
        'waived': 1,
        'blank': 1,
        'unknown': 1,
    }
    assert STORED['tiers']['dental_tier'] == {
        'EE': 1,
        'ES': 1,
        'EC': 0,
        'FAM': 0,
        'waived': 0,
        'blank': 3,
        'unknown': 0,
    }


def test_C41_tier_counts_by_plan_name():
    medical = STORED['by_plan']['medical']
    assert medical['Gold PPO'] == {'EE': 1, 'ES': 0, 'EC': 0, 'FAM': 1, 'waived': 0, 'blank': 0, 'unknown': 0}
    assert medical['HDHP 3300'] == {'EE': 0, 'ES': 0, 'EC': 0, 'FAM': 0, 'waived': 0, 'blank': 1, 'unknown': 1}
    assert medical[''] == {'EE': 0, 'ES': 0, 'EC': 0, 'FAM': 0, 'waived': 1, 'blank': 0, 'unknown': 0}


# (line, what for_line says, without by_plan)
LINES = [
    (
        'medical',
        {'EE': 1, 'ES': 0, 'EC': 0, 'FAM': 1, 'waived': 1, 'blank': 1, 'unknown': 1, 'enrolled': 2, 'source': 'census'},
    ),
    (
        'accident',
        {
            'EE': 1,
            'ES': 0,
            'EC': 0,
            'FAM': 1,
            'waived': 1,
            'blank': 1,
            'unknown': 1,
            'enrolled': 2,
            'source': 'borrowed',
        },
    ),
    ('basic_life_add', {'volume': '75000', 'field': 'basic_life_amount', 'source': 'census'}),  # C42: employees only
    ('ltd', {'volume': '60000', 'field': 'annual_salary', 'source': 'census'}),
    ('std', None),  # nothing to sum
    ('hsa', {'lives': 5, 'source': 'census'}),  # PEPM: every employee
    ('stop_loss', {'lives': 2, 'source': 'census'}),  # C44: medical enrolled
]


@pytest.mark.parametrize(('line', 'expected'), LINES)
def test_C39_C42_C43_C44_for_line_table(line, expected):
    found = rollup.for_line(STORED, line)
    if found:
        found.pop('by_plan', None)
    assert found == expected


def test_C44_stop_loss_falls_back_to_the_employee_count():
    stored = rollup.compute([emp(medical_tier='Waived'), emp()])
    assert rollup.for_line(stored, 'stop_loss') == {'lives': 2, 'source': 'census'}
    assert rollup.for_line(rollup.compute([]), 'medical') is None


def test_C45_fte_counts_employees_at_the_threshold():
    assert rollup.fte(PEOPLE) == 2  # 40 and 30; 29 and a blank never count
    assert rollup.fte(PEOPLE, '25') == 3
    assert rollup.fte([dep()]) is None


def test_C46_aged_65_at_the_effective_date_dependents_on_their_own_birth_date():
    effective = datetime.date(2026, 12, 31)
    assert rollup.aged_65(PEOPLE, effective) == 1  # the employee is 66; the spouse turns 65 the next day
    assert rollup.aged_65(PEOPLE, datetime.date(2027, 1, 1)) == 2
    assert rollup.aged_65(PEOPLE, None) is None
