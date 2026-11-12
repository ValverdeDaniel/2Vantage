"""Jobs, lanes, Stop and the reaper (plan.md §10.2; O.3.3, D105, A36). Runners here are stand-ins registered for one
test; the worker's own functions run them in the test, never a worker process (§3.5)."""

import logging
from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction

from ai import kinds, registry, running, services, worker
from ai.models import Job
from ai.progress import Progress
from ai.testing import run_jobs
from conftest import make_deal
from deals import clock
from deals.activity import Refused
from documents.tests.helpers import stored


@pytest.fixture
def queued(settings):
    settings.AI_JOBS_INLINE = False  # jobs wait for the worker, as they do outside tests


def use_runner(monkeypatch, kind, fn):
    monkeypatch.setitem(registry.job_kinds, kind, registry.JobKind(kinds.LANE_OF[kind], fn))


def statuses(*jobs):
    return [Job.objects.get(pk=job.pk).status for job in jobs]


def test_A36_a_started_job_waits_in_its_kinds_lane(user, deal, queued):
    job, created = services.start(user, deal, kinds.RANK)
    assert created and (job.status, job.lane, job.created_by) == (kinds.QUEUED, kinds.WORK, user)
    again, created_again = services.start(user, deal, kinds.RANK)
    assert (again.id, created_again) == (job.id, False)  # a double click starts one job
    other, created_other = services.start(user, deal, kinds.RANK, params={'guidance': 'cheapest'})
    assert created_other and other.id != job.id


def test_A36_one_job_runs_per_deal_and_lane(user, deal, queued, monkeypatch):
    use_runner(monkeypatch, kinds.RANK, lambda job, progress: {})
    first, _ = services.start(user, deal, kinds.RANK)
    second, _ = services.start(user, deal, kinds.RANK, params={'n': 2})
    document = stored(user, deal)
    check, _ = services.start(user, deal, kinds.LOCATE, documents=[document.id])
    elsewhere, _ = services.start(user, make_deal(user, name='Other Co.'), kinds.RANK)
    assert worker.claim('a').id == first.id
    # The second read waits for the first; the system lane and another deal do not.
    assert {worker.claim('b').id, worker.claim('c').id} == {check.id, elsewhere.id}
    assert worker.claim('d') is None
    assert statuses(first, second) == [kinds.RUNNING, kinds.QUEUED]
    with pytest.raises(IntegrityError), transaction.atomic():
        Job.objects.filter(pk=second.pk).update(status=kinds.RUNNING)  # the database refuses a second one too
    running.run(Job.objects.get(pk=first.pk))
    assert worker.claim('e').id == second.id


def test_D105_stop_on_a_queued_job_ends_it_at_once(user, deal, queued):
    job, _ = services.start(user, deal, kinds.RANK)
    stopped, changed = services.cancel(user, job.id)
    assert changed and (stopped.status, stopped.resolution) == (kinds.CANCELLED, kinds.STOPPED)
    assert worker.claim('a') is None
    again, changed_again = services.cancel(user, job.id)
    assert not changed_again and again.updated_at == stopped.updated_at  # the same Stop again changes nothing


def test_D105_stop_on_a_running_job_ends_it_at_its_next_step_keeping_what_it_finished(user, deal, queued, monkeypatch):
    def runner(job, progress):
        progress.step('File 1 of 2')
        progress.result = {'files': [1]}
        services.cancel(user, job.id)  # Stop pressed while the job runs
        assert Job.objects.get(pk=job.id).status == kinds.RUNNING
        progress.step('File 2 of 2')
        raise AssertionError('the beat after Stop must end the job')

    use_runner(monkeypatch, kinds.RANK, runner)
    job, _ = services.start(user, deal, kinds.RANK)
    run_jobs()
    job.refresh_from_db()
    assert (job.status, job.resolution, job.result) == (kinds.CANCELLED, kinds.STOPPED, {'files': [1]})
    assert job.steps[-1] == running.STOPPED_STEP and job.finished_at


def test_D105_stop_on_a_finished_job_is_refused(user, deal, queued, monkeypatch):
    use_runner(monkeypatch, kinds.RANK, lambda job, progress: {'ok': True})
    job, _ = services.start(user, deal, kinds.RANK)
    run_jobs()
    with pytest.raises(Refused) as refused:
        services.cancel(user, job.id)
    assert refused.value.sentence == services.jobs.FINISHED


def test_D105_progress_beats_and_says_what_it_does(user, deal, queued, monkeypatch):
    seen = {}

    def runner(job, progress):
        progress.step('Reading the file', 10)
        progress.say('Reading page 1 of 3', 20)
        progress.say('Reading page 2 of 3', 40)
        row = Job.objects.get(pk=job.id)
        seen.update(progress=row.progress, steps=row.steps, beat=row.heartbeat_at)
        return {'done': True}

    use_runner(monkeypatch, kinds.RANK, runner)
    job, _ = services.start(user, deal, kinds.RANK)
    run_jobs()
    # A live line replaces the one before it; writes come with the work, at most one a second.
    assert seen['steps'][:2] == [services.jobs.WAITING, 'Reading the file'] and seen['beat']
    job.refresh_from_db()
    assert (job.status, job.progress, job.result) == (kinds.DONE, 100, {'done': True})
    assert job.steps == [services.jobs.WAITING, 'Reading the file', 'Reading page 2 of 3']


def test_D105_the_reaper_ends_jobs_silent_for_ten_minutes(user, deal, queued):
    now = clock.now()
    silent = Job.objects.create(
        deal=deal, lane=kinds.WORK, kind=kinds.RANK, status=kinds.RUNNING, heartbeat_at=now - timedelta(minutes=11)
    )
    beating = Job.objects.create(
        deal=make_deal(user, name='Busy Co.'),
        lane=kinds.WORK,
        kind=kinds.RANK,
        status=kinds.RUNNING,
        heartbeat_at=now - timedelta(minutes=9),
    )
    assert worker.reap(now) == 1
    silent.refresh_from_db()
    assert (silent.status, silent.resolution, silent.error) == (kinds.FAILED, kinds.REAPED, worker.REAPED_SENTENCE)
    assert Job.objects.get(pk=beating.pk).status == kinds.RUNNING
    # The reaper's UPDATE re-checks the heartbeat itself: a beat that lands first keeps the job.
    Job.objects.filter(pk=beating.pk).update(heartbeat_at=now)
    assert worker.reap(now + timedelta(minutes=2)) == 0


def test_D105_a_reaped_job_stops_at_its_next_beat_and_keeps_the_reapers_words(user, deal, queued, monkeypatch):
    def runner(job, progress):
        worker.reap(clock.now() + timedelta(minutes=30))  # the job fell silent; the reaper took it
        progress.step('Still here?')
        raise AssertionError('a reaped job must not go on')

    use_runner(monkeypatch, kinds.RANK, runner)
    job, _ = services.start(user, deal, kinds.RANK)
    assert running.run(worker.claim('a')) is None
    job.refresh_from_db()
    assert (job.status, job.error) == (kinds.FAILED, worker.REAPED_SENTENCE)


def test_D105_a_stopping_worker_puts_its_job_back_in_the_queue(user, deal, queued, monkeypatch):
    calls = []

    def runner(job, progress):
        calls.append(job.id)
        progress.step('File 1 of 2')
        return {'files': 2}

    use_runner(monkeypatch, kinds.RANK, runner)
    job, _ = services.start(user, deal, kinds.RANK)
    assert running.run(worker.claim('a'), stopping=lambda: True) == kinds.QUEUED
    job.refresh_from_db()
    assert (job.status, job.started_at, job.steps[-1]) == (kinds.QUEUED, None, running.PAUSED_STEP)
    run_jobs()
    assert Job.objects.get(pk=job.pk).status == kinds.DONE and len(calls) == 2


def test_D105_a_failure_says_a_sentence_and_logs_no_text(user, deal, queued, monkeypatch, caplog):
    def runner(job, progress):
        raise ValueError('Employee TESTER ALPHA 01/02/1970')  # a message that could carry a file's words

    use_runner(monkeypatch, kinds.RANK, runner)
    job, _ = services.start(user, deal, kinds.RANK)
    with caplog.at_level(logging.INFO):
        run_jobs()
    job.refresh_from_db()
    assert (job.status, job.error) == (kinds.FAILED, running.FAILED_SENTENCE)
    assert 'TESTER' not in caplog.text and 'ValueError' in caplog.text


def test_A36_jobs_run_inline_in_tests(user, deal, monkeypatch):
    use_runner(monkeypatch, kinds.RANK, lambda job, progress: {'ran': 'inline'})
    job, created = services.start(user, deal, kinds.RANK)
    assert created and (job.status, job.result) == (kinds.DONE, {'ran': 'inline'})


def test_A36_steps_keep_fifty_short_lines(user, deal, queued):
    job, _ = services.start(user, deal, kinds.RANK)
    claimed = worker.claim('a')
    progress = Progress(claimed)
    for n in range(80):
        progress.step(f'Step {n} ' + 'x' * 300)
    job.refresh_from_db()
    assert len(job.steps) == kinds.STEPS_KEPT and all(len(line) <= kinds.STEP_LENGTH for line in job.steps)
    assert job.steps[-1].startswith('Step 79')
