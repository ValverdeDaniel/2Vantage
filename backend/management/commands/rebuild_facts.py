"""manage.py rebuild_facts [--deal ID] [--fix] — stored counts against a fresh rebuild (plan.md §5.3.5, O.3.7, Q.3 #9).

The stored counts are the one exception to "computed on read": `census.CensusFacts` (slice 12), and the open
warnings (`flags`) on Plan, Intake and Questionnaire, which their owners register in `deals.stored_counts` (slice
17). Each owner rebuilds its own and says what differs; with `--fix` the owner's service rewrites them. Lives in the
composition root because it calls every owner. Exits 1 when a difference is found and not fixed. Prints deal ids and
field names only, never a value that could carry PHI.
"""

from django.core.management.base import BaseCommand, CommandError

from census import facts as census_facts
from census.services import refresh_facts
from deals.stored_counts import rebuild_all


class Command(BaseCommand):
    help = 'Compare the stored counts (CensusFacts, Plan.flags) with a fresh rebuild; --fix rewrites those that differ.'

    def add_arguments(self, parser):
        parser.add_argument('--deal', type=int, help='Only this deal.')
        parser.add_argument('--fix', action='store_true', help='Rewrite the counts that differ.')

    def handle(self, *args, deal=None, fix=False, **options):
        deal_ids = [deal] if deal else census_facts.deal_ids()
        wrong = 0
        for deal_id in deal_ids:
            differs = census_facts.differences(deal_id)
            if not differs:
                continue
            wrong += 1
            self.stdout.write(f'Deal {deal_id}: census facts differ in {", ".join(sorted(differs))}')
            if fix:
                refresh_facts(deal_id)
                self.stdout.write(f'Deal {deal_id}: rewritten')
        self.stdout.write(f'Checked {len(deal_ids)} deal(s); {wrong} differed{" and were rewritten" if fix else ""}.')
        # The open-warning counts the owners register in `deals.stored_counts` (Plan.flags from slice 17, Intake.flags).
        for name, differences in rebuild_all([deal] if deal else None, write=fix).items():
            for target, stored, rebuilt in differences:
                self.stdout.write(f'{target}: flags stored {stored}, rebuilt {rebuilt}{" (rewritten)" if fix else ""}')
            self.stdout.write(f'Checked {name}; {len(differences)} differed{" and were rewritten" if fix else ""}.')
            wrong += len(differences)
        if wrong and not fix:
            raise CommandError('Stored counts differ from a rebuild. Run with --fix to rewrite them.')
