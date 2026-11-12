"""Who lands what (plan.md §10.1; D71, D76, O.3.3; Q.9 row 20: landing by person, lock and lost deal), with a test
reader standing in for the quote reader, run inline with the fake client. Synthetic files only; GD3's own landing is in
quotes/tests/test_read_landing.py."""

import hashlib

import pytest
from django.utils import timezone

import synthetic_files
from accounts.models import Profile
from ai import kinds, land, pricing, registry, running, services
from ai.models import DealAi, Job
from ai.progress import Progress
from ai.registry import Reader
from ai.services.landing import waiting
from deals import activity, rules
from deals.activity import Refused
from deals.models import Activity, Deal
from documents.tests.helpers import stored

SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['n'], 'properties': {'n': {'type': 'integer'}}}
RAW = synthetic_files.text_pdf(['Example Health 2027 renewal', 'Gold PPO Employee only $512.34'])


class Owner:
    """What the test reader's owner did: each landing writes one Activity row, as an owner's `apply` does."""

    def __init__(self):
        self.refuse = None
        self.hard = False
        self.remove = False
        self.landed = []

    def build(self, deal, user, merged, files, extra):
        items = [{'id': 'i1', 'op': 'remove_plan' if self.remove else 'create_plan', 'tick': True, 'n': merged}]
        hard = self.hard and extra.get('model') == pricing.SONNET
        return {
            'items': items,
            'summary': '1 plan',
            'documents': [f.id for f in files],
            'findings': [{'text': 'A rate does not add up.', 'hard': True}] if hard else [],
            **extra,
        }

    def apply(self, user, deal, job, select=None, picks=None):
        if self.refuse:
            raise Refused(self.refuse)
        row = activity.record(deal, user, 'test_read', 'read', 'Used the test read')
        self.landed.append(job.id)
        return {'activity_id': row.id, 'activity_ids': [row.id], 'plan_ids': [7], 'areas': ['advisor'], 'summary': '1'}

    def undo(self, user, deal, job, force=False):
        Activity.objects.filter(id__in=job.result['landed']['activity_ids']).delete()
        return {'reverted': job.result['landed']['activity_ids'], 'kept': [], 'skipped': []}


@pytest.fixture
def owner():
    owner, before = Owner(), registry.readers.get('quotes')
    registry.readers['quotes'] = Reader(
        target='quotes',
        kinds=('renewal', 'quote'),
        prompt='Read the test file.',
        schema=SCHEMA,
        version=1,
        note=lambda file, context: 'A test file.',
        merge=lambda parts, files: [data['n'] for _file, _part, data in parts],
        build_changes=owner.build,
        apply=owner.apply,
        undo=owner.undo,
    )
    yield owner
    registry.readers['quotes'] = before


@pytest.fixture
def document(user, deal, fake_claude):
    fake_claude.record(('quotes', hashlib.sha256(RAW).hexdigest()[:16], 'p1'), {'n': 1})
    return stored(user, deal, 'renewal.pdf', RAW, kind='renewal')


@pytest.fixture
def direct(db):
    from django.contrib.auth import get_user_model

    person = get_user_model().objects.create_user('dee', 'dee@example.com', 'pw-Example-1')
    Profile.objects.create(user=person, claude_direct=True)
    return person


def read(person, deal, document, **options):
    job, _created = services.start_read(person, deal, [document.id], **options)
    job.refresh_from_db()
    return job


def test_D71_an_admins_read_lands_at_once_with_undo(admin_user, deal, owner, document, api):
    job = read(admin_user, deal, document)
    assert (job.status, job.land, job.resolution) == (kinds.DONE, land.AUTO, 'applied')
    assert job.result['landed']['auto'] is True and job.activity_id == job.result['landed']['activity_id']
    assert owner.landed == [job.id] and not waiting(job)
    news = api.get(f'/api/deals/{deal.id}/ai/').json()['news']
    assert [(row['job_id'], row['auto'], row['plan_ids']) for row in news] == [(job.id, True, [7])]
    undone, changed = services.undo(admin_user, job.id)
    assert changed and undone.resolution == 'undone' and not Activity.objects.filter(area='test_read').exists()


def test_D71_a_direct_persons_read_lands_and_a_producers_waits(user, direct, deal, owner, document):
    assert read(direct, deal, document).land == land.AUTO
    job = read(user, deal, document)
    assert (job.land, job.resolution, job.wait_reason) == (land.STAGED, '', land.WAITS)
    assert waiting(job) and owner.landed != [] and job.id not in owner.landed


@pytest.mark.parametrize('why', ['locked', 'lost', 'review', 'removes'])
def test_D71_E75_D104_an_admins_read_waits_when_locked_lost_asked_or_removing(admin_user, deal, owner, document, why):
    options = {}
    if why == 'locked':
        DealAi.objects.create(deal=deal, locked_by=admin_user, locked_at=timezone.now())
    elif why == 'lost':
        Deal.objects.filter(pk=deal.pk).update(stage='lost')
    elif why == 'review':
        options['review'] = True
    else:
        owner.remove = True
    rows = Activity.objects.count()
    job = read(admin_user, deal, document, **options)
    assert (job.land, job.resolution) == (land.STAGED, '') and waiting(job)
    expected = {'locked': land.LOCKED, 'lost': rules.REFUSALS['ai_land'], 'review': land.ASKED, 'removes': land.REMOVES}
    assert job.wait_reason == expected[why]
    assert owner.landed == [] and Activity.objects.count() == rows


def test_D71_a_landing_the_owner_refuses_waits_with_its_sentence(admin_user, deal, owner, document):
    owner.refuse = 'A plan on this line changed since the read.'
    job = read(admin_user, deal, document)
    assert (job.status, job.land, job.wait_reason) == (kinds.DONE, land.STAGED, owner.refuse)
    assert waiting(job) and not Activity.objects.filter(area='test_read').exists()


def test_D71_a_job_reaped_while_it_lands_takes_its_landing_back(admin_user, deal):
    job = Job.objects.create(deal=deal, lane=kinds.WORK, kind=kinds.READ, status=kinds.FAILED, created_by=admin_user)

    def lands(job, result):
        activity.record(deal, admin_user, 'test_read', 'read', 'Used the test read')
        return {'land': land.AUTO}

    assert running._finish(job, Progress(job), kinds.DONE, result={'items': [1]}, land=lands) is False
    assert not Activity.objects.filter(area='test_read').exists()
    assert Job.objects.get(pk=job.pk).status == kinds.FAILED


def test_D105_D71_stop_keeps_what_finished_and_waits_even_for_an_admin(
    admin_user, deal, owner, fake_claude, monkeypatch
):
    monkeypatch.setattr('ai.progress.BEAT_SECONDS', 0)
    document = stored(admin_user, deal, 'renewal.pdf', RAW, kind='renewal')

    def press_stop():
        services.cancel(admin_user, Job.objects.filter(status=kinds.RUNNING).get().id)

    fake_claude.record(('quotes', hashlib.sha256(RAW).hexdigest()[:16], 'p1'), {'n': 1}, during=press_stop)
    job = read(admin_user, deal, document)
    assert (job.status, job.land, job.resolution) == (kinds.CANCELLED, land.STAGED, 'stopped')
    assert owner.landed == [] and job.result['partial'] is True and waiting(job)


def test_D76_a_hard_finding_steps_up_to_opus_before_landing_for_an_admin_only(
    user, admin_user, deal, owner, document, fake_claude
):
    owner.hard = True
    job = read(user, deal, document)
    assert [entry['params']['model'] for entry in fake_claude.log] == [pricing.SONNET]
    assert job.result['findings'] and job.land == land.STAGED
    fake_claude.log.clear()
    job = read(admin_user, deal, document)
    assert [entry['params']['model'] for entry in fake_claude.log] == [pricing.SONNET, pricing.OPUS]
    assert job.result['model'] == pricing.OPUS and job.result['findings'] == [] and job.land == land.AUTO
    assert any('Opus 5.5 reads it again' in step for step in job.steps)
    assert job.usage['calls'] == 2


def test_D71_land_decides_by_its_inputs_alone():
    change_set = {'items': [{'id': 'i1', 'op': 'create_plan'}]}
    decide = land.decide
    assert decide({'items': []}, target='quotes', direct=True).mode == ''
    assert decide(change_set, target='quotes', direct=True).mode == land.AUTO
    assert decide(change_set, target='sbc', direct=True).sentence == land.ALWAYS
    assert decide(change_set, target='quotes', must_review=True, direct=True).sentence == land.ALWAYS
    assert decide({**change_set, 'partial': True}, target='quotes', direct=True).sentence == land.PARTIAL
    halted = {**change_set, 'halted': 'This read reached its $3.00 cap; what it finished is kept.'}
    assert decide(halted, target='quotes', direct=True).sentence == halted['halted']
