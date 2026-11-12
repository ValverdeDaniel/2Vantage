"""Who gets what, in numbers (plan.md §5.6; H.6 "Pure modules"). Plain data in, plain data out; every rounding goes
through `quotes.math.round_decimal`, half up like Excel (rule 5).

- `comp_amount`: the annual dollars a Comp is worth on a premium or a headcount (H6).
- `year_terms`: a split's rows as they pay in a given year: from year 2 a row's `renewal_amount` (0 pays nothing),
  and a row past `expires_after_years` drops out (H15, H121).
- `compute_shares`: shares of agency revenue as integer millionths (100 % = 1,000,000), worked out in the old order
  (891f1b3 `commissions/services.py: compute_shares`): gross rows off the top; the house takes its % of the rest;
  flat and PEPM rows come off the producer pool; % rows take their share of what is left after them; the primary keeps
  the rest; every row is capped at what is left. With no primary the house keeps the rest. The shares always total
  exactly 100 %.
- `dollars`: the shares in dollars at cents, summing to the revenue exactly (the residual cents go to the primary,
  else the house).
"""

from decimal import Decimal

from deals import comp as comps
from quotes.math import decimal, round_decimal

MILLION = 1_000_000
HUNDRED = Decimal(100)
MONTHS = 12


def _value(comp):
    return decimal((comp or {}).get('value'))


def comp_amount(comp, premium=None, employees=None, places=0):
    """Annual dollars a Comp is worth: pct → premium × value ÷ 100; flat → value; pepm → value × employees × 12.
    None when the figure it needs is missing. Rounded half up to `places` (whole dollars by default)."""
    value = _value(comp)
    if value is None:
        return None
    kind = comp.get('type') or comps.PCT
    if kind == comps.FLAT:
        amount = value
    elif kind == comps.PEPM:
        if employees is None:
            return None
        amount = value * decimal(employees) * MONTHS
    else:
        premium = decimal(premium)
        if premium is None:
            return None
        amount = premium * value / HUNDRED
    return round_decimal(amount, places)


def year_terms(rows, year):
    """The rows as they pay in `year` (1 = the first year; None = not known, which pays the renewal terms). The
    primary is never dropped."""
    n = year or 2
    out = []
    for row in rows:
        if row.get('role') != 'primary':
            expires = row.get('expires_after_years')
            if expires and n > expires:
                continue
            if n >= 2 and row.get('renewal_amount') is not None:
                row = {**row, 'amount': row['renewal_amount']}
        out.append(row)
    return out


def millionths(pct):
    """A percentage (Decimal or text) as integer millionths of the whole: 15 → 150,000."""
    return int(round_decimal(decimal(pct) * MILLION / HUNDRED))


def _fixed(row):
    return (row.get('amount') or {}).get('type') in (comps.FLAT, comps.PEPM)


def _fixed_share(row, revenue, employees, cap):
    """A flat or PEPM row's share of the revenue, capped; nothing while the revenue is unknown or zero."""
    amount = comp_amount(row.get('amount'), employees=employees, places=2)
    if amount is None or not revenue:
        return 0
    return min(int(round_decimal(amount * MILLION / revenue)), cap)


def compute_shares(revenue, rows, house_pct, employees=None):
    """[{party, role, share}] in millionths: the house first (party None), then the primary, the pool rows and the
    gross rows. `rows` are already year-applied; `house_pct` is 100 − the primary's producer %; `employees` is the
    headcount a PEPM split row pays on (the deal's medical employees, else its largest line's; OQ71)."""
    revenue = decimal(revenue)
    primary = next((row for row in rows if row.get('role') == 'primary'), None)
    others = [row for row in rows if row.get('role') != 'primary']
    gross = [row for row in others if row.get('basis') == 'gross']
    pool_rows = [row for row in others if row.get('basis') != 'gross']

    def out(row, share):
        return {'party': row.get('party'), 'role': row.get('role'), 'share': share}

    left = MILLION
    gross_out = []
    for row in [r for r in gross if _fixed(r)] + [r for r in gross if not _fixed(r)]:
        if _fixed(row):
            share = _fixed_share(row, revenue, employees, left)
        else:
            share = min(millionths(_value(row.get('amount')) or 0), left)
        left -= share
        gross_out.append(out(row, share))

    house = int(round_decimal(Decimal(left) * decimal(house_pct) / HUNDRED))
    pool = left - house
    shares = [{'party': None, 'role': 'house', 'share': house}]
    for row in [r for r in pool_rows if _fixed(r)]:
        share = _fixed_share(row, revenue, employees, pool)
        pool -= share
        shares.append(out(row, share))
    after_fixed = pool
    for row in [r for r in pool_rows if not _fixed(r)]:
        pct = _value(row.get('amount')) or Decimal(0)
        share = min(int(round_decimal(Decimal(after_fixed) * pct / HUNDRED)), pool)
        pool -= share
        shares.append(out(row, share))
    shares.extend(gross_out)
    if primary is not None:
        shares.insert(1, {'party': primary.get('party'), 'role': 'primary', 'share': pool})
    else:
        shares[0]['share'] += pool
    return shares


def dollars(revenue, shares):
    """Each share of `revenue` at cents, the residual cents to the primary (else the house), so they sum to the
    revenue exactly. None for each when the revenue is unknown."""
    revenue = decimal(revenue)
    if revenue is None:
        return [None for _ in shares]
    amounts = [round_decimal(revenue * share['share'] / MILLION, 2) for share in shares]
    residual = round_decimal(revenue, 2) - sum(amounts, Decimal(0))
    if residual:
        target = next((i for i, share in enumerate(shares) if share['role'] == 'primary'), 0)
        amounts[target] += residual
    return amounts


def pct_text(share):
    """Millionths as a percentage's text: 150,000 → '15', 333,333 → '33.3333'."""
    text = format(Decimal(share) / 10_000, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def pct_label(share):
    """Millionths as the editor shows a share, one decimal (the old `toFixed(1)`): 333,333 → '33.3%'."""
    return f'{round_decimal(Decimal(share) / 10_000, 1)}%'
