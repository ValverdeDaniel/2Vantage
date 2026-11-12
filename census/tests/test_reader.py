"""The census reader (plan.md §5.3.2, §10.4, §10.5, §10.8; C11, C19, D29, D74, D110; slice 51), run inline with the
fake client on a synthetic PDF roster: the people Claude read wait as a staged import for the Census tab, the job only
points at it, and nothing names a person outside the census."""

import json

import pytest

from ai import kinds, services
from ai.models import Job
from census import services as census
from census.models import CensusImport, Member
from census.reader import merge
from census.services import reads
from deals.models import Activity

from .reader_world import ANSWER, leaks, roster_read, value


class _File:
    def __init__(self, id, order):
        self.id, self.order = id, order


class _Part:
    def __init__(self, *pages):
        self.pages = pages


def test_D110_C19_a_pdf_roster_becomes_a_staged_import_that_its_read_points_at(user, deal, fake_claude):
    job, document = roster_read(user, deal, fake_claude)
    assert job.status == kinds.DONE and job.land == 'staged' and services.landing.waiting(job)
    [item] = job.result['items']
    imp = CensusImport.objects.get(pk=item['import'])
    assert item['op'] == 'census_import' and (item['people'], item['employees'], item['dependents']) == (4, 2, 2)
    assert imp.status == CensusImport.PROPOSED and imp.job_id == job.id and imp.document_id == document.id
    assert [person['kind'] for person in imp.read['people']] == ['employee', 'dependent', 'dependent', 'employee']
    assert [person['parent'] for person in imp.read['people']] == [None, 0, 0, None]
    assert Member.all_objects.filter(deal=deal).count() == 0  # the roster waits for a person
    assert 'Read 4 people (2 employees, 2 dependents)' in job.result['summary']


def test_Q8_a_census_read_names_no_one_outside_the_census(user, deal, fake_claude):
    job, _document = roster_read(user, deal, fake_claude)
    assert not leaks(json.dumps(job.result)) and not leaks(json.dumps(job.steps)) and not leaks(job.error)
    rows = list(Activity.objects.filter(deal=deal).values('summary', 'changes'))
    assert rows and not leaks(json.dumps(rows, default=str))
    imp = CensusImport.objects.get(job=job)
    census.apply_import(user, imp.id)
    job.refresh_from_db()
    rows = list(Activity.objects.filter(deal=deal).values('summary', 'changes'))
    assert not leaks(json.dumps(job.result)) and not leaks(json.dumps(rows, default=str))


def test_C19_applied_on_the_census_tab_people_keep_their_file_and_page_and_the_read_is_used(user, deal, fake_claude):
    job, document = roster_read(user, deal, fake_claude)
    imp = CensusImport.objects.get(job=job)
    answer = census.dry_run(imp.id)
    assert answer['counts']['added'] == 4 and answer['counts']['dependents'] == 2
    census.apply_import(user, imp.id)
    people = {member.values['first_name']: member for member in Member.objects.filter(deal=deal)}
    spouse = people['Marisolde']
    assert spouse.employee_id == people['Zephyrine'].id and spouse.kind == 'dependent'
    assert spouse.values['dob'] == '1984-02-02' and people['Zephyrine'].values['medical_tier'] == 'FAM'
    entry = spouse.sources['dob']
    assert entry['origin'] == 'ai' and entry['doc'] == document.id and entry['page'] == 1 and entry['low']
    assert 'low' not in spouse.sources['first_name']
    job.refresh_from_db()
    imp.refresh_from_db()
    assert job.resolution == 'applied' and 'items' not in job.result  # used, and emptied (D74)
    assert job.result['landed']['undo'] is False and job.activity_id == job.result['landed']['activity_id']
    assert imp.status == CensusImport.APPLIED and not imp.read.get('people')


def test_D29_use_this_scan_applies_its_import_and_undo_says_how_to_go_back(user, deal, fake_claude):
    job, _document = roster_read(user, deal, fake_claude)
    job, landed = services.apply(user, job.id)
    assert Member.objects.filter(deal=deal).count() == 4 and landed['undo'] is False
    assert CensusImport.objects.get(job=job).status == CensusImport.APPLIED
    with pytest.raises(services.landing.UndoRefused):
        services.undo(user, job.id)


def test_D74_discarding_the_read_sets_its_import_aside_and_the_other_way_round(user, deal, fake_claude):
    job, _document = roster_read(user, deal, fake_claude)
    services.discard(user, job.id)
    imp = CensusImport.objects.get(job=job)
    assert imp.status == CensusImport.DISCARDED and not imp.read.get('people')
    second, _document = roster_read(user, deal, fake_claude)
    census.discard_import(user, CensusImport.objects.get(job=second).id)
    second.refresh_from_db()
    assert second.resolution == 'discarded' and not services.landing.waiting(second)
    assert Member.all_objects.filter(deal=deal).count() == 0


def test_C17_a_new_census_file_sets_a_waiting_read_aside_with_its_read(user, deal, fake_claude):
    from .helpers import family, import_file, roster, xlsx

    job, _document = roster_read(user, deal, fake_claude)
    import_file(user, deal, xlsx(roster(family('E1', 'Example'))))
    job.refresh_from_db()
    assert job.resolution == 'discarded' and CensusImport.objects.get(job=job).status == CensusImport.DISCARDED


def test_C19_a_read_import_takes_column_changes_but_no_sheet(user, api, deal, fake_claude):
    job, _document = roster_read(user, deal, fake_claude)
    imp = CensusImport.objects.get(job=job)
    shown = api.get(f'/api/census/imports/{imp.id}/').json()
    assert shown['read'] and shown['sheets'] == [] and all(not item['letter'] for item in shown['mapping'])
    tier = next(item for item in shown['mapping'] if item['field'] == 'medical_tier')
    assert tier['samples'][0] == 'Family'
    refused = api.patch(f'/api/census/imports/{imp.id}/', {'sheet_name': 'Other'}, format='json')
    assert refused.status_code == 400
    moved = api.patch(
        f'/api/census/imports/{imp.id}/', {'mapping': [{'column': tier['column'], 'field': ''}]}, format='json'
    )
    assert moved.status_code == 200
    census.apply_import(user, imp.id)
    assert not any('medical_tier' in member.values for member in Member.objects.filter(deal=deal))


def test_C19_people_read_twice_are_kept_once_and_dependents_go_under_their_printed_employee():
    first = {'people': ANSWER['people'][:2]}
    again = {
        'people': [
            ANSWER['people'][1],  # the spouse again, at the top of the next page: printed under Zephyrine
            ANSWER['people'][3],
            {'dependent': True, 'employee': 'Zephyrine Quillonbeck', 'values': [value('first_name', 'Wren')]},
            {
                'dependent': True,
                'employee': '',
                'values': [value('first_name', 'Ash'), value('last_name', 'Pembleton')],
            },
        ]
    }
    file = _File(7, 0)
    merged = merge.merge([(file, _Part(2), again), (file, _Part(1), first)], [file])
    names = [person['values']['first_name'] for person in merged['people']]
    assert names == ['Zephyrine', 'Marisolde', 'Oskar', 'Wren', 'Ash'] and merged['duplicates'] == 1
    assert [person['parent'] for person in merged['people']] == [None, 0, None, 0, 2] and merged['guessed'] == 1


def test_C19_a_dependent_never_goes_under_an_employee_of_another_file():
    lone = {'people': [{'dependent': True, 'employee': '', 'values': [value('first_name', 'Rook')]}]}
    merged = merge.merge([(_File(1, 0), _Part(1), {'people': ANSWER['people'][:1]}), (_File(2, 1), _Part(1), lone)], [])
    assert merged['people'][1]['parent'] is None and merged['people'][1]['doc'] == 2


def test_O33_a_census_read_always_waits_even_for_an_admin(admin_user, deal, fake_claude):
    job, _document = roster_read(admin_user, deal, fake_claude)
    assert job.land == 'staged' and job.resolution == '' and Member.all_objects.filter(deal=deal).count() == 0


def test_D110_reader_apply_refuses_without_a_waiting_import(user, deal, fake_claude):
    job, _document = roster_read(user, deal, fake_claude)
    CensusImport.objects.filter(job=job).update(status=CensusImport.DISCARDED)
    with pytest.raises(Exception) as refused:
        reads.reader_apply(user, deal, Job.objects.get(pk=job.id))
    assert reads.NOT_STAGED in str(refused.value.detail)
