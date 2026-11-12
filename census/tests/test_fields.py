"""The census columns, storing a value, and the one requiredness rule (plan.md §4.4, §5.3.1, §5.3.3; OQ16, OQ17)."""

import pytest

from census import fields, values
from census.fields import DEPENDENT, EMPLOYEE, Context

QUOTING = Context(['medical', 'dental'], medical_in_force=True)
NEW_GROUP = Context(['medical'], medical_in_force=False)

# (key, kind, context, rules, carrier_required, required?)
REQUIRED = [
    ('first_name', DEPENDENT, NEW_GROUP, None, None, True),  # A: every person
    ('gender', DEPENDENT, NEW_GROUP, None, None, True),
    ('zip', EMPLOYEE, NEW_GROUP, None, None, True),  # E
    ('zip', DEPENDENT, NEW_GROUP, None, None, False),  # a dependent inherits the employee's ZIP
    ('hours_per_week', EMPLOYEE, NEW_GROUP, None, None, True),
    ('hours_per_week', DEPENDENT, NEW_GROUP, None, None, False),
    ('medical_tier', EMPLOYEE, NEW_GROUP, None, None, True),  # L:medical
    ('dental_tier', EMPLOYEE, NEW_GROUP, None, None, False),  # dental not requested
    ('dental_tier', EMPLOYEE, QUOTING, None, None, True),
    ('medical_tier', DEPENDENT, QUOTING, None, None, False),  # a dependent inherits the election
    ('medical_plan', EMPLOYEE, QUOTING, None, None, True),  # M: requested and in force
    ('medical_plan', EMPLOYEE, NEW_GROUP, None, None, False),  # a group with no medical today
    ('ssn', EMPLOYEE, QUOTING, None, None, False),  # OQ16: optional
    ('ssn', EMPLOYEE, QUOTING, {'ssn': 'required'}, None, True),  # OQ17: Required per deal
    ('dob', EMPLOYEE, QUOTING, {'dob': 'waived'}, None, False),  # Waived beats A
    ('medical_tier', EMPLOYEE, QUOTING, {'medical_tier': 'waived'}, None, False),
    ('dental_tier', DEPENDENT, QUOTING, {'dental_tier': 'required'}, None, False),  # nothing reaches past step 1
    ('address1', EMPLOYEE, NEW_GROUP, None, {'address1': {'employee': ['Aetna'], 'dependent': []}}, True),
    ('address1', DEPENDENT, NEW_GROUP, None, {'address1': {'employee': ['Aetna'], 'dependent': []}}, False),
    ('address1', DEPENDENT, NEW_GROUP, None, {'address1': {'employee': [], 'dependent': ['UHC']}}, True),
    ('address1', EMPLOYEE, NEW_GROUP, {'address1': 'waived'}, {'address1': {'employee': ['Aetna']}}, False),
    ('city', EMPLOYEE, QUOTING, None, None, False),
]


@pytest.mark.parametrize(('key', 'kind', 'context', 'rules', 'carrier', 'expected'), REQUIRED)
def test_C22_is_required_table(key, kind, context, rules, carrier, expected):
    assert fields.is_required(key, kind, context, rules, carrier) is expected


def test_C22_the_columns_follow_section_4_4_in_display_order():
    assert len(fields.FIELDS) == len(set(fields.KEYS))
    assert fields.KEYS[:3] == ['ext_emp_id', 'first_name', 'middle_name']
    assert {'medical_tier', 'dental_tier', 'vision_tier'} == set(fields.TIER_KEYS)
    assert all(field['help'] for field in fields.FIELDS)
    assert fields.choices('dental_tier')[-1] == ('Waived', 'Waived: declined this line')


# (key, raw, stored)
CLEANED = [
    ('medical_tier', ' employee + spouse ', 'ES'),
    ('dental_tier', 'EF', 'FAM'),
    ('vision_tier', 'n/a', 'Waived'),
    ('medical_tier', 'Gold', 'Gold'),  # kept as typed; validation says why
    ('dob', '1/5/1980', '1980-01-05'),
    ('dob', '01/05/80', '1980-01-05'),
    ('dob', '1980-01-05', '1980-01-05'),
    ('dob', '01/05/1980 00:00', '1980-01-05'),
    ('dob', 'sometime', 'sometime'),
    ('ssn', '123456789', '123-45-6789'),
    ('ssn', '123-45-678', '123-45-678'),
    ('annual_salary', '$52,000.50', '52000.50'),
    ('hours_per_week', '40', '40'),
    ('hours_per_week', 'full', 'full'),
    ('gender', 'female', 'F'),
    ('gender', 'X', 'X'),
    ('zip', '2134', '02134'),
    ('zip', '021341234', '02134-1234'),
    ('zip', '33101', '33101'),
    ('state', 'fl', 'FL'),
    ('work_state', ' ga ', 'GA'),
    ('first_name', '  Avery ', 'Avery'),
    ('first_name', '', ''),
]


@pytest.mark.parametrize(('key', 'raw', 'stored'), CLEANED)
def test_C16_clean_table(key, raw, stored):
    assert values.clean(key, raw) == stored


def test_OQ16_an_ssn_is_shown_masked():
    assert values.mask_ssn('123-45-6789') == '***-**-6789'
    assert values.masked_last4('•••-••-6789') == '6789'
    assert values.masked_last4('123-45-6789') is None
