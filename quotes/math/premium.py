"""The monthly premium by rate basis, and the figures derived from it (plan.md §5.5). Pure, in Decimal.

`monthly_premium(plan, line, enrollment) -> (dollars | None, reason, quoted)`; `quoted` says the quoted premium
(`group_premium_monthly`) was used. No enrollment, no price: a price with nobody enrolled is "no price", never $0.
"""

from decimal import Decimal

from .. import fields
from .enrollment import TIERS
from .rounding import decimal, plain, round_decimal

TIER_RATE = dict(zip(TIERS, fields.TIER_RATE_KEYS, strict=True))
TIER_CONTRIB = dict(zip(TIERS, fields.CONTRIB_KEYS, strict=True))
REASON_WORDS = {
    'no_enrollment': 'enter enrollment',
    'missing_rate': 'a rate is missing for an enrolled tier',
    'per_plan_counts_needed': 'enter enrollment for each current plan',
}
# The divisor of each unit-rate basis: volume ÷ 1,000; weekly benefit ÷ 10; annual payroll ÷ 12 ÷ 100; lives.
UNIT_DIVISOR = {'volume_1000': 1000, 'weekly_10': 10, 'payroll_100': 1200, 'pepm': 1}


def rate(plan, key):
    return decimal(plan.values.get(key))


def _quoted(plan):
    """The quoted premium, rounded, or no price when the plan has none."""
    quoted = round_decimal(rate(plan, 'group_premium_monthly'))
    return (quoted, None, True) if quoted is not None else (None, 'missing_rate', False)


def monthly_premium(plan, line, enrollment):
    basis = line.rate_basis
    if enrollment is None or not any(enrollment.values()):
        return None, 'no_enrollment', False
    if basis == 'composite':
        amount = Decimal(0)
        for tier in TIERS:
            count = decimal(enrollment.get(tier)) or Decimal(0)
            if count > 0:
                tier_rate = rate(plan, TIER_RATE[tier])
                if tier_rate is None:
                    return _quoted(plan)
                amount += tier_rate * count
        return round_decimal(amount), None, False
    if basis == 'stop_loss':
        spec = rate(plan, 'sl_spec_rate')
        if spec is None:
            return _quoted(plan)
        load = spec + (rate(plan, 'sl_agg_rate') or 0) + (rate(plan, 'sl_other_load') or 0)
        return round_decimal(load * decimal(enrollment['lives'])), None, False
    unit = rate(plan, 'unit_rate')
    if unit is None:
        return _quoted(plan)
    size = decimal(enrollment.get('volume', enrollment.get('lives')))
    # Multiplied before it is divided, so an exact figure stays exact (1/12 has no end in decimals).
    return round_decimal(size * unit / UNIT_DIVISOR[basis]), None, False


def annual(monthly):
    """Twelve times a monthly premium (already rounded), or None: the year every file prints beside the month."""
    monthly = decimal(monthly)
    return None if monthly is None else monthly * 12


def change(annual, base_annual):
    """{delta, pct} against the base's annual premium, or None; `pct` is None when the base is 0."""
    annual, base_annual = decimal(annual), decimal(base_annual)
    if annual is None or base_annual is None:
        return None
    delta = annual - base_annual
    pct = round_decimal(delta / base_annual * 100, 1) if base_annual else None
    return {'delta': plain(delta), 'pct': None if pct is None else float(pct)}


def monthly_change(monthly, base_monthlies):
    """A plan's change a month against the plans it is compared with, their monthly premiums summed: {delta, pct}, or
    None when a figure is missing (Pages' "Change vs current", J.6.7 `monthly_delta`; slice 14)."""
    bases = [decimal(base) for base in base_monthlies]
    if not bases or any(base is None for base in bases):
        return None
    return change(monthly, sum(bases, Decimal(0)))


def add(amounts):
    """Money figures summed in Decimal (the proposal summary's totals across lines, J64), or None when any is missing:
    a total with a hole in it is not a total."""
    found = [decimal(amount) for amount in amounts]
    if not found or any(amount is None for amount in found):
        return None
    return plain(sum(found, Decimal(0)))


def employee_cost(plan):
    """What an employee pays a month per tier: max(0, rate − contribution) to the cent; None when either is blank."""
    cost = {}
    for tier in TIERS:
        tier_rate, contrib = rate(plan, TIER_RATE[tier]), rate(plan, TIER_CONTRIB[tier])
        if tier_rate is None or contrib is None:
            cost[tier] = None
        else:
            cost[tier] = float(max(Decimal(0), round_decimal(tier_rate - contrib, 2)))
    return cost


def tier_rate_change(plan, current):
    """A renewal's change per tier against its current plan's rate: {delta, pct} or None."""
    result = {}
    for tier in TIERS:
        new, old = rate(plan, TIER_RATE[tier]), rate(current, TIER_RATE[tier])
        if new is None or old is None:
            result[tier] = None
        else:
            pct = round_decimal((new - old) / old * 100, 1) if old else None
            result[tier] = {'delta': float(round_decimal(new - old, 2)), 'pct': None if pct is None else float(pct)}
    return result
