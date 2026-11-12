"""The reformat of a one-row-per-benefit census (plan.md §5.3.2 step 3; C13). Pure."""

from census import pivot
from census.importer.read import Table

HEAD = ['Emp ID', 'Relationship', 'First Name', 'Last Name', 'DOB', 'Benefit', 'Plan', 'Tier']


def rows_for(people, benefits=(('Medical', 'Gold PPO'), ('Dental', 'Dental Plus'), ('Vision', 'Vision Basic'))):
    """One row per person per benefit. people: [(emp id, relationship, first, last, dob)]."""
    return [[*person, benefit, plan, 'EE'] for person in people for benefit, plan in benefits]


PEOPLE = [
    ('E1', 'Employee', 'Avery', 'One', '01/01/1980'),
    ('E1', 'Spouse', 'Blake', 'One', '02/02/1981'),
    ('E2', 'Employee', 'Casey', 'Two', '03/03/1982'),
    ('E3', 'Employee', 'Dana', 'Three', '04/04/1983'),
]


def reshaped(rows, headers=HEAD, reformat=True):
    return pivot.reshape(Table('Census', headers, rows, list(range(2, len(rows) + 2))), reformat)


def test_C13_a_benefit_per_row_file_becomes_a_person_per_row():
    table, recipe, conflicts = reshaped(rows_for(PEOPLE))
    assert recipe['applied'] is True and recipe['confidence'] >= 0.8
    assert recipe['lines'] == ['medical', 'dental', 'vision']
    assert (recipe['source_rows'], recipe['employee_rows'], recipe['dependent_rows']) == (12, 3, 1)
    assert table.headers[:5] == ['Emp ID', 'Relationship', 'First Name', 'Last Name', 'DOB']
    assert 'Medical Tier' in table.headers and 'Vision Effective Date' in table.headers
    assert [row[2] for row in table.rows] == ['Avery', 'Blake', 'Casey', 'Dana']  # each family: employee, dependents
    assert table.numbers == []  # no one cell holds a reshaped value
    assert conflicts == []


def test_C13_only_the_recipe_is_stored_never_a_row():
    _table, recipe, _ = reshaped(rows_for(PEOPLE))
    assert set(recipe) == set(pivot.STORED)
    assert 'Avery' not in str(recipe) and '1980' not in str(recipe)


def test_C13_an_ordinary_roster_is_left_alone():
    rows = [['E1', 'Employee', 'Avery', 'One', '01/01/1980', '', 'Gold PPO', 'EE']]
    rows += [[f'E{n}', 'Employee', f'P{n}', 'X', f'01/0{n}/1990', '', 'Gold PPO', 'EE'] for n in range(2, 8)]
    table, recipe, _ = reshaped(rows)
    assert recipe == {} and table.rows == rows


def test_C13_the_grey_band_needs_attention_and_maps_as_it_is():
    headers = ['Emp ID', 'Benefit', 'Plan', 'Tier']  # benefits named, but no column tells who each row is
    rows = [[f'E{n // 3}', benefit, 'Gold PPO', 'EE'] for n, benefit in enumerate(['Medical', 'Dental', 'Vision'] * 2)]
    table, recipe, _ = reshaped(rows, headers)
    assert recipe['applied'] is False and recipe['reason'] == pivot.ATTENTION
    assert pivot.needs_attention(recipe)
    assert table.rows == rows


def test_C13_unknown_benefits_refuse_with_a_reason():
    rows = rows_for(PEOPLE, (('Medical', 'Gold'), ('Pet insurance', 'Paws'), ('Dental', 'Den')))
    rows += rows_for(PEOPLE, (('Legal shield', 'L'),))
    _table, recipe, _ = reshaped(rows)
    assert recipe['applied'] is False
    assert "name a benefit we don't recognize" in recipe['reason']
    assert pivot.needs_attention(recipe)


def test_C13_a_duplicate_benefit_row_keeps_the_first_and_says_so():
    rows = rows_for(PEOPLE) + [['E2', 'Employee', 'Casey', 'Two', '03/03/1982', 'Medical', 'Silver HMO', 'EE']]
    table, recipe, conflicts = reshaped(rows)
    assert recipe['applied'] is True
    medical_plan = table.headers.index('Medical Plan')
    assert table.rows[2][medical_plan] == 'Gold PPO'
    assert conflicts == ['Casey Two has two medical rows (Gold PPO / Silver HMO) — kept Gold PPO']


def test_C13_use_the_original_file_instead():
    rows = rows_for(PEOPLE)
    table, recipe, conflicts = reshaped(rows, reformat=False)
    assert recipe['applied'] is False and recipe['declined'] is True and not pivot.needs_attention(recipe)
    assert table.rows == rows and conflicts == []
