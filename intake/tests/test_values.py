"""The one cleaner and the shown-when rule (plan.md §4.5, §5.2; B1–B3). Pure: no database."""

import pytest

from intake import form, values


def _q(key):
    return form.BY_KEY[key]


@pytest.mark.parametrize(
    ('key', 'raw', 'stored'),
    [
        ('legal_name', '  Example Co.  ', 'Example Co.'),
        ('legal_name', '   ', ''),
        ('fein', '12 3456789', '12-3456789'),
        ('fein', '12-3456789', '12-3456789'),
        ('total_employees', '1,500', '1500'),
        ('budget_target', '$45,000.50', '45000.5'),
        ('acceptable_increase_pct', '7.50%', '7.5'),
        ('decision_date', '12/1/2026', '2026-12-01'),
        ('decision_date', '2027-01-01', '2027-01-01'),
        ('decision_date', 'March 3, 2027', '2027-03-03'),
        ('decision_date', '3/4/27', '2027-03-04'),  # month first when ambiguous
        ('union', 'y', 'Yes'),
        ('union', 'FALSE', 'No'),
        ('entity_type', 's-corp', 'S-Corp'),
        ('states_operating', 'fl, ga; tx/FL al', ['FL', 'GA', 'TX', 'AL']),
        ('states_operating', ['ga', 'FL', 'GA'], ['GA', 'FL']),
        ('states_operating', [], ''),
    ],
)
def test_B3_one_cleaner_stores_each_type_one_way(key, raw, stored):
    assert values.clean_value(_q(key), raw) == (stored, None)


@pytest.mark.parametrize(
    ('key', 'raw', 'error'),
    [
        ('fein', '123', 'FEIN takes XX-XXXXXXX, not "123"'),
        ('total_employees', 'about 40', 'Total Employees takes a number, not "about 40"'),
        ('decision_date', 'soon', 'Decision Date takes a date, not "soon"'),
        ('union', 'maybe', 'Union Employees takes Yes or No, not "maybe"'),
        (
            'payroll_processing',
            'fax',
            'Payroll Processing takes one of: API, Manual — "fax" is not one of them',
        ),
    ],
)
def test_B3_one_cleaner_refuses_in_words(key, raw, error):
    assert values.clean_value(_q(key), raw) == (None, error)


def test_B3_a_multi_refusal_names_the_first_options_and_the_bad_parts():
    value, error = values.clean_value(_q('states_operating'), 'FL, Narnia')
    assert value is None
    assert error.startswith('States of Operation takes AL, AK, AZ')
    assert error.endswith('…; not: Narnia')


def test_B2_shown_when_rules_read_the_stored_answers():
    waive = _q('waive_reason')
    assert not values.shown(waive, {})
    assert not values.shown(waive, {'waiving_count': '0'})
    assert values.shown(waive, {'waiving_count': '3'})
    assert not values.shown(waive, {'waiving_count': 'several'})  # gt compares numbers only
    assert values.shown(_q('locations_list'), {'multi_location': 'Yes'})
    assert not values.shown(_q('locations_list'), {'multi_location': 'No'})
    assert values.shown(_q('legal_name'), {})  # no rule: always shown


def test_B2_hidden_lists_the_questions_their_rule_hides():
    hidden = values.hidden({'section_125': 'Yes', 'waiving_count': '2'})
    assert 'section_125_handler' not in hidden and 'waive_reason' not in hidden
    assert {'locations_list', 'form_5500_handler', 'pcori_handler'} <= set(hidden)


def test_B1_form_holds_the_old_questions_in_four_sections():
    assert [key for key, _ in form.SECTIONS] == ['employer', 'eligibility', 'goals', 'compliance']
    assert {q['section'] for q in form.QUESTIONS} == {key for key, _ in form.SECTIONS}
    assert {'legal_name', 'fein', 'sic_code', 'total_employees', 'employee_count'} <= {
        q['key'] for q in form.QUESTIONS if q['need'] == 'Q'
    }
    assert _q('waive_reason')['need'] == 'C'
    assert _q('situs_state')['options'] == form.STATES
    assert form.GUIDANCE not in form.BY_KEY and form.GUIDANCE in form.ANSWER_KEYS
    assert all(q['type'] in form.TYPES for q in form.QUESTIONS)
    assert all(q['shown_when']['field'] in form.BY_KEY for q in form.QUESTIONS if q.get('shown_when'))
