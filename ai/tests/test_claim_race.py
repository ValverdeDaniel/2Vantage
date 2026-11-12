"""The claim race (plan.md §10.2; O.3.3, Q.3 #8): two workers claiming at once pass each other's locked rows, and the
one-running-job-per-deal-and-lane constraint settles a tie. Real transactions on separate connections."""

import threading
import time

import pytest
from django.db import connection, transaction

from ai import kinds, worker
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
