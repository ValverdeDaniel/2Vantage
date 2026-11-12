"""`manage.py check_sources [--deal ID] [--recheck] [--dry-run]` (plan.md §10.7; E84): look for every value in its own
file, in code, outside a job (the old `locate_sources`). Without `--recheck`, only values never checked or checked by
an older locator; with it, every one (after the locator learns something). `--dry-run` counts and writes nothing.
Prints ids and counts only, never a file name or a value.
"""

from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from ai import check
from deals.models import Deal
from documents.models import Document


class Command(BaseCommand):
    help = 'Check read values against their own files (the locator); prints counts only.'

    def add_arguments(self, parser):
        parser.add_argument('--deal', type=int, help='Only this deal.')
        parser.add_argument('--recheck', action='store_true', help='Check values already checked again.')
        parser.add_argument('--dry-run', action='store_true', help='Count the values to check; write nothing.')

    def handle(self, *args, deal=None, recheck=False, dry_run=False, **options):
        deals = Deal.objects.all() if deal is None else Deal.objects.filter(pk=deal)
        if deal is not None and not deals.exists():
            raise CommandError(f'No deal {deal}.')
        totals = Counter()
        for row in deals.order_by('id').iterator():
            for document in Document.all_objects.filter(deal=row).order_by('id'):
                if dry_run:
                    waiting = len(check.queries(row, document, recheck))
                    totals['to_check'] += waiting
                    if waiting:
                        self.stdout.write(f'Deal {row.id}, document {document.id}: {waiting} to check')
                    continue
                counts, saved, _areas, _row = check.check_document(None, row, document, recheck)
                totals.update(counts)
                totals['saved'] += saved
                if counts['checked']:
                    states = ', '.join(f'{key} {counts[key]}' for key in check.COUNTED if counts[key])
                    self.stdout.write(f'Deal {row.id}, document {document.id}: {counts["checked"]} checked ({states})')
        summary = ', '.join(f'{key} {value}' for key, value in sorted(totals.items()) if value)
        self.stdout.write(f'Total: {summary or "nothing to check"}')
