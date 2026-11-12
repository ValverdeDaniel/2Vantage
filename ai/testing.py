"""For tests (plan.md §3.5, §12.1; Q.6): jobs run inline, never through a worker process, and never reach a network.
Slice 18 adds the fake Claude client here, replaying recorded responses."""

from .worker import Worker


def run_jobs(limit=20):
    """Claim and run queued jobs in this process until none is free (or `limit`); returns the jobs run."""
    worker, ran = Worker(name='test'), []
    for _ in range(limit):
        job = worker.work_once()
        if job is None:
            break
        ran.append(job)
    return ran
