"""manage.py seed_golden [GD1 …] — (re)build the golden deals in the current database (plan.md §12.6)."""

from django.core.management.base import BaseCommand, CommandError

from golden import seed, specs


class Command(BaseCommand):
    help = 'Build (or rebuild) the synthetic golden deals from their specs, through the services.'

    def add_arguments(self, parser):
        parser.add_argument('deals', nargs='*', help='Deal keys to build (default: every spec and variant), e.g. GD1')

    def handle(self, *args, **options):
        known = {key.upper(): key for key in [*specs.keys(), *specs.variant_keys()]}
        unknown = sorted({key.upper() for key in options['deals']} - set(known))
        if unknown:
            raise CommandError(f'No golden spec named {", ".join(unknown)}; there are {", ".join(known.values())}.')
        wanted = [known[key.upper()] for key in options['deals']]
        for key, built in seed.build_all(only=wanted, variants=True).items():
            self.stdout.write(f'{key} {built.deal.client.name}: deal {built.deal.id}, {len(built.refs)} plans')
