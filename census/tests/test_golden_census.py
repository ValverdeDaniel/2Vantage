"""GD4 against its hand-counted key (plan.md §13.4, Q.4, Q.9 row 12): its file imports, a re-import lists who changes,
the Warner-template copy imports, and the tier counts equal the hand count. GD4 is read-only here: what writes runs on
a factory deal with GD4's own files."""

import pytest

from census import facts, rollup, services
from census.models import CensusImport, Member
from deals.models import Activity
from documents.models import Document

from .helpers import upload

pytestmark = pytest.mark.django_db

BUCKETS = ('EE', 'ES', 'EC', 'FAM', 'waived', 'blank')
LINES = {'medical': 'medical_tier', 'dental': 'dental_tier', 'vision': 'vision_tier'}
# The Warner template's columns the mapper cannot read alone (§4.8 is unchanged): a member picks them in the dialog.
WARNER_CHOICES = [
    {'column': 3, 'field': 'last_name'},  # D, under the merged MEMBER NAME
    {'column': 9, 'field': 'employment_status'},  # J, EE STATUS
    {'column': 10, 'field': 'medical_tier'},  # K, COVERAGE TYPE under medical
    {'column': 13, 'field': 'dental_tier'},
    {'column': 14, 'field': 'dental_plan'},
    {'column': 15, 'field': 'vision_tier'},
    {'column': 16, 'field': 'vision_plan'},
    {'column': 18, 'field': 'emp_class'},
]


def _counts(stored, key):
    return {line: {b: stored['tiers'][column][b] for b in BUCKETS} for line, column in LINES.items()}


def _by_plan(stored):
    return {
        line: {text: {b: counts[b] for b in BUCKETS} for text, counts in stored['by_plan'][line].items()}
        for line in LINES
    }


def assert_census_equals_key(deal, key):
    stored = facts.stored(deal.id)
    summary = facts.summary(stored)
    assert (summary['employees'], summary['dependents']) == (key['employees'], key['dependents'])
    assert _counts(stored['rollup'], key) == key['tiers']
    assert _by_plan(stored['rollup']) == key['by_plan']
    for line, column in LINES.items():
        assert rollup.enrolled(stored['rollup']['tiers'][column]) == key['enrolled'][line], line
    assert (summary['required_total'], summary['missing_required']) == (key['required_total'], key['missing_required'])
    assert (summary['errors'], summary['warnings'], summary['readiness_pct'], summary['ok']) == (
        key['errors'],
        key['warnings'],
        key['readiness_pct'],
        key['ok'],
    )


def _file(deal, name):
    document = Document.objects.get(deal=deal, original_name=name)
    with document.file.open('rb') as handle:
        return handle.read()


def test_C39_C41_GD4_tier_counts_equal_the_hand_count(golden, golden_keys):
    deal, _refs, _spec = golden['GD4']
    assert_census_equals_key(deal, golden_keys['GD4']['census'])
    assert facts.differences(deal.id) == {}


def test_C45_C46_GD4_fte_and_the_65_plus_count(golden, golden_keys, api):
    deal, _refs, _spec = golden['GD4']
    key = golden_keys['GD4']['census']
    derived = api.get(f'/api/deals/{deal.id}/census/').json()['derived']
    assert (derived['fte'], derived['aged_65']) == (key['fte'], key['aged_65'])
    spouses = Member.objects.filter(deal=deal, kind='dependent', values__relationship='Spouse').count()
    assert (spouses, key['dependents'] - spouses) == (key['spouses'], key['children'])


def test_C12_C14_GD4_file_imports_through_the_dialog_and_a_reimport_lists_no_change(user, deal, golden, golden_keys):
    gd4, _refs, spec = golden['GD4']
    content = _file(gd4, spec['census']['file'])
    first = services.create_import(user, deal.id, upload(user, deal, content, spec['census']['file']).id)
    checked = {item['header']: item['field'] for item in first.mapping if item['low']}
    assert checked == {'Home Street': 'address1', 'Effective Date': 'effective_date'}  # the dialog asks to check
    assert [item['header'] for item in first.mapping if not item['field']] == ['Notes']
    services.apply_import(user, first.id)
    assert_census_equals_key(deal, golden_keys['GD4']['census'])
    again = services.create_import(user, deal.id, upload(user, deal, content, spec['census']['file']).id)
    answer = services.dry_run(again.id)
    assert answer['counts']['unchanged'] == answer['counts']['people']
    assert answer['added'] == answer['changed'] == answer['removed'] == answer['kept'] == []


def test_C15_GD4_the_warner_template_copy_imports_with_its_rows_chosen(user, deal, golden, golden_keys):
    gd4, _refs, spec = golden['GD4']
    warner = spec['census']['warner_file']
    imp = services.create_import(user, deal.id, upload(user, deal, _file(gd4, warner), warner).id)
    assert (imp.sheet_name, imp.header_row) == ('Census Template', spec['census']['warner_header_row'])
    first_row = spec['census']['warner_first_data_row']
    imp, _ = services.update_import(user, imp.id, {'first_data_row': first_row, 'mapping': WARNER_CHOICES})
    services.apply_import(user, imp.id)
    assert_census_equals_key(deal, golden_keys['GD4']['census'])
    assert (
        Member.objects.filter(deal=deal, values__employment_status='Active').count()
        == golden_keys['GD4']['census']['employees']
    )


def test_C17_GD4_the_warner_copy_over_the_client_file_matches_everyone(user, deal, golden):
    gd4, _refs, spec = golden['GD4']
    client, warner = spec['census']['file'], spec['census']['warner_file']
    services.apply_import(
        user, services.create_import(user, deal.id, upload(user, deal, _file(gd4, client), client).id).id
    )
    imp = services.create_import(user, deal.id, upload(user, deal, _file(gd4, warner), warner).id)
    first_row = spec['census']['warner_first_data_row']
    services.update_import(user, imp.id, {'first_data_row': first_row, 'mapping': WARNER_CHOICES})
    answer = services.dry_run(imp.id)
    assert answer['added'] == answer['removed'] == answer['kept'] == []  # matched by name and birth date
    # employees gain Warner's status and class; dependents take Warner's relationship words ("Spouse/Partner")
    assert {tuple(person['columns']) for person in answer['changed']} == {
        ('Class', 'Employment Status'),
        ('Relationship',),
    }


def test_Q8_GD4_canaries_stay_on_the_roster(golden):
    deal, _refs, spec = golden['GD4']
    canaries = [value for key, value in spec['census']['canaries'].items()]
    assert Member.objects.filter(deal=deal, values__first_name=spec['census']['canaries']['first_name']).exists()
    stored = [
        *Activity.objects.filter(deal=deal).values('summary', 'changes'),
        *CensusImport.objects.filter(deal=deal).values(),
    ]
    assert not [canary for canary in canaries if canary in str(stored)]


def test_Q9_41_C6_C38_GD4_a_fix_answers_one_person_and_its_template_comes_back_unchanged(user, api, deal, golden):
    from census import template

    gd4, _refs, spec = golden['GD4']
    name = spec['census']['file']
    services.apply_import(user, services.create_import(user, deal.id, upload(user, deal, _file(gd4, name), name).id).id)
    blank = next(m for m in Member.objects.filter(deal=deal, kind='employee') if not m.values.get('medical_tier'))
    before = facts.summary(facts.stored(deal.id))['missing_required']
    answer = api.patch(f'/api/census/members/{blank.id}/', {'values': {'medical_tier': 'ee'}}, format='json').json()
    assert answer['member']['id'] == blank.id and 'members' not in answer
    assert answer['member']['values']['medical_tier'] == 'EE' and 'medical_tier' not in answer['member']['missing']
    assert answer['summary']['missing_required'] == before - 1
    filled, people = template.template(deal)
    assert people == Member.objects.filter(deal=deal).count()
    returned = services.create_import(user, deal.id, upload(user, deal, filled, 'census template (returned).xlsx').id)
    assert not [item['header'] for item in returned.mapping if item['low'] or not item['field']]
    again = services.dry_run(returned.id)
    assert again['added'] == again['changed'] == again['removed'] == again['kept'] == []
    assert again['counts']['unchanged'] == people
