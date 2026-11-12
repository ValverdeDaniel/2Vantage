"""Which enrollment prices a plan (plan.md §5.5, O.6 #24). Pure, over `shapes.LineData`.

The shape follows the line's rate basis (`deals.lines.ENROLLMENT_KEYS`): tier counts `{EE, ES, EC, FAM}` for composite
lines, `{volume}` for volume_1000, weekly_10 and payroll_100, `{lives}` for pepm and stop_loss. Figures are Decimals.

Built today: step 1 (the plan's own typed counts), step 3 (a renewal's or replaced plans' typed counts) and step 5
(two or more current plans stop). Priced versions, the census, the line figure and borrowing arrive with slices 13
and 35 (`LineEnrollment`, the census rollup).
"""

from decimal import Decimal

from deals import lines

from .rounding import decimal, plain

TIERS = lines.TIER_CODES


def enrollment_keys(basis):
    return list(lines.ENROLLMENT_KEYS[basis])


def typed(plan, keys):
    """The plan's typed figures when they are switched on and any is above zero, else None."""
    if not plan.enrollment_on:
        return None
    figures = {key: decimal(plan.enrollment.get(key)) or Decimal(0) for key in keys}
    return figures if any(figures.values()) else None


def total(enrollments, keys):
    """Several plans' figures summed key by key (a consolidation carries the people of every plan it replaces)."""
    return {key: sum((e[key] for e in enrollments), Decimal(0)) for key in keys}


def enrollment_for(plan, line):
    """(figures, source) or (None, reason)."""
    keys = enrollment_keys(line.rate_basis)
    own = typed(plan, keys)
    if own:
        return own, 'typed'
    bases = [line.by_id[pid] for pid in line.base_ids(plan)]
    if plan.role in ('renewal', 'alternate') and bases:
        figures = [typed(base, keys) for base in bases]
        if all(figures):
            return total(figures, keys), 'from current plan' if plan.role == 'renewal' else 'from replaced plan'
    if len(line.current) >= 2:
        return None, 'per_plan_counts_needed'
    return None, 'no_enrollment'


def same_people(a, b):
    """Whether two enrollments count the same people, key by key (§5.5's "apples to apples")."""
    if a is None or b is None:
        return False
    return all(decimal(a[key]) == decimal(b.get(key, 0)) for key in a)


def as_plain(figures):
    """Figures as the API's numbers."""
    return None if figures is None else {key: plain(value) for key, value in figures.items()}
