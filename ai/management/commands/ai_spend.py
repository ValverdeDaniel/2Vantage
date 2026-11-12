"""`manage.py ai_spend [--calls N]` (plan.md §3.5, §10.3; slice 18): what every Claude call this database recorded has
cost, against the total cap (`AI_TOTAL_BUDGET_USD`; none when unset). Calls still out count at their worst case.
`--calls` lists the newest calls: purpose, models, status, estimate, cost and tokens; never a file or a value.
"""

from django.core.management.base import BaseCommand

from ai import budget
from ai.models import Call


class Command(BaseCommand):
    help = 'Show what Claude has cost here, against the total cap; counts and dollars only.'

    def add_arguments(self, parser):
        parser.add_argument('--calls', type=int, default=0, help='Also list the newest N calls.')

    def handle(self, *args, calls=0, **options):
        row = budget.ledger()
        cap = budget.total_cap()
        total = row['spent'] + row['reserved']
        self.stdout.write(f'Spent: ${row["spent"]:.4f} over {row["calls"]} call(s)')
        self.stdout.write(f'Out now (at their worst case): ${row["reserved"]:.4f}')
        if cap is None:
            self.stdout.write('Total cap: none (AI_TOTAL_BUDGET_USD is unset)')
        else:
            self.stdout.write(f'Total cap: ${cap:.2f} · counted ${total:.4f} · left ${max(cap - total, 0):.4f}')
        for call in Call.objects.order_by('-id')[:calls]:
            usage = call.usage or {}
            tokens = '/'.join(
                str(usage.get(key, 0))
                for key in ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')
            )
            self.stdout.write(
                f'#{call.id} {call.created_at:%Y-%m-%d %H:%M} {call.purpose} {call.model}'
                f'{" -> " + call.answered if call.answered and call.answered != call.model else ""} {call.status} '
                f'est ${call.estimate_usd:.4f} cost ${call.cost_usd:.6f} tokens in/out/cw/cr {tokens}'
                f'{" job " + str(call.job_id) if call.job_id else ""}'
            )
