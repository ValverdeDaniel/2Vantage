"""`manage.py reader_eval --set all|tuning|held_out [--cases a,b] [--target quotes] [--model M] [--out FILE]`
(plan.md §12.8; Q.2's Eval lane, Q.6): read the reader's synthetic corpus live with Claude and score it against the
keys. It costs money: every call goes in the ledger (`manage.py ai_spend`) and the total cap holds. Prints counts and
rates only; exits 1 under any of Q.6's thresholds. `--out` writes the JSON report (outside the repository).
"""

import json
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ai import budget, client, registry
from ai import eval as reader_eval


class Command(BaseCommand):
    help = 'Read the synthetic corpus live with Claude and score it (the Eval lane; it costs money).'

    def add_arguments(self, parser):
        parser.add_argument('--set', default='all', choices=['all', 'tuning', 'held_out'])
        parser.add_argument('--cases', default='', help='Only these cases (comma-separated names).')
        parser.add_argument('--target', default='quotes')
        parser.add_argument('--model', default='')
        parser.add_argument('--out', default='', help='Write the JSON report here.')

    def handle(self, *args, **options):
        if not client.available():
            raise CommandError(client.NoKey.sentence)
        reader = registry.readers.get(options['target'])
        if reader is None or reader.corpus is None:
            raise CommandError(f'No corpus for the {options["target"]} reader.')
        names = {name.strip() for name in options['cases'].split(',') if name.strip()}
        cases = [
            case
            for case in reader.corpus()
            if (options['set'] == 'all' or case.set == options['set']) and (not names or case.name in names)
        ]
        if not cases:
            raise CommandError('No case matches.')
        model = options['model'] or settings.AI_MODEL
        effort = settings.AI_EFFORT.get('read', 'high')

        def said(case, part, done):
            state = done.error.reason if done.error else 'ok'
            self.stdout.write(f'{case.name} {part.label}: {state}, ${done.cost:.4f}')

        try:
            report = reader_eval.run(reader, cases, model=model, effort=effort, on_call=said)
        except budget.OverLimit as exc:
            raise CommandError(exc.sentence) from exc
        for name, totals in report['sets'].items():
            metrics = ', '.join(f'{key} {value}' for key, value in totals['metrics'].items())
            self.stdout.write(f'{name}: {metrics}; cost ${totals["cost_usd"]} (estimate ${totals["estimate_usd"]})')
        misses = reader_eval.check(report)
        if options['out']:
            with open(options['out'], 'w', encoding='utf-8') as handle:
                json.dump({**report, 'misses': misses}, handle, indent=1, default=str)
        for miss in misses:
            self.stdout.write(f'MISS {miss}')
        if misses:
            sys.exit(1)
        self.stdout.write('Every threshold met.')
