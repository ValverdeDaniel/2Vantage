"""Reading a census file, the offline mapper and building people (plan.md §4.8, §5.3.2; C12, C14, C16). Pure."""

import pytest

from census.importer import CensusFileError, mapping, open_table, read
from census.importer.people import SsnOnFile, build

from .helpers import csv_bytes, xlsx


def test_C12_the_header_row_is_the_first_with_three_labels():
    rows = [
        ['Census for a synthetic group'],
        ['', '01/01/2027', '$1,000'],
        ['Emp ID', 'First', 'Last'],
        ['1', 'A', 'B'],
    ]
    assert read.find_header_row(rows) == 3
    assert read.find_header_row([['1', '2', '3']] * 12) is None


def test_C12_a_csv_reads_with_or_without_a_bom_else_latin_1():
    rows = [['First Name', 'Last Name', 'DOB'], ['Zoë', 'Nuñez', '1/2/1990']]
    for content in (csv_bytes(rows), csv_bytes(rows, 'utf-8'), csv_bytes(rows, 'latin-1')):
        found = open_table('census.csv', content)
        assert found.table.headers == rows[0]
        assert found.table.rows == [rows[1]]
        assert found.table.sheet == 'Sheet1'


def test_C12_rows_keep_their_sheet_numbers_and_blank_rows_go():
    content = xlsx([['First Name', 'Last Name', 'DOB', ''], ['A', 'One', '1/1/1990'], [], ['B', 'Two', '2/2/1990']])
    found = open_table('c.xlsx', content)
    assert found.table.headers == ['First Name', 'Last Name', 'DOB']  # trailing blank header cells dropped
    assert found.table.numbers == [2, 4]
    assert read.cell(found.table, 2, 1) == 'Census!C4'


def test_C12_anything_but_a_sheet_is_refused_without_naming_the_file():
    with pytest.raises(CensusFileError) as refused:
        open_table('Avery Smith roster.pdf', b'%PDF-1.4')
    assert str(refused.value) == 'This file is not a spreadsheet or CSV census file.'
    assert 'Avery' not in str(refused.value)


def test_C14_samples_are_three_values_and_ssns_show_their_last_four():
    content = xlsx(
        [['SSN', 'First Name', 'Last Name'], ['123-45-6789', 'A', 'X'], ['', 'B', 'Y'], ['987654321', 'C', 'Z']]
    )
    found = open_table('c.xlsx', content)
    assert read.samples(found.table, 0) == ['***-**-6789', '***-**-4321']
    assert read.samples(found.table, 1) == ['A', 'B', 'C']


# (headers, the fields proposed, the confidences)
MAPPINGS = [
    (['Emp ID', 'Rel', 'Fname', 'Surname'], ['ext_emp_id', 'relationship', 'first_name', 'last_name'], [0.95] * 4),
    (['Medical Tier', 'Hours / Week', 'ZIP'], ['medical_tier', 'hours_per_week', 'zip'], [0.95] * 3),  # labels
    (['Medical Tier', 'Effective Date'], ['medical_tier', 'effective_date'], [0.95, 0.70]),  # positional, checked
    (['Basic Life Amount', 'Effective Date'], ['basic_life_amount', 'basic_life_effective_date'], [0.95, 0.70]),
    (['Dental Tier', 'Effective Date'], ['dental_tier', 'dental_effective_date'], [0.95, 0.70]),
    (['Home Street'], ['address1'], [0.60]),  # fuzzy
    (['Dental Coverage Type'], ['dental_tier'], [0.60]),  # the line word lets the fuzzy pass reach a dental key
    (['Coverage Type'], ['relationship'], [0.60]),  # never a line's key without the line's word (old behaviour)
    (['Plan', 'Plan'], ['medical_plan', ''], [0.95, 0.0]),  # one key, one column: the first claims it
    (['Notes', ''], ['', ''], [0.0, 0.0]),
]


@pytest.mark.parametrize(('headers', 'expected', 'confidence'), MAPPINGS)
def test_C14_offline_mapper_table(headers, expected, confidence):
    proposed = mapping.propose(headers)
    assert [item['field'] for item in proposed] == expected
    assert [item['confidence'] for item in proposed] == confidence
    assert [item['low'] for item in proposed] == [
        bool(f) and c < 0.85 for f, c in zip(expected, confidence, strict=True)
    ]


def test_C15_a_members_choice_takes_the_column_and_a_key_twice_is_refused():
    proposed = mapping.propose(['First Name', 'Notes'])
    chosen, errors = mapping.confirm(proposed, [{'column': 1, 'field': 'middle_name'}])
    assert errors == {} and chosen[1] == {
        'column': 1, 'header': 'Notes', 'field': 'middle_name', 'confidence': 1.0, 'low': False,
    }  # fmt: skip
    _chosen, errors = mapping.confirm(proposed, [{'column': 1, 'field': 'first_name'}])
    assert errors == {'1': ['First Name is mapped to two columns. Map each census column once.']}
    _chosen, errors = mapping.confirm(proposed, [{'column': 1, 'field': 'shoe_size'}])
    assert errors == {'1': ['Unknown census column.']}


def _people(rows, roster=None):
    found = open_table('c.xlsx', xlsx(rows))
    on_file = SsnOnFile(roster or [])
    return build(found.table, mapping.propose(found.table.headers), on_file), on_file


def test_C16_employees_dependents_and_their_links():
    rows = [
        ['Emp ID', 'Relationship', 'First Name', 'Last Name', 'SSN', 'Employee SSN'],
        ['E1', 'Self', 'Avery', 'One', '', '111-22-3333'],
        ['E2', 'EE', 'Blake', 'Two', '222-33-4444', ''],
        ['', 'Spouse', 'Casey', 'One', '', '111223333'],  # by the employee SSN, though another came between
        ['E2', 'Child', 'Dana', 'Two', '', ''],  # by Emp ID
        ['', 'Child', 'Eden', 'Two', '', ''],  # the last employee above
    ]
    people, _ = _people(rows)
    assert [person['kind'] for person in people] == ['employee', 'employee', 'dependent', 'dependent', 'dependent']
    assert people[0]['values']['ssn'] == '111-22-3333'  # copied from the employee SSN
    assert [person['parent'] for person in people] == [None, None, 0, 1, 1]
    assert people[2]['cells']['first_name'] == 'Census!C4'


def test_C16_a_dependent_with_no_employee_above_stays_unlinked():
    people, _ = _people([['Relationship', 'First Name', 'Last Name'], ['Child', 'Eden', 'Two'], ['Employee', 'A', 'B']])
    assert people[0]['kind'] == 'dependent' and people[0]['parent'] is None


def test_C16_low_confidence_columns_are_marked_on_their_values():
    people, _ = _people([['First Name', 'Last Name', 'Home Street'], ['A', 'B', '1 Synthetic Way']])
    assert people[0]['low'] == ['address1']


def test_C16_masked_ssn_restored_only_when_the_last_four_agree():
    roster = [
        {'id': 1, 'employee_id': None, 'values': {'ext_emp_id': 'E1', 'ssn': '111-22-3333'}},
        {'id': 2, 'employee_id': None, 'values': {'ext_emp_id': 'E2', 'ssn': '222-33-4444'}},
    ]
    rows = [
        ['Emp ID', 'First Name', 'SSN'],
        ['E1', 'A', '***-**-3333'],
        ['E2', 'B', '***-**-9999'],
        ['E3', 'C', 'xxx-xx-1'],
    ]
    people, on_file = _people(rows, roster)
    assert people[0]['values']['ssn'] == '111-22-3333'
    assert 'ssn' not in people[1]['values']
    assert people[2]['values']['ssn'] == 'xxx-xx-1'  # not a mask: kept as typed, validation says why
    assert on_file.summary() == {'restored': 1, 'unmatched': 1}
