"""The import door: propose, change, dry run, apply (plan.md §5.3.2, §7.7; C12–C17). Factory deals, synthetic files."""

import pytest

from census import facts, services
from census.models import CensusImport, Member
from deals.activity import KEYS_ONLY, Refused, revert
from deals.models import Activity

from .helpers import HEADERS, family, import_file, imported, roster, xlsx

pytestmark = pytest.mark.django_db

SMITH = family('E1', 'Smith', tier='ES', deps=[('Spouse', 'Blake', '02/02/1981')])
JONES = family(
    'E2',
    'Jones',
    tier='FAM',
    plan='Silver HMO',
    deps=[('Spouse', 'Casey', '03/03/1979'), ('Child', 'Dana', '04/04/2012')],
)
LEE = family('E3', 'Lee', first='Robin', plan='Gold PPO')


def names(listed):
    return sorted(person['name'] for person in listed)


def assert_facts_rebuild(deal):
    assert facts.differences(deal.id) == {}


def test_C12_C14_a_file_on_the_deal_proposes_a_mapping(user, deal):
    imp = import_file(user, deal, xlsx(roster(SMITH, LEE)))
    assert imp.status == CensusImport.PROPOSED
    assert (imp.sheet_name, imp.header_row, imp.first_data_row) == ('Census', 1, 2)
    assert imp.headers == HEADERS
    fields = [item['field'] for item in imp.mapping]
    assert fields == [
        'ext_emp_id', 'relationship', 'first_name', 'last_name', 'dob', 'gender', 'zip', 'hours_per_week',
        'medical_plan', 'medical_tier',
    ]  # fmt: skip
    assert not Member.objects.filter(deal=deal).exists()  # a proposal touches no one


def test_C14_the_import_stores_no_sample_value(user, deal):
    imp = import_file(user, deal, xlsx(roster(SMITH)))
    stored = str(CensusImport.objects.filter(pk=imp.id).values().get())
    for value in ('Smith', 'Avery', 'Blake', '1980', '33101', 'Gold PPO'):
        assert value not in stored


def test_C12_a_file_that_is_not_a_census_sheet_is_refused_in_words(user, deal, api):
    from .helpers import upload

    pdf = upload(user, deal, b'%PDF-1.4\n%%EOF\n', name='roster.pdf')
    answer = api.post(f'/api/deals/{deal.id}/census/imports/', {'document_id': pdf.id}, format='json')
    assert answer.status_code == 400
    assert answer.json() == {'detail': 'This file is not a spreadsheet or CSV census file.'}
    blank = upload(user, deal, xlsx([['1', '2'], ['', '']]))
    answer = api.post(f'/api/deals/{deal.id}/census/imports/', {'document_id': blank.id}, format='json')
    assert answer.json() == {'detail': 'Could not find a header row in this file.'}


def test_C17_the_dry_run_lists_people_and_writes_nothing(user, deal):
    imported(user, deal, xlsx(roster(SMITH, JONES)))
    changed_smith = family('E1', 'Smith', tier='ES', plan='Silver HMO', deps=[('Spouse', 'Blake', '02/02/1981')])
    imp = import_file(user, deal, xlsx(roster(changed_smith, LEE)))
    before, log = list(Member.all_objects.filter(deal=deal).values()), list(Activity.objects.values())
    answer = services.dry_run(imp.id)
    assert list(Member.all_objects.filter(deal=deal).values()) == before
    assert list(Activity.objects.values()) == log
    assert CensusImport.objects.get(pk=imp.id).status == CensusImport.PROPOSED
    assert names(answer['added']) == ['Robin Lee']
    assert names(answer['changed']) == ['Avery Smith']
    assert answer['changed'][0]['columns'] == ['Medical Plan']
    assert answer['cells_changed'] == {str(answer['changed'][0]['id']): ['Medical Plan']}
    assert names(answer['removed']) == ['Avery Jones', 'Casey Jones', 'Dana Jones']
    assert answer['kept'] == []
    assert answer['counts'] == {
        'people': 3, 'employees': 2, 'dependents': 1, 'added': 1, 'changed': 1, 'unchanged': 1, 'removed': 3,
        'kept': 0,
    }  # fmt: skip


def test_C17_apply_writes_the_roster_and_a_key_only_activity_row(user, deal):
    imp = imported(user, deal, xlsx(roster(SMITH, JONES)))
    people = list(Member.objects.filter(deal=deal).order_by('position'))
    assert [(m.kind, m.values['first_name']) for m in people] == [
        ('employee', 'Avery'), ('dependent', 'Blake'), ('employee', 'Avery'), ('dependent', 'Casey'),
        ('dependent', 'Dana'),
    ]  # fmt: skip
    assert people[1].employee_id == people[0].id and people[4].employee_id == people[2].id
    assert people[0].values['dob'] == '1980-01-15'
    assert people[0].sources['dob']['origin'] == 'import'
    assert people[0].sources['dob']['doc'] == imp.document_id
    assert people[0].sources['dob']['cell'] == 'Census!E2'
    row = Activity.objects.filter(deal=deal, area='census', action='imported').get()
    assert row.summary == 'Imported census: 5 people (3 dependents)'
    assert all(isinstance(entry['k'], list) for entry in row.changes)
    assert 'Smith' not in str(row.changes) and '1980' not in str(row.changes)
    with pytest.raises(Refused) as refused:
        revert(row.id, user)
    assert refused.value.sentence == KEYS_ONLY
    assert imp.status == CensusImport.APPLIED and imp.stats['created'] == 5
    assert_facts_rebuild(deal)


def test_C17_a_reimport_moves_only_file_values_and_removes_softly(user, deal):
    imported(user, deal, xlsx(roster(SMITH, JONES)))
    smith = Member.objects.get(deal=deal, values__last_name='Smith', kind='employee')
    smith.values['medical_plan'] = 'Typed Plan'
    smith.sources['medical_plan'] = {'origin': 'typed', 'by': user.id, 'at': '2026-01-01T00:00:00+00:00'}
    smith.save()
    changed = family('E1', 'Smith', tier='EE', plan='Silver HMO', deps=[('Spouse', 'Blake', '02/02/1981')])
    imported(user, deal, xlsx(roster(changed, LEE)))
    smith.refresh_from_db()
    assert smith.values['medical_plan'] == 'Typed Plan'  # what a person typed stays
    assert smith.values['medical_tier'] == 'EE'  # what a file said moves
    jones = Member.all_objects.filter(deal=deal, values__last_name='Jones')
    assert jones.count() == 3 and all(m.removed_at for m in jones)
    assert not Member.objects.filter(deal=deal, values__last_name='Jones').exists()
    assert_facts_rebuild(deal)
    imported(user, deal, xlsx(roster(changed, JONES, LEE)))  # back by identity
    assert Member.objects.filter(deal=deal, values__last_name='Jones').count() == 3
    assert Member.all_objects.filter(deal=deal).count() == 6
    assert_facts_rebuild(deal)


def test_C17_someone_a_person_worked_on_is_kept_and_reported(user, deal):
    imported(user, deal, xlsx(roster(SMITH, JONES)))
    casey = Member.objects.get(deal=deal, values__first_name='Casey')
    casey.values['ssn'] = '123-45-6789'
    casey.sources['ssn'] = {'origin': 'typed', 'by': user.id, 'at': '2026-01-01T00:00:00+00:00'}
    casey.save()
    imp = import_file(user, deal, xlsx(roster(SMITH)))
    answer = services.dry_run(imp.id)
    assert names(answer['kept']) == ['Avery Jones', 'Casey Jones']
    assert names(answer['removed']) == ['Dana Jones']
    services.apply_import(user, imp.id)
    assert sorted(Member.objects.filter(deal=deal).values_list('values__first_name', flat=True)) == [
        'Avery', 'Avery', 'Blake', 'Casey'
    ]  # fmt: skip
    assert_facts_rebuild(deal)


def test_C17_the_same_file_again_changes_no_one(user, deal):
    imported(user, deal, xlsx(roster(SMITH, JONES)))
    before = list(Member.all_objects.filter(deal=deal).values())
    imp = import_file(user, deal, xlsx(roster(SMITH, JONES)))
    answer = services.dry_run(imp.id)
    assert answer['counts']['unchanged'] == 5 and answer['counts']['changed'] == 0
    services.apply_import(user, imp.id)
    assert list(Member.all_objects.filter(deal=deal).values()) == before
    row = Activity.objects.filter(deal=deal, action='imported').latest('id')
    assert row.changes == []


def test_C15_sheet_header_and_first_data_row_can_be_chosen(user, deal):
    warner = [
        ['Census (synthetic)'],
        [],
        ['', 'RELATIONSHIP', 'FIRST', 'LAST', 'DATE OF BIRTH', 'GENDER', 'ZIP CODE', 'COVERAGE TYPE'],
        ['', '', 'First', 'Last', '', '', '', ''],
        ['Ex:', 'Employee', 'Sample', 'Person', '01/01/1970', 'M', '00000', 'EE'],
        [1, 'Employee', 'Avery', 'Smith', '01/15/1980', 'F', '33101', 'ES'],
        [2, 'Spouse/Partner', 'Blake', 'Smith', '02/02/1981', 'M', '33101', ''],
        [3],
        [4],
    ]
    content = xlsx(
        [['Step', 'What to fill in', 'Who'], ['1', 'Everyone', 'HR']],
        sheet='Instructions',
        more={'Census Template': warner},
    )
    imp = import_file(user, deal, content)
    assert imp.sheet_name == 'Instructions'
    assert import_file(
        user, deal, xlsx([['Notes only']], sheet='Read me', more={'Census Template': warner})
    ).sheet_name == ('Census Template')  # a first sheet with no header row: the first sheet that has one
    imp = import_file(user, deal, content)
    imp, changed = services.update_import(user, imp.id, {'sheet_name': 'Census Template'})
    assert imp.header_row == 3 and imp.first_data_row == 4 and 'mapping' in changed
    imp, _ = services.update_import(
        user, imp.id, {'first_data_row': 6, 'mapping': [{'column': 7, 'field': 'medical_tier'}]}
    )
    answer = services.dry_run(imp.id)
    assert names(answer['added']) == ['Avery Smith', 'Blake Smith']  # numbered empty rows are no one
    services.apply_import(user, imp.id)
    avery = Member.objects.get(deal=deal, values__first_name='Avery')
    assert avery.sources['medical_tier']['cell'] == 'Census Template!H6'
    assert 'low' not in avery.sources['medical_tier']  # a column the member chose is no longer a guess


def test_C15_one_census_column_on_two_file_columns_answers_400(user, deal, api):
    imp = import_file(user, deal, xlsx(roster(SMITH)))
    body = {'mapping': [{'column': 0, 'field': 'first_name'}]}
    answer = api.patch(f'/api/census/imports/{imp.id}/', body, format='json')
    assert answer.status_code == 400
    assert 'First Name is mapped to two columns' in str(answer.json())


def test_C15_an_applied_import_refuses_changes_with_a_sentence(user, deal, api):
    imp = imported(user, deal, xlsx(roster(SMITH)))
    answer = api.post(f'/api/census/imports/{imp.id}/apply/')
    assert answer.status_code == 409
    assert 'already applied' in answer.json()['detail']
    assert api.patch(f'/api/census/imports/{imp.id}/', {'first_data_row': 3}, format='json').status_code == 409


def test_C15_a_new_proposal_sets_the_waiting_one_aside(user, deal):
    first = import_file(user, deal, xlsx(roster(SMITH)))
    second = import_file(user, deal, xlsx(roster(LEE)))
    first.refresh_from_db()
    assert first.status == CensusImport.DISCARDED and second.status == CensusImport.PROPOSED
    services.discard_import(user, second.id)
    second.refresh_from_db()
    assert second.status == CensusImport.DISCARDED


def test_C16_masked_ssns_come_back_from_the_roster_or_go_blank(user, deal):
    headers = ['Emp ID', 'First Name', 'Last Name', 'DOB', 'SSN']
    imported(user, deal, xlsx([headers, ['E1', 'Avery', 'Smith', '01/15/1980', '123-45-6789']]))
    masked = [
        headers,
        ['E1', 'Avery', 'Smith', '01/15/1980', '***-**-6789'],
        ['E9', 'Robin', 'Lee', '1/1/1990', 'XXX-XX-1111'],
    ]
    imp = import_file(user, deal, xlsx(masked))
    answer = services.dry_run(imp.id)
    assert answer['masked_ssns'] == {'restored': 1, 'unmatched': 1}
    services.apply_import(user, imp.id)
    assert Member.objects.get(deal=deal, values__first_name='Avery').values['ssn'] == '123-45-6789'
    assert 'ssn' not in Member.objects.get(deal=deal, values__first_name='Robin').values


def test_C15_use_the_original_file_instead_maps_it_as_uploaded(user, deal):
    rows = [['Emp ID', 'First Name', 'Last Name', 'DOB', 'Benefit', 'Plan', 'Tier']]
    for n in range(1, 6):
        for benefit, plan in (('Medical', 'Gold PPO'), ('Dental', 'Dental Plus')):
            rows.append([f'E{n}', f'P{n}', 'Synthetic', f'0{n}/01/1980', benefit, plan, 'EE'])
    imp = import_file(user, deal, xlsx(rows))
    assert imp.pivot['applied'] is True and imp.pivot['lines'] == ['medical', 'dental']
    assert 'Medical Plan' in imp.headers and 'Dental Tier' in imp.headers
    imp, _ = services.update_import(user, imp.id, {'reformat': False})
    assert imp.pivot['applied'] is False and imp.pivot['declined'] is True
    assert imp.headers == rows[0]


def test_C15_remapping_a_file_starts_from_the_last_choices_for_it(user, deal):
    from .helpers import upload

    rows = [['Census (synthetic)'], ['Notes', 'Tier', 'First Name', 'Last Name'], ['x', 'EE', 'Avery', 'Smith']]
    document = upload(user, deal, xlsx(rows))
    imp = services.create_import(user, deal.id, document.id)
    imp, _ = services.update_import(user, imp.id, {'mapping': [{'column': 0, 'field': 'middle_name'}]})
    services.apply_import(user, imp.id)
    again = services.create_import(user, deal.id, document.id)
    assert again.mapping == CensusImport.objects.get(pk=imp.id).mapping
    assert (again.header_row, again.first_data_row) == (2, 3)
