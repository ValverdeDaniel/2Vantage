"""What a deal books today (plan.md §5.6; H26, H27, H124, OQ75): read from the deal's line states, intake's coverage and
the rates, never written. `book_deal` writes these as records; the tab compares them with the booked ones (H120).

- A lost deal books nothing (H124), and neither does a deal with no sold plan (un-selling the last one voids every
  record, the Keep lines' too: H32).
- One target per line and carrier that has sold plans (OQ75): its premium is the Sold package of that carrier's sold
  plans (the sold set summed, bug 11), its employees that package's, its rate the deal's agreed rate, else the agency
  default (H5, H8).
- Plus the Intake "Keep as-is" lines with an in-force commission and no sold plan: rate `in_force`, the premium the
  line's Renewal, else Current, package (H26).
"""

from collections import namedtuple

from deals import lines
from deals.models import AgencySettings
from deals.rules import LOST
from intake import coverage as intake_coverage
from quotes import packages
from quotes.math import decimal, round_decimal
from quotes.selectors import deal_state

from . import book_rules, revenue
from .models import Commission

# facts: the sale's keys as `book_rules.facts` reads a record; origins: {key: 'sale' | 'agency' | 'in_force'}
Target = namedtuple('Target', 'line carrier facts origins')


def money_text(amount):
    """An annual premium as the record stores it: text at cents ("76092.00"), or None."""
    value = decimal(amount)
    return None if value is None else format(round_decimal(value, 2), 'f')


def _facts(deal, carrier, package, line, rate, plan_names):
    out = {
        'carrier': carrier,
        'premium_annual': money_text(package['annual']) if package else None,
        'rate': rate,
        'employees': revenue.employees_of(package, line) if package else None,
        'plan_label': book_rules.plan_label(plan_names),
        'plan_ids': list(package['plan_ids']) if package else [],
        'effective_date': deal.effective_date.isoformat() if deal.effective_date else None,
    }
    return {key: value for key, value in out.items() if value not in (None, '', [])}


def _sold(deal, line, state, rate, rate_origin):
    groups = {}
    for plan in state.data.plans:
        if plan.sold:
            groups.setdefault(plan.carrier, []).append(plan)
    for carrier, sold in groups.items():
        package = packages.package([plan.id for plan in sold], state.data, state.results, 'sold', 'Sold')
        facts = _facts(deal, carrier, package, line, rate, [plan.label for plan in sold])
        yield Target(line, carrier, facts, {'rate': rate_origin})


def _kept(deal, line, state, row):
    """A Keep-as-is line still in force that pays us (H26): rate `in_force`, premium from Renewal, else Current."""
    rate = revenue.comp_or_none(row.commission)
    current = [plan.carrier for plan in (state.data.plans if state else []) if plan.role == 'current' and plan.carrier]
    carrier = ', '.join(dict.fromkeys(current)) or row.carrier
    found = {package['key']: package for package in (state.packages if state else [])}
    priced = [found[key] for key in ('renewal', 'current') if key in found and found[key]['annual'] is not None]
    package = priced[0] if priced else None
    names = [state.data.by_id[pid].label for pid in package['plan_ids']] if package else []
    facts = _facts(deal, carrier, package, line, rate, names)
    facts.pop('plan_ids', None)  # a kept line has no sold plan
    return Target(line, carrier, facts, {'rate': 'in_force'})


def _keep_rows(deal):
    """{line: its first coverage row} for the lines kept as-is: in force, not shopped, on the proposal, with a comp."""
    shopped = set(deal.requested_lines or [])
    out = {}
    for line, row in revenue.coverage_rows(deal.id).items():
        this_year = intake_coverage.this_year_of(line in shopped, row.on_proposal)
        if row.in_force and this_year == intake_coverage.KEEP and revenue.comp_or_none(row.commission):
            out[line] = row
    return out


def targets(deal, states=None):
    """[Target] in §4.1's line order: what booking the deal now would write. `states` may be passed in by a caller that
    already worked them out (the tab)."""
    if deal.stage == LOST:
        return []
    states = deal_state(deal) if states is None else states
    if not any(plan.sold for state in states.values() for plan in state.data.plans):
        return []
    rates = Commission.objects.filter(deal_id=deal.id).values_list('rates', flat=True).first() or {}
    agency = revenue.comp_or_none(AgencySettings.get().default_commission)
    out = []
    keep = _keep_rows(deal)
    for line in [key for key in lines.LINE_KEYS if key in states or key in keep]:
        state = states.get(line)
        if state is not None and any(plan.sold for plan in state.data.plans):
            rate, source = revenue.effective(revenue.comp_or_none(rates.get(line)), agency)
            out.extend(_sold(deal, line, state, rate, 'agency' if source == 'agency' else 'sale'))
        elif line in keep:
            out.append(_kept(deal, line, state, keep[line]))
    return out
