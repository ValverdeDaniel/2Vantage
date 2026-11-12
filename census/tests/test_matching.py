"""Matching a file's people to the roster (plan.md §5.3.2 step 7; C17, L112). Pure."""

import pytest

from census import matching


def member(member_id, kind='employee', employee_id=None, origin='import', removed=False, position=0, **values):
    return {
        'id': member_id,
        'kind': kind,
        'employee_id': employee_id,
        'position': position,
        'values': values,
        'sources': {key: {'origin': origin} for key in values},
        'client': {},
        'added_by_link': None,
        'removed': removed,
    }


def person(kind='employee', parent=None, **values):
    return {'kind': kind, 'parent': parent, 'values': values, 'cells': {}, 'low': []}


# (roster, incoming people, {incoming index: matched member id})
IDENTITIES = [
    # the employer's id first
    ([member(1, ext_emp_id='E1', last_name='Smith')], [person(ext_emp_id='e1', last_name='Smyth')], {0: 1}),
    # then the SSN
    ([member(1, ssn='111-22-3333')], [person(ssn='111223333', first_name='A')], {0: 1}),
    # then last name, first name and birth date, without case
    (
        [member(1, last_name='Smith', first_name='Avery', dob='1980-01-15')],
        [person(last_name='SMITH', first_name='avery', dob='1980-01-15')],
        {0: 1},
    ),
    # an identity two people share identifies nobody
    (
        [
            member(1, last_name='Lee', first_name='Robin', dob='1990-01-01'),
            member(2, last_name='Lee', first_name='Robin', dob='1990-01-01'),
        ],
        [person(last_name='Lee', first_name='Robin', dob='1990-01-01')],
        {},
    ),
    # a name alone is no identity
    (
        [member(1, last_name='Lee', first_name='Robin', dob='1990-01-01')],
        [person(last_name='Lee', first_name='Robin')],
        {},
    ),
]


@pytest.mark.parametrize(('roster', 'people', 'matched'), IDENTITIES)
def test_C17_employee_identity_table(roster, people, matched):
    assert matching.match(people, roster).matched == matched


def test_C17_dependents_match_only_inside_their_family():
    roster = [
        member(1, ext_emp_id='E1'),
        member(2, 'dependent', 1, relationship='Child', first_name='Kit', position=1),
        member(3, 'dependent', 1, relationship='Child', first_name='Lou', position=2),
        member(4, ext_emp_id='E2', position=3),
        member(
            5, 'dependent', 4, relationship='Spouse', first_name='Mo', last_name='Two', dob='1980-02-02', position=4
        ),
    ]
    people = [
        person(ext_emp_id='E1'),
        person('dependent', 0, relationship='Child'),  # by relationship and order: the first child
        person('dependent', 0, relationship='Child'),
        person(ext_emp_id='E3'),
        person('dependent', 3, relationship='Spouse', first_name='Mo', last_name='Two', dob='1980-02-02'),
    ]
    found = matching.match(people, roster)
    assert found.matched == {0: 1, 1: 2, 2: 3}  # Mo moved family: not matched across families
    assert found.created == [3, 4]
    assert found.removed == [4, 5]


# (stored value, its origin, the file's value, changed to)
KEEP = [
    ('Gold', 'import', 'Silver', 'Silver'),  # a file's value moves
    ('Gold', 'ai', 'Silver', 'Silver'),
    ('Gold', 'typed', 'Silver', None),  # what a person entered stays
    ('Gold', 'relay', 'Silver', None),
    ('Gold', 'client', 'Silver', None),
    (None, None, 'Silver', 'Silver'),  # a blank fills
    ('Gold', 'import', 'Gold', None),  # equal: nothing, not even the source
]


@pytest.mark.parametrize(('stored', 'origin', 'incoming', 'expected'), KEEP)
def test_C17_keep_rule_table(stored, origin, incoming, expected):
    values = {'medical_plan': stored} if stored else {}
    sources = {'medical_plan': {'origin': origin}} if stored else {}
    changed = matching.changes_for(values, sources, {'medical_plan': incoming})
    assert changed == ({'medical_plan': expected} if expected else {})


def test_C17_a_blank_in_the_file_keeps_the_stored_value():
    assert matching.changes_for({'zip': '33101'}, {'zip': {'origin': 'import'}}, {}) == {}


def test_C17_people_missing_from_the_file_go_softly_unless_someone_worked_on_them():
    roster = [
        member(1, ext_emp_id='E1'),
        member(2, ext_emp_id='E2'),
        member(3, 'dependent', 2, relationship='Child', first_name='Kit', position=1),
        member(4, ext_emp_id='E4', origin='typed'),
        member(5, ext_emp_id='E5'),
        member(6, 'dependent', 5, origin='typed', relationship='Spouse', first_name='Mo'),
        member(7, ext_emp_id='E7', removed=True),
    ]
    found = matching.match([person(ext_emp_id='E1')], roster)
    assert found.removed == [2, 3]
    assert found.kept == [4, 5, 6]
    assert found.why == {4: 'has values a person entered', 5: 'a dependent is kept', 6: 'has values a person entered'}


def test_C17_a_removed_person_comes_back_by_identity():
    roster = [member(1, ext_emp_id='E1', removed=True), member(2, 'dependent', 1, relationship='Spouse', removed=True)]
    found = matching.match([person(ext_emp_id='E1'), person('dependent', 0, relationship='Spouse')], roster)
    assert found.matched == {0: 1, 1: 2} and found.restored == {1, 2}
