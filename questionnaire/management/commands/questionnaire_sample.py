"""manage.py questionnaire_sample — a synthetic filled Florida Blue 51+ form for reader trials, and its score (G109;
slice 52). A dev command: the app never runs it, and it never calls Claude.

    python manage.py questionnaire_sample --out <folder outside the repository>
        writes fl_blue_51-filled-synthetic.pdf (the sample stamped on the carrier's blank) and its answer key, .json
    python manage.py questionnaire_sample --score <staged read id> --key <the key .json>
        compares a waiting read (`StagedRead.read`, before it is used) with the key: counts only, never a value
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from questionnaire import trials
from questionnaire.models import StagedRead


class Command(BaseCommand):
    help = 'Write a synthetic filled Florida Blue 51+ form and its key, or score a staged read against the key (dev).'

    def add_arguments(self, parser):
        parser.add_argument('--out', default='', help='write the filled form and its key into this folder')
        parser.add_argument('--score', type=int, default=0, help='the staged read to score')
        parser.add_argument('--key', default='', help='the answer key the --out run wrote')

    def handle(self, *args, **options):
        if options['out']:
            folder = Path(options['out'])
            folder.mkdir(parents=True, exist_ok=True)
            pdf = folder / f'{trials.FORM}-filled-synthetic.pdf'
            pdf.write_bytes(trials.printed_sample())
            (folder / f'{trials.FORM}-filled-synthetic.key.json').write_text(json.dumps(trials.key(), indent=1))
            self.stdout.write(f'Wrote {pdf} and its key.')
            return
        if not (options['score'] and options['key']):
            raise CommandError('Give --out, or --score with --key.')
        staged = StagedRead.objects.filter(pk=options['score']).first()
        if staged is None or not staged.read:
            raise CommandError('No waiting read with that id (a used or discarded read keeps no values).')
        key_data = json.loads(Path(options['key']).read_text())
        self.stdout.write(json.dumps(trials.score(key_data, staged.read), indent=1))
