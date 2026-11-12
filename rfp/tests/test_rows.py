"""One format's rows from the census (plan.md §9.8 "Rows" and "Cells"; K92, K97; OQ61). Pure: synthetic people in."""

from datetime import date

from rfp.formats import definitions, rows

from .roster import crowd, dependent, employee, person

WARNER = definitions.DEFINITIONS['warner_census']
AETNA = definitions.DEFINITIONS['aetna_gateway']
ANGLE = definitions.DEFINITIONS['angle']
UHC = definitions.DEFINITIONS['uhc']
ALL_LINES = ['medical', 'dental', 'vision', 'basic_life_add', 'std', 'ltd']
EFFECTIVE = date(2027, 1, 1)


def cells(fmt, built, ri):
    """{header (or hint): value} of one built row; a repeated header keeps its first column."""
    out = {}
    for column, value in zip(fmt['columns'], built.rows[ri], strict=True):
        out.setdefault(column.get('header') or column.get('hint'), value)
    return out


def column_of(fmt, field=None, source=None, line=None):
    return next(
        i
        for i, c in enumerate(fmt['columns'])
        if (field and c.get('field') == field and (line is None or c.get('line') == line))
        or (source and c.get('source') == source)
    )


def test_K92_each_employee_is_followed_by_its_own_dependents_and_orphans_go_last():
    people = [employee(1), employee(2), dependent(3, 1), dependent(4, 2), person(5, 'dependent', 99, first_name='X')]
    built = rows.build(WARNER, people, ALL_LINES, EFFECTIVE)
    assert [p['id'] for p in built.people] == [1, 3, 2, 4, 5]


def test_K92_relationship_tokens_are_spelled_the_carriers_way():
    people = [
        employee(1),
        dependent(2, 1, relationship='Wife'),
        dependent(3, 1, relationship='Domestic partner'),
        dependent(4, 1, relationship='Stepchild'),
    ]
    warner = rows.build(WARNER, people, ALL_LINES, EFFECTIVE)
    assert [r[0] for r in warner.rows] == ['Employee', 'Spouse/Partner', 'Spouse/Partner', 'Child/Dependent']
    aetna = rows.build(AETNA, people, ALL_LINES, EFFECTIVE)
    member_type = column_of(AETNA, source='row:member_type')
    assert [r[member_type] for r in aetna.rows] == ['EE', 'SP', 'SP', 'CH']
    uhc = rows.build(UHC, people, ALL_LINES, EFFECTIVE)
    assert [r[0] for r in uhc.rows] == ['Employee', 'Dependent', 'Dependent', 'Dependent']
    assert [r[1] for r in uhc.rows] == ['', 'Spouse', 'Domestic Partner', 'Child']


def test_K92_a_dependent_with_no_relationship_goes_out_as_a_child_and_says_so_without_a_name():
    built = rows.build(WARNER, [employee(1), dependent(2, 1, relationship='')], ALL_LINES, EFFECTIVE)
    assert built.rows[1][0] == 'Child/Dependent'
    note = next(n for n in built.notes if n['code'] == 'relationship_default')
    assert note['row_ids'] == [2]
    assert 'Kid2' not in note['text'] and '1 dependent has no relationship' in note['text']


def test_K92_tiers_translate_and_a_token_the_carrier_lacks_goes_out_blank_with_a_note():
    people = [employee(1, medical_tier='FAM'), employee(2, medical_tier='Waived'), employee(3, medical_tier='ES')]
    warner = rows.build(WARNER, people, ['medical'], EFFECTIVE)
    tier = column_of(WARNER, field='medical_tier')
    assert [r[tier] for r in warner.rows] == ['EF', 'Waive', 'ES']
    angle = rows.build(ANGLE, people, ['medical'], EFFECTIVE)
    tier = column_of(ANGLE, field='medical_tier')
    assert [r[tier] for r in angle.rows] == ['Employee+Family', '', 'Employee+Spouse']
    note = next(n for n in angle.notes if n['code'] == 'no_carrier_code')
    assert (note['token'], note['count']) == ('WAIVE', 1)


def test_K92_status_gender_zip_and_initial_transforms():
    people = [
        employee(1, employment_status='COBRA continuation', gender='female', zip='7030', middle_name='quinn'),
        employee(2, employment_status='Terminated', gender='Male', zip='33101-1234'),
    ]
    uhc = rows.build(UHC, people, ALL_LINES, EFFECTIVE)
    first, second = cells(UHC, uhc, 0), cells(UHC, uhc, 1)
    assert first['*Employee Status'] == 'Cobra' and second['*Employee Status'] == 'Active'
    assert (first['*Gender'], second['*Gender']) == ('Female', 'Male')
    assert (first['Zip Code (Required if Level Funded)'], second['Zip Code (Required if Level Funded)']) == (
        '07030',
        '33101',
    )
    assert first['Middle Initial (optional)'] == 'Q'
    assert any(n['code'] == 'terminated_active' and n['row_ids'] == [2] for n in uhc.notes)


def test_K92_a_line_not_quoted_leaves_its_columns_blank_and_dependents_never_get_employee_only_cells():
    people = [employee(1, dental_tier='ES', emp_class='Hourly'), dependent(2, 1)]
    built = rows.build(WARNER, people, ['medical'], EFFECTIVE)
    assert built.rows[0][column_of(WARNER, field='dental_tier')] == ''
    assert built.rows[0][column_of(WARNER, field='medical_tier')] == 'EE'
    classes = [i for i, c in enumerate(WARNER['columns']) if c.get('field') == 'emp_class']
    assert [built.rows[0][i] for i in classes] == ['Hourly', 'Hourly']  # OQ109: S and X both
    assert [built.rows[1][i] for i in classes] == ['', '']


def test_K92_a_deal_quoting_nothing_gets_every_column():
    built = rows.build(WARNER, [employee(1, dental_tier='ES')], [], EFFECTIVE)
    assert built.rows[0][column_of(WARNER, field='dental_tier')] == 'ES'


def test_K92_a_dependent_inherits_the_employees_zip_and_county():
    people = [employee(1, zip='70112'), dependent(2, 1)]
    built = rows.build(WARNER, people, ALL_LINES, EFFECTIVE)
    zip_col, county_col = column_of(WARNER, field='zip'), column_of(WARNER, source='derive:county')
    assert built.rows[1][zip_col] == '70112'
    assert built.rows[0][county_col] == built.rows[1][county_col] == 'Orleans Parish'


def test_K92_a_typed_county_wins_over_the_crosswalk_and_an_unknown_zip_stays_blank():
    people = [employee(1, county='Typed County'), employee(2, zip='20500')]
    built = rows.build(WARNER, people, ALL_LINES, EFFECTIVE)
    county_col = column_of(WARNER, source='derive:county')
    assert [r[county_col] for r in built.rows] == ['Typed County', '']


def test_K92_age_is_measured_at_the_effective_date():
    people = [employee(1, dob='1985-03-14'), employee(2, dob='')]
    built = rows.build(UHC, people, ALL_LINES, date(2027, 3, 14))
    age = column_of(UHC, source='derive:age')
    assert [r[age] for r in built.rows] == ['42', '']


def test_K92_out_of_area_is_no_for_the_lower_48_and_blank_with_a_warning_elsewhere():
    people = [employee(1, zip='33101'), employee(2, zip='96813'), employee(3, zip='')]
    built = rows.build(UHC, people, ALL_LINES, EFFECTIVE)
    area = column_of(UHC, source='derive:out_of_area')
    assert [r[area] for r in built.rows] == ['No', '', '']
    assert any('1 member is in Hawaii' in text for text in built.warnings)


def test_K92_enroll_sources_print_when_an_amount_is_on_file():
    people = [employee(1, annual_salary='61500', basic_life_amount='50000'), employee(2)]
    built = rows.build(WARNER, people, ALL_LINES, EFFECTIVE)
    pay_mode = column_of(WARNER, source='row:enroll:annual_salary')
    life = column_of(WARNER, source='row:enroll:basic_life_amount')
    assert [(r[pay_mode], r[life]) for r in built.rows] == [('Annual', 'Enroll'), ('', '')]


def test_K74_a_blank_tier_is_counted_once_per_employee_and_column():
    people = [employee(i, medical_tier='', dental_tier='', vision_tier='') for i in range(1, 10)]
    built = rows.build(WARNER, people, ['medical', 'dental', 'vision'], EFFECTIVE)
    blanks = [text for text in built.warnings if 'have no "COVERAGE TYPE"' in text]
    assert len(blanks) == 3 and all(text.startswith('9 employees') for text in blanks)
    assert any('(Dental)' in text for text in blanks)


def test_K92_required_blanks_are_marked_but_never_a_dependents_tier():
    people = [employee(1, gender=''), dependent(2, 1)]
    built = rows.build(AETNA, people, ['medical'], EFFECTIVE)
    gender = column_of(AETNA, field='gender')
    assert (0, gender) in built.missing
    assert not any(ri == 1 for ri, _ci in built.missing)


def test_K97_OQ61_a_roster_past_the_cap_warns_how_many_did_not_fit():
    built = rows.build(WARNER, crowd(503), ['medical'], EFFECTIVE)
    assert len(built.rows) == 503
    assert rows.overflow_text(WARNER, 503) in built.warnings
    assert 'room for 500 people; the last 3 on the census do not fit' in rows.overflow_text(WARNER, 503)
    assert 'CSV for their portal carries everyone' in rows.overflow_text(ANGLE, 214)


def test_K92_values_print_as_stored_only_never_a_pending_client_answer():
    found = employee(1, gender='F')
    found['client'] = {'gender': {'status': 'pending', 'value': 'M'}}
    built = rows.build(AETNA, [found], ['medical'], EFFECTIVE)
    assert built.rows[0][column_of(AETNA, field='gender')] == 'F'
