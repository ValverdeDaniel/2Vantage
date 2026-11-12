"""All money math (plan.md §5.5, OQ9 b), one module per idea: `rounding` (round_decimal, the only rounding of money),
`enrollment` (which enrollment prices a plan) and `premium` (the monthly premium by rate basis and what derives from
it). `pricing.py` (priced versions, slice 35) and `stop_loss.py` (slice 36) join here. Pure functions over
`quotes.shapes`; every figure is a Decimal until `rounding.plain` makes it the API's number.
"""

from .enrollment import TIERS, enrollment_for, enrollment_keys, same_people, total, typed
from .premium import (
    REASON_WORDS,
    TIER_CONTRIB,
    TIER_RATE,
    change,
    employee_cost,
    monthly_premium,
    rate,
    tier_rate_change,
)
from .rounding import decimal, plain, round_decimal, round_money

__all__ = [
    'REASON_WORDS',
    'TIERS',
    'TIER_CONTRIB',
    'TIER_RATE',
    'change',
    'decimal',
    'employee_cost',
    'enrollment_for',
    'enrollment_keys',
    'monthly_premium',
    'plain',
    'rate',
    'round_decimal',
    'round_money',
    'same_people',
    'tier_rate_change',
    'total',
    'typed',
]
