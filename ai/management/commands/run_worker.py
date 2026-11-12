"""`manage.py run_worker`: the job worker, its own Compose service (plan.md §3.4, §10.2; O.3.3, D105).

It runs every lane's jobs (reads, chats, re-checks, Rank, locate and Issue) whether or not a Claude key is set, and
does not reload when code changes: `docker compose restart worker` after changing code it runs. SIGTERM stops it at
the running job's next step and puts that job back in the queue.
"""

import signal

from django.core.management.base import BaseCommand

from ai.worker import Worker


class Command(BaseCommand):
    help = 'Run queued jobs (reads, chat turns, re-checks, Rank, locate, Issue) until stopped.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Run at most one job, then exit.')

    def handle(self, *args, once=False, **options):
        worker = Worker()
        signal.signal(signal.SIGTERM, worker.stop)
        signal.signal(signal.SIGINT, worker.stop)
        if once:
            job = worker.work_once()
            self.stdout.write(f'Ran job {job.id}.' if job else 'No job was waiting.')
            return
        self.stdout.write(f'Job worker {worker.name} started.')
        worker.loop()
        self.stdout.write(f'Job worker {worker.name} stopped.')
