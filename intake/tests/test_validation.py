"""The intake's inline checks, one row per rule of plan.md §5.2's table (B8; OQ50 default: they never block). Pure."""

import datetime

import pytest

from intake import validation

TODAY = datetime.date(2026, 11, 11)


def _issues(answers, **kwargs):
    return validation.validate_intake(answers, today=TODAY, **kwargs)


@pytest.mark.parametrize(
    ('answers', 'key', 'code', 'severity', 'message'),
    [
        ({'fein': '12-345'}, 'fein', 'fein_format', 'error', 'FEIN "12-345" is not in XX-XXXXXXX format'),
        (
            {'total_employees': '40', 'employee_count': '45'},
            'employee_count',
            'counts_order',
            'error',
            'Eligible employees (45) exceeds total employees (40)',
        ),
        (
            {'employee_count': '30', 'enrolled_count': '25', 'waiving_count': '6'},
            'enrolled_count',
            'counts_sum',
            'warning',
            'Enrolled + waiving is more than the eligible count — check the numbers',
        ),
        (
            {'situs_state': 'Florida'},
            'situs_state',
            'state_format',
            'warning',
            '"Florida" is not a 2-letter state code',
        ),
        (
            {'states_operating': ['FL', 'Georgia']},
            'states_operating',
            'state_format',
            'warning',
            '"Georgia" is not a 2-letter state code',
        ),
        (
            {'total_employees': '50'},
            'ale_status',
            'ale_suggest',
            'warning',
            '50 employees — likely an ACA Applicable Large Employer; please confirm',
        ),
        (
            {'enrolled_count': '60', 'enrolled_life_count': '104', 'form_5500_required': 'No'},
            'form_5500_required',
            'form_5500_contradiction',
            'error',
            '104 enrolled on at least one benefit line but Form 5500 is marked "No" — did you make a mistake, or is '
            'the group out of compliance? (100+ participants triggers a filing)',
        ),
        (
            {'self_funded': 'Yes', 'pcori_filing': 'No'},
            'pcori_filing',
            'pcori_contradiction',
            'warning',
            'Self-funded groups owe a PCORI filing (IRS Form 720, due July 31) — please double-check this answer',
        ),
        (
            {'hours_threshold': '45'},
            'hours_threshold',
            'hours_range',
            'warning',
            'Hours/week is usually between 1 and 40',
        ),
        (
            {'hours_threshold': '0'},
            'hours_threshold',
            'hours_range',
            'warning',
            'Hours/week is usually between 1 and 40',
        ),
        (
            {'child_age_limit': '17'},
            'child_age_limit',
            'child_age_range',
            'warning',
            'Dependent child age limit is usually 26 (allowed 18–30)',
        ),
    ],
)
def test_B8_each_rule_says_its_words(answers, key, code, severity, message):
    assert _issues(answers)[key] == [{'code': code, 'severity': severity, 'message': message}]


@pytest.mark.parametrize(
    'answers',
    [
        {'fein': '12-3456789'},
        {'fein': '123456789'},
        {'total_employees': '40', 'employee_count': '40'},
        {'employee_count': '30', 'enrolled_count': '25', 'waiving_count': '5'},
        {'enrolled_count': '25'},  # no eligible count: nothing to add up against
        {'situs_state': 'FL', 'states_operating': ['FL', 'GA']},
        {'total_employees': '49'},
        {'total_employees': '72', 'ale_status': 'No'},
        {'enrolled_count': '99', 'form_5500_required': 'No'},
        {'enrolled_count': '120'},  # blank 5500 answer: still gathering, not a contradiction
        {'enrolled_count': '120', 'form_5500_required': 'Yes'},
        {'self_funded': 'No', 'pcori_filing': 'No'},
        {'hours_threshold': '1'},
        {'hours_threshold': '40'},
        {'child_age_limit': '18'},
        {'child_age_limit': '30'},
        {'total_employees': 'many'},  # not a number: no rule reads it
    ],
)
def test_B8_clean_answers_raise_nothing(answers):
    assert _issues(answers) == {}


@pytest.mark.parametrize(
    ('answer', 'funding', 'flagged'),
    [
        ('Yes', 'fully_insured', True),
        ('No', 'level_funded', True),
        ('No', 'self_funded', True),
        ('Yes', 'level_funded', False),
        ('No', 'fully_insured', False),
        ('', 'fully_insured', False),
        ('Yes', '', False),
    ],
)
def test_B8_funding_contradiction_reads_the_medical_line(answer, funding, flagged):
    issues = _issues({'self_funded': answer} if answer else {}, medical_funding=funding)
    if flagged:
        words = {'fully_insured': 'fully insured', 'level_funded': 'level-funded', 'self_funded': 'self-funded'}
        message = f'The medical coverage is recorded as {words[funding]} — check "Are you self-funded?"'
        assert issues == {'self_funded': [{'code': 'funding_contradiction', 'severity': 'warning', 'message': message}]}
    else:
        assert 'self_funded' not in issues


def test_B8_renewal_dates_and_emails_are_keyed_by_their_row():
    coverage = [
        {'id': 1, 'renewal_date': datetime.date(2026, 11, 10)},
        {'id': 2, 'renewal_date': datetime.date(2027, 11, 12)},
        {'id': 3, 'renewal_date': datetime.date(2027, 11, 11)},  # exactly twelve months out: fine
        {'id': 4, 'renewal_date': TODAY},
        {'id': 5, 'renewal_date': None},
    ]
    contacts = [{'id': 7, 'email': 'hr@example'}, {'id': 8, 'email': 'hr@example.com'}, {'id': 9, 'email': ''}]
    issues = _issues({}, coverage=coverage, contacts=contacts)
    assert issues == {
        'coverage:1': [{'code': 'renewal_past', 'severity': 'warning', 'message': 'Renewal date is in the past'}],
        'coverage:2': [
            {'code': 'renewal_far', 'severity': 'warning', 'message': 'Renewal date is more than 12 months out'}
        ],
        'contact:7': [
            {'code': 'email_format', 'severity': 'error', 'message': '"hr@example" is not a valid email address'}
        ],
    }


def test_B8_one_question_can_carry_two_rules_and_others_their_own():
    issues = _issues({'fein': 'x', 'total_employees': '80', 'employee_count': '90', 'hours_threshold': '60'})
    assert set(issues) == {'fein', 'employee_count', 'ale_status', 'hours_threshold'}
    assert [issue['severity'] for issue in issues['employee_count']] == ['error']
