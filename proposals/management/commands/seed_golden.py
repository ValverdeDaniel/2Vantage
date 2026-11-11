"""manage.py seed_golden — (re)build the golden deals in the current database (plan.md §12.6)."""

from django.core.management.base import BaseCommand

from proposals import golden


class Command(BaseCommand):
    help = 'Build (or rebuild) the synthetic golden deals through the services.'

    def handle(self, *args, **options):
        for deal, refs in golden.build_all():
            self.stdout.write(f'{deal.client.name}: deal {deal.id}, {len(refs)} plans')
