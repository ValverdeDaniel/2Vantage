"""The rates grid and what the deal is worth (plan.md §5.6; H3–H8). One read in a fixed number of queries: the deal's
line states (`quotes.selectors.deal_state`, every line in one grouped read), intake's coverage rows and the agency
default.

- Rows (H3): the requested lines (else the lines with plans, else medical), the lines with an agreed rate and the
  lines with a sold plan, in §4.1's order; then the in-force lines with a commission that are not being quoted, muted.
- In-force (H4): the incumbent's commission from intake's coverage row, and its carrier from the current plans, else
  the coverage row (the shared incumbent rule, `quotes.facts.incumbent`).
- Effective rate (H5, H8): the deal's agreed rate, else the agency default, else none.
- Basis (H6, OQ74 default): once the line has a sold plan, only the Sold package (with its reason when it has no
  total); before, Renewal, then Current, then the first starred plan as a one-plan "estimate": the first with a total.
- Expected (H6, H7): `math.comp_amount` on the basis package's annual premium, or on its own employees for a PEPM rate.
  The deal total is the sum of the lines that have a figure. A PEPM split row counts the deal's medical employees,
  else the largest line's, never a sum (OQ71).
"""

from decimal import Decimal

from deals import comp as comps
from deals import lines
from intake import coverage as intake_coverage
from intake.models import CurrentCoverage
from quotes import packages
from quotes.math import SOURCES, decimal, plain
from quotes.selectors import deal_state
from quotes.selectors.state import empty

from . import math, vocab

MEDICAL = 'medical'
SOURCE_WORDS = dict(intake_coverage.COMMISSION_SOURCES)
NO_COUNTS = 'Enrollment counts are unknown, so no premium can be computed yet.'


def comp_or_none(raw):
    found, error = comps.parse_comp(raw, allow_blank=True)
    return None if error else found


def effective(agreed, agency):
    """(the rate that applies, its source): the deal's agreed rate, else the agency default (H5, H8)."""
    if agreed:
        return agreed, vocab.RATE_DEAL
    if agency:
        return agency, vocab.RATE_AGENCY
    return None, ''


def _order(key):
    return lines.LINE_KEYS.index(key) if key in lines.LINE_KEYS else len(lines.LINE_KEYS)


def shown_lines(requested, rates, plan_lines, sold_lines):
    keys = [key for key in lines.LINE_KEYS if key in set(requested or [])]
    keys = keys or [key for key in lines.LINE_KEYS if key in plan_lines] or [MEDICAL]
    extra = [key for key in [*rates, *sold_lines] if key in lines.BY_KEY and key not in keys]
    return sorted(dict.fromkeys([*keys, *extra]), key=_order)


def employees_of(package, line):
    """The people a package covers as employees: the tier counts summed, or the lives; None for a volume line."""
    enrollment = (package or {}).get('enrollment')
    if not enrollment:
        return None
    keys = lines.ENROLLMENT_KEYS.get(lines.BY_KEY[line]['rate_basis'], ())
    if 'volume' in keys:
        return None
    total = sum((decimal(enrollment.get(key)) or Decimal(0) for key in keys), Decimal(0))
    return int(total) if total else None


def basis(state):
    """The package a line's revenue is worked out on, or None (§5.6)."""
    found = {package['key']: package for package in state.packages}
    if 'sold' in found:
        return found['sold']
    for key in ('renewal', 'current'):
        if key in found and found[key]['annual'] is not None:
            return found[key]
    starred = next((plan for plan in state.data.plans if plan.starred), None)
    if starred is not None:
        one = packages.package([starred.id], state.data, state.results, 'estimate', 'estimate')
        if one['annual'] is not None:
            return one
    return None


def _basis_block(state, package, line):
    if package is None:
        return None
    by_id = state.data.by_id
    plans = [f'{by_id[pid].carrier} — {by_id[pid].label}'.strip(' —') for pid in package['plan_ids']]
    sources = {state.results[pid]['enrollment_source'] for pid in package['plan_ids'] if pid in state.results}
    sources.discard(None)
    words = [SOURCES[key]['label'] for key in sorted(sources) if key in SOURCES]
    if len(plans) == 1:
        label = plans[0] + (' (estimate)' if package['key'] == 'estimate' else '')
    else:
        label = f'{vocab.BASIS_PACKAGES.get(package["key"], package["label"])} · {len(plans)} plans'
    return {
        'key': package['key'],
        'label': label,
        'plans': plans,
        'annual': package['annual'],
        'employees': employees_of(package, line),
        'enrollment_source': ' · '.join(words),
        'reason': package['reason'] if package['annual'] is None else None,
    }


def _coverage(deal_id):
    """{line: first in-force coverage row} in the card's order (the row the intent card decides on)."""
    out = {}
    for row in CurrentCoverage.objects.filter(deal_id=deal_id, in_force=True).order_by('sort_order', 'id'):
        out.setdefault(row.line, row)
    return out


def _in_force(state, row):
    current = [plan.carrier for plan in (state.data.plans if state else []) if plan.role == 'current' and plan.carrier]
    carrier = ', '.join(dict.fromkeys(current)) or (row.carrier if row else '')
    comp = comp_or_none(row.commission) if row else None
    if not comp and not carrier:
        return None
    return {
        'label': comps.comp_label(comp),
        'carrier': carrier,
        'source': row.commission_source if row and comp else '',
        'source_label': SOURCE_WORDS.get(row.commission_source, '') if row and comp else '',
    }


def line_rows(deal, rates, agency):
    """(rows, total, note, employees for a PEPM split row) for the grid (H3–H8). `rates` is the deal's {line: Comp};
    `agency` the agency default Comp or None."""
    states = deal_state(deal)
    sold_lines = [key for key, state in states.items() if any(plan.sold for plan in state.plans)]
    keys = shown_lines(deal.requested_lines, rates, states, sold_lines)
    coverage = _coverage(deal.id)
    rows, total, counted = [], Decimal(0), False
    for key in keys:
        state = states.get(key) or empty(key)
        agreed = comp_or_none(rates.get(key))
        rate, source = effective(agreed, agency)
        block = _basis_block(state, basis(state), key)
        expected = math.comp_amount(rate, block and block['annual'], block and block['employees'])
        if expected is not None:
            total += expected
            counted = True
        rows.append(_row(key, state, coverage.get(key), agreed, rate, source, block, expected))
    for key in sorted(set(coverage) - set(keys), key=_order):
        if key in lines.BY_KEY and comp_or_none(coverage[key].commission):
            rows.append(_row(key, states.get(key), coverage[key], None, None, '', None, None, muted=True))
    people = _split_employees(rows)
    return rows, (plain(total) if counted else None), _note(rows, people), people


def _row(key, state, coverage_row, agreed, rate, source, block, expected, muted=False):
    return {
        'line': key,
        'label': lines.label(key),
        'not_requested': muted,
        'in_force': _in_force(state, coverage_row),
        'has_coverage': coverage_row is not None,
        'rate': agreed,
        'effective': rate,
        'effective_label': comps.comp_label(rate),
        'source': source,
        'source_label': vocab.RATE_SOURCES[source] if not muted else '',
        'basis': block,
        'expected': plain(expected),
    }


def _split_employees(rows):
    """(employees, line) a PEPM split row pays on: medical's, else the largest line's (OQ71)."""
    counted = [(row['basis']['employees'], row['line']) for row in rows if row['basis'] and row['basis']['employees']]
    medical = next((pair for pair in counted if pair[1] == MEDICAL), None)
    return medical or max(counted, default=(None, None))


def _note(rows, people):
    employees, line = people
    if employees is None:
        return NO_COUNTS
    row = next(row for row in rows if row['line'] == line)
    where = row['basis']['enrollment_source'].lower() or 'source not known'
    return f'Based on {employees} enrolled on {lines.label(line)} ({where}).'
