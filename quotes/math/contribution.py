"""The employer's contribution on the client spreadsheet's Compare tab (plan.md §5.5, §9.4; J148 "contribution modes";
ported from old Vantage 891f1b3 `presentation_math` and `contribution_math`). Pure, in Decimal; None is a blank cell.

Two modes, as Bryke's file has them: a percent the employer pays of the employee rate and one of the dependent cost
(each tier's rate less the employee rate), or the dollars a month it pays for each tier. The dollars win once any tier
holds one, and a tier left blank then pays nothing. Each function is the figure of one formula in
`proposals/workbook/formulas.py`; the workbook stores it as the cell's result. `inputs` is what the Compare tab's
inputs start from: the current plan's own share, never an assumed one.
"""

from decimal import Decimal

from .enrollment import TIERS
from .rounding import decimal, round_decimal

DEPENDENT_TIERS = TIERS[1:]
AGREE = Decimal('0.001')  # dependent tiers whose shares agree within a tenth of a percent state one percent


def employer_share(rate, contribution):
    """The share of `rate` the employer pays: None for a blank or zero rate; a blank contribution is 0."""
    rate = decimal(rate)
    if rate is None or rate == 0:
        return None
    return (decimal(contribution) or Decimal(0)) / rate


def inputs(rates, contributions, people):
    """{'ee_pct', 'dep_pct', 'tier'}: the current plan's share as the Compare tab's inputs. Bryke's two percents when
    its figures state one: employees from the employee contribution over the employee rate, dependents from each
    tier's contribution above the employee's over its rate above the employee's, every stating tier agreeing within a
    tenth of a percent (or none stating one). Otherwise the dollars it pays each tier, when every tier with people has
    a figure. Otherwise nothing. `rates`, `contributions`, `people`: {tier: value}."""
    blank = {'ee_pct': None, 'dep_pct': None, 'tier': None}
    ee_rate, ee_share = decimal(rates.get('EE')), decimal(contributions.get('EE'))
    out = dict(blank)
    if ee_rate and ee_share is not None:
        share = employer_share(ee_rate, ee_share)
        if share is not None and 0 <= share <= 1:
            out['ee_pct'] = round_decimal(share, 4)
    shares = []
    for tier in DEPENDENT_TIERS:
        rate, paid = decimal(rates.get(tier)), decimal(contributions.get(tier))
        if None in (rate, paid, ee_rate, ee_share) or rate <= ee_rate:
            continue
        shares.append((paid - ee_share) / (rate - ee_rate))
    if shares and max(shares) - min(shares) <= AGREE and min(shares) >= 0 and max(shares) <= 1:
        out['dep_pct'] = round_decimal(sum(shares) / len(shares), 4)
    stated = any(decimal(contributions.get(tier)) is not None for tier in DEPENDENT_TIERS)
    if out['ee_pct'] is not None and (out['dep_pct'] is not None or not stated):
        return out
    amounts = {tier: decimal(contributions.get(tier)) for tier in TIERS}
    if (
        amounts['EE'] is not None
        and all(amount is None or amount >= 0 for amount in amounts.values())
        and all(amount is not None or not decimal((people or {}).get(tier)) for tier, amount in amounts.items())
    ):
        return {**blank, 'tier': amounts}
    return blank


def _enrolled(counts):
    return sum((decimal(counts.get(tier)) or Decimal(0) for tier in TIERS), Decimal(0))


def _by_tier(amounts):
    return any(decimal(amount) is not None for amount in (amounts or {}).values())


def for_employees(counts, rates, pct, amounts=None):
    """The employer's monthly cost toward each enrolled person's employee rate under the percent, whole dollars; None
    when a tier holds dollars, nobody is enrolled, or there is no employee rate or no percent."""
    enrolled, ee, pct = _enrolled(counts), decimal(rates.get('EE')), decimal(pct)
    if _by_tier(amounts) or enrolled == 0 or ee is None or pct is None:
        return None
    return round_decimal(enrolled * ee * pct)


def for_dependents(counts, rates, pct, amounts=None):
    """The employer's monthly cost toward the dependent part of each tier (its rate less the employee rate, never below
    0) under the percent; None when a tier holds dollars, nobody is enrolled, no percent, or an enrolled dependent tier
    (or the employee rate) has no rate. A tier nobody is in adds 0."""
    pct = decimal(pct)
    if _by_tier(amounts) or _enrolled(counts) == 0 or pct is None:
        return None
    ee = decimal(rates.get('EE'))
    for tier in DEPENDENT_TIERS:
        if (decimal(counts.get(tier)) or 0) != 0 and (decimal(rates.get(tier)) is None or ee is None):
            return None
    total = Decimal(0)
    for tier in DEPENDENT_TIERS:
        count = decimal(counts.get(tier)) or Decimal(0)
        if count:
            total += count * max(Decimal(0), decimal(rates[tier]) - ee)
    return round_decimal(total * pct)


def for_tier(count, rate, amount, amounts):
    """One tier's monthly cost under the dollars: its people times the dollars, never more than its rate nor below 0;
    a tier left blank pays 0. None when no tier holds dollars, nobody is in the tier, or it has no rate."""
    count, rate, amount = decimal(count) or Decimal(0), decimal(rate), decimal(amount)
    if not _by_tier(amounts) or not count or rate is None:
        return None
    if amount is None:
        return Decimal(0)
    return round_decimal(count * max(Decimal(0), min(amount, rate)))


def employer_total(*parts):
    """The parts that hold a figure, summed; None when none does."""
    found = [decimal(part) for part in parts if decimal(part) is not None]
    return sum(found, Decimal(0)) if found else None


def employee_total(monthly, employer):
    """What the people pay a month: the total less the employer's, never below 0."""
    monthly, employer = decimal(monthly), decimal(employer)
    if monthly is None or employer is None:
        return None
    return max(Decimal(0), monthly - employer)
