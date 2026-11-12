"""The claim race (plan.md §10.2; O.3.3, Q.3 #8): two workers claiming at once pass each other's locked rows, and the
one-running-job-per-deal-and-lane constraint settles a tie. Real transactions on separate connections. The queue runs
in the order jobs were started, by id, never by the clock, which steps back under load."""

import threading
import time
from datetime import timedelta

import pytest
from django.db import connection, transaction

from ai import kinds, selectors, worker
from ai.models import Job
from conftest import make_deal


def _job(deal):
    return Job.objects.create(deal=deal, lane=kinds.WORK, kind=kinds.RANK)


@pytest.mark.django_db(transaction=True)
def test_A36_two_workers_claim_at_once_and_one_job_runs_per_deal_and_lane(user):
    first_deal, other_deal = make_deal(user, name='First Co.'), make_deal(user, name='Other Co.')
    x1, y1, x2 = _job(first_deal), _job(other_deal), _job(first_deal)
    holding, release = threading.Event(), threading.Event()
    got = {}

    def worker_a():
        try:
            with transaction.atomic():  # claims X1 and keeps its transaction open
                got['a'] = worker.claim('a')
                holding.set()
                release.wait(10)
        finally:
            connection.close()

    def claimer(name):
        def run():
            try:
                got[name] = worker.claim(name)
            finally:
                connection.close()

        return threading.Thread(target=run)

    a = threading.Thread(target=worker_a)
    a.start()
    assert holding.wait(10)
    b = claimer('b')
    started = time.monotonic()
    b.start()
    b.join(5)
    # B skipped X1 (locked by A) and took Y1 at once, while A still holds its transaction.
    assert not b.is_alive() and got['b'].id == y1.id and time.monotonic() - started < 3
    c = claimer('c')
    c.start()
    time.sleep(0.3)
    assert c.is_alive()  # C picked X2 and waits on the constraint for A's claim of X1
    release.set()
    a.join(10)
    c.join(10)
    assert got['a'].id == x1.id and got['c'] is None
    assert {job.id: job.status for job in Job.objects.all()} == {
        x1.id: kinds.RUNNING,
        y1.id: kinds.RUNNING,
        x2.id: kinds.QUEUED,
    }


@pytest.mark.django_db
def test_A36_the_queue_runs_in_the_order_jobs_were_started_even_when_the_clock_stepped_back(user):
    deal, other = make_deal(user, name='First Co.'), make_deal(user, name='Other Co.')
    first, elsewhere, then = _job(deal), _job(other), _job(deal)
    # The clock stepped back a second after the first job was started (a VM resyncing its time under load).
    Job.objects.filter(pk__in=[elsewhere.pk, then.pk]).update(created_at=first.created_at - timedelta(seconds=1))
    places = {job['id']: job['queue_position'] for job in selectors.deal_state(deal, user)['jobs']}
    assert places == {first.id: 1, then.id: 2}
    assert [worker.claim(name).id for name in 'ab'] == [first.id, elsewhere.id]
    assert worker.claim('c') is None  # `then` waits for `first`: one job runs per deal and lane
