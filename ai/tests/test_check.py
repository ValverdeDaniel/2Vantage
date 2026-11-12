"""The `locate` job, "Check this file" (plan.md §10.7; E59, E81–E84, D95). A stand-in value owner registers its locate
hooks for each test, over real synthetic files; quotes' own hooks are tested in quotes."""

import pytest
from rest_framework.exceptions import ValidationError

import synthetic_files
from ai import check, kinds, registry, services
from ai.models import Job
from ai.testing import run_jobs
from conftest import make_deal
from deals.models import Activity
from documents.locate import VERSION, Query
from documents.tests.helpers import RATES_PDF, stored


class Owner:
    """An in-memory value owner: {ref: {'value', 'doc', 'loc'}}, with the hooks' shape (registry.LocateHook)."""

    def __init__(self, values, on_save=None):
        self.values = values
        self.on_save = on_save

    def queries(self, deal, document, recheck):
        return [
            (ref, Query(entry['value']))
            for ref, entry in self.values.items()
            if entry['doc'] == document.id and (recheck or not entry.get('loc'))
        ]

    def save(self, user, deal, document, answers):
        saved = 0
        for ref, loc in answers:
            stored_loc = {k: v for k, v in (self.values[ref].get('loc') or {}).items() if k != 'at'}
            if stored_loc != {k: v for k, v in loc.items() if k != 'at'}:
                self.values[ref]['loc'] = loc
                saved += 1
        if self.on_save:
            self.on_save(document)
        return {'saved': saved, 'areas': ['advisor'] if saved else []}


@pytest.fixture
def owner(monkeypatch):
    def use(values, on_save=None):
        made = Owner(values, on_save)
        monkeypatch.setattr(registry, 'locate_hooks', {'stand-in': registry.LocateHook(made.queries, made.save)})
        return made

    return use


@pytest.fixture
def renewal(user, deal):
    return stored(user, deal, name='renewal.pdf', kind='renewal')


def test_E59_check_this_file_finds_each_value_in_its_file(user, deal, renewal, owner):
    values = owner({'ee': {'value': '512.34', 'doc': renewal.id}, 'typo': {'value': '999.99', 'doc': renewal.id}})
    job, created = services.start_locate(user, deal, [renewal.id])
    assert created and job.status == kinds.DONE and job.lane == kinds.SYSTEM
    assert values.values['ee']['loc'] | {'at': None} == {
        'state': 'found',
        'page': 2,
        'hits': 1,
        'via': 'number',
        'v': VERSION,
        'at': None,
    }
    assert values.values['typo']['loc']['state'] == 'absent'
    assert job.result['counts'] == {'checked': 2, 'found': 1, 'derived': 0, 'weak': 0, 'absent': 1, 'nocheck': 0}
    assert job.result['files'] == [{'id': renewal.id, 'checked': 2, 'absent': 1}]
    assert job.result['landed']['areas'] == ['advisor']
    assert job.steps[-1] == 'The file: Checked 2 values against the file — 1 not found in it'
    row = Activity.objects.get(pk=job.activity_id)
    assert (row.area, row.action, row.document_id, row.actor) == ('ai', 'checked', renewal.id, user)
    assert row.summary == 'Checked 2 values against the file — 1 not found in it'
    assert not row.changes and not row.revertible  # bookkeeping: no value changed, so nothing to revert


def test_E84_a_second_check_looks_only_at_unchecked_values_and_writes_nothing(user, deal, renewal, owner):
    values = owner({'ee': {'value': '512.34', 'doc': renewal.id}})
    services.start_locate(user, deal, [renewal.id])
    rows = Activity.objects.count()
    again, _ = services.start_locate(user, deal, [renewal.id])
    assert again.result['counts']['checked'] == 0 and again.activity_id is None
    recheck, _ = services.start_locate(user, deal, [renewal.id], recheck=True)
    assert recheck.result['counts']['checked'] == 1 and recheck.result['saved'] == 0
    assert Activity.objects.count() == rows  # the same answer again stores nothing and records nothing
    assert values.values['ee']['loc']['state'] == 'found'


def test_E59_stop_between_files_keeps_the_files_already_checked(user, deal, owner, settings):
    settings.AI_JOBS_INLINE = False
    first = stored(user, deal, name='first.pdf', kind='renewal')
    second = stored(user, deal, name='second.pdf', kind='quote')
    job_box = {}

    def press_stop(document):
        if document.id == first.id:
            services.cancel(user, job_box['job'].id)

    values = owner(
        {'a': {'value': '512.34', 'doc': first.id}, 'b': {'value': '512.34', 'doc': second.id}}, on_save=press_stop
    )
    job_box['job'], _ = services.start_locate(user, deal, [first.id, second.id])
    run_jobs()
    job = Job.objects.get(pk=job_box['job'].id)
    assert (job.status, job.resolution) == (kinds.CANCELLED, kinds.STOPPED)
    assert values.values['a']['loc']['state'] == 'found' and 'loc' not in values.values['b']
    assert [entry['id'] for entry in job.result['files']] == [first.id]


def test_E59_a_check_never_waits_behind_a_read(user, deal, renewal, owner):
    Job.objects.create(deal=deal, lane=kinds.WORK, kind=kinds.READ, status=kinds.RUNNING)
    owner({'ee': {'value': '512.34', 'doc': renewal.id}})
    job, _ = services.start_locate(user, deal, [renewal.id])
    assert job.status == kinds.DONE


def test_E81_a_file_missing_from_storage_says_check_by_eye(user, deal, renewal, owner):
    values = owner({'ee': {'value': '512.34', 'doc': renewal.id}})
    renewal.file.storage.delete(renewal.file.name)
    services.start_locate(user, deal, [renewal.id])
    assert values.values['ee']['loc'] | {'at': None} == {'state': 'nocheck', 'why': 'missing', 'v': VERSION, 'at': None}


def test_E59_a_long_file_reports_its_pages(user, deal, owner):
    pages = [[f'Exhibit page {n}', 'Nothing to see on this page'] for n in range(1, 31)]
    pages[29] = ['Exhibit page 30', 'Employee only $512.34']
    long_pdf = stored(user, deal, name='long.pdf', kind='renewal', content=synthetic_files.text_pdf(*pages))
    values = owner({'ee': {'value': '512.34', 'doc': long_pdf.id}})
    job, _ = services.start_locate(user, deal, [long_pdf.id])
    assert values.values['ee']['loc']['page'] == 30
    assert job.steps == [
        services.jobs.WAITING,
        'Checking the values against their file',
        'Looking for 1 value',
        'The file: Checked 1 value against the file',
    ]


@pytest.mark.parametrize('ids', [[], None])
def test_E59_check_needs_files(user, deal, ids):
    with pytest.raises(ValidationError):
        services.start_locate(user, deal, ids)


def test_E59_check_takes_only_this_deals_files(user, deal):
    elsewhere = stored(user, make_deal(user, name='Other Co.'), content=RATES_PDF)
    with pytest.raises(ValidationError):
        services.start_locate(user, deal, [elsewhere.id])


def test_E59_check_queries_every_registered_owner(user, deal, renewal, monkeypatch):
    seen = []

    def queries(name):
        return lambda deal_, document, recheck: seen.append((name, document.id, recheck)) or []

    hooks = {name: registry.LocateHook(queries(name), None) for name in ('quotes', 'intake')}
    monkeypatch.setattr(registry, 'locate_hooks', hooks)
    assert check.queries(deal, renewal, True) == []
    assert seen == [('quotes', renewal.id, True), ('intake', renewal.id, True)]
