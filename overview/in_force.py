"""Coverage in force on the client page (plan.md §8.5; CL20, H106; slice 67): what the client has today, from the deal
the page works in. Reads only, inside the page's batch scope.

- Once a plan is sold (a client): the sold plans, one row per line, with the premium a month of the line's Sold
  package (`quotes` prices it: `package()` is the one source of a package, rule 5) and the commission the
  Commission tab applies to it — the rate and what it earns a year (`commission.revenue.line_rows`, the tab's grid).
- Before (a prospect, or a client converted by hand): the current coverage intake records, each line's carrier (its
  current plans' once the Advisor has them, `quotes.facts.incumbent`) and funding, with its in-force commission; then
  each line whose current plans the Advisor holds and intake does not (no commission known there).

`in_force(deal)` → {kind: 'sold' | 'current' | None, rows: [{line, label, carrier, plan, funding, premium_month,
commission, expected, renews}]}: `premium_month` and `expected` in whole dollars, half up, as the old table printed
them; `renews` is when the line next renews — the current coverage on the deal's effective date, the sold plans a year
after it (the old table's Renews).
"""

from datetime import date

from commission import revenue
from commission.models import Commission
from commission.selectors import agency_default
from deals import comp, lines
from intake import providers as intake_providers
from intake import selectors as intake_selectors
from quotes import facts as quote_facts
from quotes.math import round_money
from quotes.selectors import deal_state

SOLD = 'sold'


def a_year_after(day):
    """The same day a year on (29 February → 28 February), or None."""
    if day is None:
        return None
    try:
        return day.replace(year=day.year + 1)
    except ValueError:
        return date(day.year + 1, 2, 28)


def _sold_rows(deal):
    states = deal_state(deal)
    packages = {line: next((p for p in state.packages if p['key'] == SOLD), None) for line, state in states.items()}
    if not any(package and package['plan_ids'] for package in packages.values()):
        return []
    rates = Commission.objects.filter(deal_id=deal.id).values_list('rates', flat=True).first() or {}
    grid = {row['line']: row for row in revenue.line_rows(deal, rates, agency_default(), states)[0]}
    rows = []
    for line, state in states.items():
        package = packages[line]
        if not package or not package['plan_ids']:
            continue
        by_id = {plan.id: plan for plan in state.plans}
        sold = [by_id[pid] for pid in package['plan_ids'] if pid in by_id]
        found = grid.get(line) or {}
        rows.append(
            {
                'line': line,
                'label': lines.label(line),
                'carrier': ', '.join(dict.fromkeys(plan.carrier for plan in sold if plan.carrier)),
                'plan': ', '.join(plan.name for plan in sold),
                'funding': next((str(plan.values.get('funding')) for plan in sold if plan.values.get('funding')), ''),
                'premium_month': round_money(package['monthly']),
                'commission': found.get('effective_label') or '',
                'expected': round_money(found.get('expected')),
                'renews': a_year_after(deal.effective_date),
            }
        )
    return rows


def _current_rows(deal):
    rows, seen = [], set()
    for row in intake_selectors.coverage_rows(deal.id):
        if not row.in_force or row.line in seen or row.line not in lines.BY_KEY:
            continue
        seen.add(row.line)
        found = quote_facts.incumbent(deal, row.line) or {}
        rows.append(
            {
                'line': row.line,
                'label': lines.label(row.line),
                'carrier': found.get('carrier') or row.carrier or '',
                'plan': '',
                'funding': found.get('funding') or row.funding or '',
                'premium_month': None,
                'commission': comp.comp_label(revenue.comp_or_none(row.commission)),
                'expected': None,
                'renews': deal.effective_date,
            }
        )
    for line, found in intake_providers.quote_lines(deal.id).items():
        current = found.get('current')
        if not current or line in seen or line not in lines.BY_KEY:
            continue
        seen.add(line)
        rows.append(
            {
                'line': line,
                'label': lines.label(line),
                'carrier': current.get('carrier') or '',
                'plan': '',
                'funding': current.get('funding') or '',
                'premium_month': None,
                'commission': '',
                'expected': None,
                'renews': deal.effective_date,
            }
        )
    return sorted(rows, key=lambda row: lines.LINE_KEYS.index(row['line']))


def in_force(deal):
    if deal is None:
        return {'kind': None, 'rows': []}
    sold = _sold_rows(deal)
    if sold:
        return {'kind': SOLD, 'rows': sold}
    return {'kind': 'current', 'rows': _current_rows(deal)}
