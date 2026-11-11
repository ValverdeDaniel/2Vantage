"""Premium math (plan.md §5.5). Pure functions over plain data; the only place money is computed.

A `PlanData` is a plan's facts; `LineData` is one line's plans and rate basis. Selectors build them from models.
"""

import math
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from . import values as cleaning

TIERS = ['EE', 'ES', 'EC', 'FAM']
TIER_RATE = {'EE': 'rate_ee', 'ES': 'rate_es', 'EC': 'rate_ec', 'FAM': 'rate_fam'}
TIER_CONTRIB = {'EE': 'contrib_ee', 'ES': 'contrib_es', 'EC': 'contrib_ec', 'FAM': 'contrib_fam'}
REASON_WORDS = {
    'no_enrollment': 'enter enrollment',
    'missing_rate': 'a rate is missing for an enrolled tier',
    'per_plan_counts_needed': 'enter enrollment for each current plan',
}


def round_money(amount, places=0):
    """Half away from zero after reading the value at 15 significant digits — exactly Excel's ROUND."""
    if amount is None or not math.isfinite(amount):
        return None
    exact = Decimal(format(amount, '.15g')).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return int(exact) if places == 0 else float(exact) + 0.0


@dataclass
class PlanData:
    id: int
    role: str
    carrier: str = ''
    name: str = ''
    values: dict = field(default_factory=dict)
    enrollment: dict = field(default_factory=dict)
    enrollment_on: bool = False
    renews: int | None = None
    replaces: tuple = ()
    recommended: bool = False
    sold: bool = False

    @property
    def label(self):
        return self.name or self.carrier or f'Plan {self.id}'


@dataclass
class LineData:
    rate_basis: str
    plans: list

    def __post_init__(self):
        self.by_id = {plan.id: plan for plan in self.plans}
        self.current = [plan for plan in self.plans if plan.role == 'current']


def enrollment_keys(basis):
    if basis == 'composite':
        return TIERS
    return ['lives'] if basis in ('pepm', 'stop_loss') else ['volume']


def _typed(plan, keys):
    """The plan's typed enrollment when it is switched on and any figure is above zero."""
    if not plan.enrollment_on:
        return None
    figures = {key: float(plan.enrollment.get(key) or 0) for key in keys}
    return figures if any(figures.values()) else None


def base_ids(plan, line):
    """The current plan(s) a plan is measured against (§5.5)."""
    if plan.role == 'renewal':
        return [plan.renews] if plan.renews in line.by_id else []
    if plan.role == 'alternate':
        if plan.replaces:
            return [pid for pid in plan.replaces if pid in line.by_id]
        if len(line.current) == 1:
            return [line.current[0].id]
    return []


def _sum(enrollments, keys):
    return {key: sum(e[key] for e in enrollments) for key in keys}


def enrollment_for(plan, line):
    """(enrollment, source) or (None, reason) — §5.5 steps 1, 2, 3, 5 and 7 (4 and 6 need the census, Release 3)."""
    keys = enrollment_keys(line.rate_basis)
    own = _typed(plan, keys)
    if own:
        return own, 'typed'
    bases = [line.by_id[pid] for pid in base_ids(plan, line)]
    if plan.role in ('renewal', 'alternate') and bases:
        typed = [_typed(base, keys) for base in bases]
        if all(typed):
            return _sum(typed, keys), 'from current plan' if plan.role == 'renewal' else 'from replaced plan'
    if len(line.current) >= 2:
        return None, 'per_plan_counts_needed'
    return None, 'no_enrollment'


def _rate(plan, key):
    return cleaning.as_float(plan.values.get(key))


def _quoted(plan):
    quoted = _rate(plan, 'group_premium_monthly')
    return round_money(quoted) if quoted is not None else None


def monthly_premium(plan, line, enrollment):
    """(dollars, reason, quoted) for one plan given its enrollment (§5.5 table)."""
    basis = line.rate_basis
    if enrollment is None or not any(enrollment.values()):
        return None, 'no_enrollment', False
    if basis == 'composite':
        total = 0.0
        for tier in TIERS:
            count = enrollment.get(tier, 0)
            if count > 0:
                rate = _rate(plan, TIER_RATE[tier])
                if rate is None:
                    quoted = _quoted(plan)
                    return (quoted, None, True) if quoted is not None else (None, 'missing_rate', False)
                total += rate * count
        return round_money(total), None, False
    if basis == 'stop_loss':
        spec = _rate(plan, 'sl_spec_rate')
        if spec is None:
            quoted = _quoted(plan)
            return (quoted, None, True) if quoted is not None else (None, 'missing_rate', False)
        load = spec + (_rate(plan, 'sl_agg_rate') or 0) + (_rate(plan, 'sl_other_load') or 0)
        return round_money(load * enrollment['lives']), None, False
    unit = _rate(plan, 'unit_rate')
    if unit is None:
        quoted = _quoted(plan)
        return (quoted, None, True) if quoted is not None else (None, 'missing_rate', False)
    size = enrollment.get('volume', enrollment.get('lives', 0))
    divisor = {'volume_1000': 1000, 'weekly_10': 10, 'payroll_100': 1200, 'pepm': 1}[basis]
    return round_money(size / divisor * unit), None, False


def change(annual, base_annual):
    if annual is None or base_annual is None:
        return None
    pct = round_money((annual - base_annual) / base_annual * 100, 1) if base_annual else None
    return {'delta': annual - base_annual, 'pct': pct}


def same_enrollment(a, b):
    return a is not None and b is not None and all(abs(a[k] - b.get(k, 0)) < 1e-9 for k in a)


def employee_cost(plan):
    cost = {}
    for tier in TIERS:
        rate, contrib = _rate(plan, TIER_RATE[tier]), _rate(plan, TIER_CONTRIB[tier])
        cost[tier] = max(0.0, round_money(rate - contrib, 2)) if rate is not None and contrib is not None else None
    return cost


def tier_rate_change(plan, current):
    result = {}
    for tier in TIERS:
        new, old = _rate(plan, TIER_RATE[tier]), _rate(current, TIER_RATE[tier])
        if new is None or old is None:
            result[tier] = None
        else:
            result[tier] = {
                'delta': round_money(new - old, 2),
                'pct': round_money((new - old) / old * 100, 1) if old else None,
            }
    return result
