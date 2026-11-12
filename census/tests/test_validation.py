"""Census validation, one severity word (plan.md §5.3.4; C21, C3). Pure; the clock is a fixed date."""

import datetime

import pytest

from census import validation

TODAY = datetime.date(2027, 1, 15)


def emp(person_id, **values):
    return {'id': person_id, 'kind': 'employee', 'employee_id': None, 'values': values}


def dep(person_id, employee_id, **values):
    return {'id': person_id, 'kind': 'dependent', 'employee_id': employee_id, 'values': values}


def codes(people):
    found = validation.validate(people, TODAY)
    return {(pid, key): [(i['code'], i['severity']) for i in listed] for (pid, key), listed in found.items()}


# (people, {(id, key): [(code, severity)]}) — every row of §5.3.4 but missing_required (counted apart)
RULES = [
    ([emp(1, ssn='123-45-678')], {(1, 'ssn'): [('ssn_format', 'error')]}),
    ([emp(1, ssn='666-12-3456')], {(1, 'ssn'): [('ssn_invalid', 'error')]}),
    ([emp(1, ssn='912-34-5678')], {(1, 'ssn'): [('ssn_invalid', 'error')]}),
    (
        [emp(1, ssn='123-45-6789'), emp(2, ssn='123456789')],
        {(2, 'ssn'): [('ssn_duplicate', 'error')], (1, 'ssn'): [('ssn_duplicate', 'error')]},
    ),
    (
        [
            emp(1, last_name='Lee', first_name='Robin', dob='1990-01-01'),
            emp(2, last_name='LEE', first_name='robin', dob='1990-01-01'),
        ],
        {(2, 'last_name'): [('person_duplicate', 'warning')], (1, 'last_name'): [('person_duplicate', 'warning')]},
    ),
    ([emp(1, dob='sometime')], {(1, 'dob'): [('dob_unparseable', 'error')]}),
    ([emp(1, dob='2027-01-16')], {(1, 'dob'): [('dob_future', 'error')]}),
    ([emp(1, dob='1916-01-14')], {(1, 'dob'): [('dob_age', 'error')]}),
    ([emp(1, dob='2013-01-16')], {(1, 'dob'): [('dob_young', 'warning')]}),
    ([emp(1, dob='2013-01-15')], {}),  # 14 today
    ([emp(1, zip='3310')], {(1, 'zip'): [('zip_format', 'warning')]}),
    ([emp(1, zip='33101-1234', state='FL')], {}),
    ([emp(1, state='Fla')], {(1, 'state'): [('state_format', 'warning')]}),
    ([emp(1, dental_tier='Gold')], {(1, 'dental_tier'): [('tier_unknown', 'error')]}),
    ([emp(1, vision_tier='Waived', medical_tier='EE')], {}),  # a waiver is an answer
    ([emp(1), dep(2, 1)], {(2, 'relationship'): [('dep_relationship', 'error')]}),
    ([dep(2, None, relationship='Child')], {(2, 'relationship'): [('dep_orphan', 'error')]}),
    (
        [emp(1, medical_tier='EE'), dep(2, 1, relationship='Child')],
        {(1, 'medical_tier'): [('tier_ee_deps', 'warning')]},
    ),
    (
        [emp(1, medical_tier='EC'), dep(2, 1, relationship='Spouse')],
        {(1, 'medical_tier'): [('tier_ec_no_child', 'warning')]},
    ),
    ([emp(1, medical_tier='EC'), dep(2, 1, relationship='Stepchild')], {}),
    (
        [emp(1, medical_tier='ES'), dep(2, 1, relationship='Son')],
        {(1, 'medical_tier'): [('tier_es_no_spouse', 'warning')]},
    ),
    ([emp(1, medical_tier='ES'), dep(2, 1, relationship='Domestic Partner')], {}),
    ([emp(1, medical_tier='FAM')], {(1, 'medical_tier'): [('tier_fam_no_deps', 'warning')]}),
    (
        [emp(1, hire_date='2027-02-01', effective_date='2027-01-01')],
        {(1, 'hire_date'): [('hire_after_effective', 'warning')]},
    ),
]


@pytest.mark.parametrize(('people', 'expected'), RULES)
def test_C21_validation_table(people, expected):
    assert codes(people) == expected


def test_C21_messages_say_what_is_wrong():
    found = validation.validate([emp(1, ssn='123-45-678', dob='1916-01-14')], TODAY)
    assert found[(1, 'ssn')][0]['message'] == 'SSN "123-45-678" is not 9 digits'
    assert found[(1, 'dob')][0]['message'] == 'Age 111 — check the birth year'
    assert validation.counts(found) == (2, 0)


def test_C3_the_duplicate_person_warning_counts_as_a_warning():
    people = [
        emp(1, last_name='Lee', first_name='R', dob='1990-01-01'),
        emp(2, last_name='Lee', first_name='R', dob='1990-01-01'),
    ]
    assert validation.counts(validation.validate(people, TODAY)) == (0, 2)
