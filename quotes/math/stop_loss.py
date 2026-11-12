"""Stop-loss arithmetic (plan.md §5.5, §9.13; F98–F107; the old pipeline/stop_loss_math.py at 891f1b3). Pure, in
Decimal: the Advisor's stop-loss board, its five-tab workbook and the tests share one arithmetic.

The vocabulary (the old workbook's Glossary):
- Annual = PEPM × enrolled employees × months. PEPM math uses EMPLOYEES, never members.
- Aggregate attachment (annual) = expected-claims factor PEPM × corridor × headcount × months, floored by any quoted
  minimum annual aggregate deductible (0 or blank: the attachment floats with the census).
- Additional laser liability = max(0, laser − specific deductible) per laser. "Compare laser liability, not premium."
- MAXIMUM ANNUAL LIABILITY = annual SL premium + annual admin + annual aggregate attachment + total laser liability:
  the verdict, never premium alone.
- Projected plan cost = annual SL premium + annual admin + expected claims (the factor before the corridor).

A missing LOAD-BEARING input (the specific rate; the factor and the corridor; the specific deductible under lasers)
makes what depends on it None, never a made-up number; a missing optional one (the aggregate rate, the other load,
the admin fee, lasers) counts as 0, as a blank sheet cell does.

`sl_lasers` is a text mini-format ("B.S. 200000, M.W. 90000"): claimant ids or initials, which are PHI (§3.8, rule 10).
`parse_lasers` keeps the claimant only so the workbook can line one person's lasers up across options (`shared_rows`);
everything this module returns to a reader names a laser by its position (1, 2, …), never by claimant (F104, OQ104).
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from .rounding import decimal, plain, round_decimal

MONTHS = 12
# The three premium components of the stop-loss PEPM. The SPECIFIC rate is load-bearing: no real stop-loss quote is
# without it, so agg or load alone never mint a premium (a partial read would show a huge fake saving).
PREMIUM_KEYS = ('sl_spec_rate', 'sl_agg_rate', 'sl_other_load')
# A candidate laser amount: a standalone number, optional decimals, optional k ("90k"), never after a minus sign.
_LASER_AMOUNT = re.compile(r'(?<![\w.,-])(\d+(?:\.\d+)?)\s*([kK]\b)?')
_THOUSANDS = re.compile(r'(?<=\d),(?=\d{3}\b)')
_ENTRY = re.compile(r'[,;\n]+')
NO_CLAIMANT = '—'


@dataclass(frozen=True)
class Laser:
    claimant: str  # never leaves quotes (rule 10): read only by `shared_rows`
    amount: Decimal


def parse_lasers(text):
    """`sl_lasers` → [Laser] in the order typed. Entries split on commas, semicolons and new lines (thousands
    separators first, so "90,000" stays one entry); an entry's amount is its LARGEST standalone number, so "B.S. 200000
    (renal)" keeps its claimant; "90k" reads 90,000; a bare number under three digits is a note, not an amount; an
    entry with no amount is skipped. The claimant is whatever precedes the amount."""
    found = []
    for raw in _ENTRY.split(_THOUSANDS.sub('', str(text or ''))):
        raw = raw.strip()
        candidates = []
        for match in _LASER_AMOUNT.finditer(raw):
            figure = Decimal(match.group(1))
            if match.group(2) or figure >= 100:
                candidates.append((figure * (1000 if match.group(2) else 1), match))
        if not candidates:
            continue
        amount, best = max(candidates, key=lambda pair: pair[0])
        if amount <= 0:
            continue
        found.append(Laser(raw[: best.start()].strip(' \t:=$-') or NO_CLAIMANT, amount))
    return found


def annual(pepm, headcount, months=MONTHS):
    """PEPM × headcount × months, or None when the PEPM is unknown or nobody is counted."""
    if pepm is None or not headcount or not months:
        return None
    return pepm * headcount * months


def attachment(factor, corridor, headcount, months=MONTHS, floor=None):
    """Factor × corridor × headcount × months, floored by a quoted minimum annual aggregate deductible."""
    if factor is None or corridor is None or not headcount or not months:
        return None
    computed = factor * corridor * headcount * months
    return max(computed, floor) if floor else computed


def above_spec(amount, spec):
    """What one laser adds above the specific deductible, floored at 0; None when the deductible is unknown."""
    if amount is None or spec is None:
        return None
    return max(Decimal(0), amount - spec)


def laser_liability(amounts, spec):
    """Σ max(0, laser − spec): 0 with no lasers; None when there are lasers but no specific deductible."""
    if not amounts:
        return Decimal(0)
    if spec is None:
        return None
    return sum((above_spec(amount, spec) for amount in amounts), Decimal(0))


def _premium_pepm(parts):
    spec, agg, load = parts
    if spec is None:
        return None
    return spec + (agg or 0) + (load or 0)


def summary(values, headcount, months=MONTHS, without=()):
    """Everything the analysis derives from one plan's values ({field: typed text}), exactly, as Decimals.

    `without` holds laser positions (1-based) the what-if leaves out (F104): never stored; ignored while the specific
    deductible is unknown, as the old toggles were. `lasers` lists each laser by position with what it adds."""
    headcount = decimal(headcount)
    spec = decimal(values.get('sl_spec_deductible'))
    parts = [decimal(values.get(key)) for key in PREMIUM_KEYS]
    premium_pepm = _premium_pepm(parts)
    admin_pepm = decimal(values.get('tpa_admin_fee'))
    factor = decimal(values.get('sl_agg_factor'))
    corridor = decimal(values.get('sl_agg_corridor'))
    floor = decimal(values.get('sl_agg_floor'))
    dropped = {int(n) for n in without} if spec is not None else set()
    lasers = [
        {'n': n, 'amount': laser.amount, 'extra': above_spec(laser.amount, spec), 'included': n not in dropped}
        for n, laser in enumerate(parse_lasers(values.get('sl_lasers')), start=1)
    ]
    counted = [laser['amount'] for laser in lasers if laser['included']]
    annual_premium = annual(premium_pepm, headcount, months)
    annual_admin = annual(admin_pepm, headcount, months) or Decimal(0)
    annual_attachment = attachment(factor, corridor, headcount, months, floor)
    expected = annual(factor, headcount, months)
    lasers_total = laser_liability(counted, spec)
    scored = None not in (annual_premium, annual_attachment, lasers_total)
    return {
        'headcount': headcount,
        'months': months,
        'spec_deductible': spec,
        'spec_rate': parts[0],
        'agg_rate': parts[1],
        'other_load': parts[2],
        'premium_pepm': premium_pepm,
        'annual_premium': annual_premium,
        'admin_pepm': admin_pepm,
        'annual_admin': annual_admin,
        'factor_pepm': factor,
        'corridor': corridor,
        'attachment_floor': floor,
        'attachment_pepm': factor * corridor if factor is not None and corridor is not None else None,
        'annual_attachment': annual_attachment,
        'annual_expected_claims': expected,
        'lasers': lasers,
        'laser_count': (
            sum(1 for amount in counted if amount > spec) if spec is not None else (None if counted else 0)
        ),
        'laser_liability': lasers_total,
        'fixed_cost': annual_premium + annual_admin if annual_premium is not None else None,
        'projected_cost': annual_premium + annual_admin + expected if None not in (annual_premium, expected) else None,
        'max_annual_liability': annual_premium + annual_admin + annual_attachment + lasers_total if scored else None,
        'what_if': bool(dropped & {laser['n'] for laser in lasers}),
    }


def difference(mine, theirs):
    """`mine` − `theirs`, or None when either is missing: a delta with a hole in it is not a delta."""
    if mine is None or theirs is None:
        return None
    return mine - theirs


def against_current(option, current):
    """An option's deltas against the one in-force contract (negative: lower than today). The laser delta needs a
    stated premium too: an option with no specific rate has laser liability 0, which would otherwise read as saving
    the whole in-force laser layer (the old workbook's own gate)."""
    quoted = option['annual_premium'] is not None
    return {
        'max_annual_liability': difference(option['max_annual_liability'], current['max_annual_liability']),
        'annual_premium': difference(option['annual_premium'], current['annual_premium']),
        'laser_liability': difference(option['laser_liability'], current['laser_liability']) if quoted else None,
    }


def per_month(annual_figure, months=MONTHS):
    """An annual figure a month (the workbook's Monthly column, derived back from the annual)."""
    if annual_figure is None or not months:
        return None
    return annual_figure / decimal(months)


def per_employee(annual_figure, headcount, months=MONTHS):
    """An annual figure per employee per month (the workbook's PEPM column, derived back from the annual)."""
    if annual_figure is None or not headcount or not months:
        return None
    return annual_figure / decimal(headcount) / decimal(months)


def total(figures):
    """Figures summed, the missing ones skipped (a sheet's SUM over typed cells)."""
    return sum((figure for figure in figures if figure is not None), Decimal(0))


def times(*figures):
    """The product of figures, or None when any is missing (a sheet's PEPM × headcount)."""
    out = Decimal(1)
    for figure in figures:
        figure = decimal(figure)
        if figure is None:
            return None
        out *= figure
    return out


def shared_rows(lasers_by_plan):
    """The workbook's shared laser rows: one row per claimant across options (first seen first), each option's own
    amount on its claimant's row; a laser with no claimant gets a row of its own, never merged with another. Returns
    (row count, [{row: amount}] in the plans' order). The rows are numbered; no claimant leaves this function."""
    rows, out = {}, []
    for i, lasers in enumerate(lasers_by_plan):
        mine = {}
        for j, laser in enumerate(lasers):
            claimant = laser.claimant.strip()
            key = claimant.casefold() if claimant and claimant != NO_CLAIMANT else ('anon', i, j)
            rows.setdefault(key, len(rows) + 1)
            mine[rows[key]] = laser.amount
        out.append(mine)
    return len(rows), out


def lf_split(values):
    """A level-funded plan's "% to claims" (F107): {claim_funding, fixed_costs, monthly_total, pct_to_claims}, or None
    without the claim funding AND at least one fixed bucket (a partial read would score itself 100%)."""
    claims = decimal(values.get('lf_claim_funding'))
    fixed = [decimal(values.get(key)) for key in ('lf_stop_loss_premium', 'lf_admin_fee', 'lf_tro')]
    stated = [figure for figure in fixed if figure is not None]
    if claims is None or not stated:
        return None
    total = claims + sum(stated, Decimal(0))
    if total <= 0:
        return None
    return {
        'claim_funding': plain(claims),
        'fixed_costs': plain(sum(stated, Decimal(0))),
        'monthly_total': plain(total),
        'pct_to_claims': float(round_decimal(claims / total * 100, 1)),
    }


# What the board shows of each exact figure: annual money in whole dollars, PEPM money in cents (one figure never
# reads three ways across the board, the quote board and the workbook).
WHOLE = (
    'spec_deductible',
    'annual_premium',
    'annual_admin',
    'attachment_floor',
    'annual_attachment',
    'annual_expected_claims',
    'laser_liability',
    'fixed_cost',
    'projected_cost',
    'max_annual_liability',
)
CENTS = ('spec_rate', 'agg_rate', 'other_load', 'premium_pepm', 'admin_pepm', 'factor_pepm', 'attachment_pepm')


def money(figure, places=0):
    """One figure as the API sends it: rounded half up (Excel's ROUND), as a plain number."""
    return plain(round_decimal(figure, places)) if figure is not None else None


def shown(found):
    """A `summary` as the board shows it: every money figure rounded once, here; counts and the corridor as stated."""
    out = {key: money(found[key]) for key in WHOLE}
    out.update({key: money(found[key], 2) for key in CENTS})
    out.update(
        {
            'headcount': plain(found['headcount']),
            'months': found['months'],
            'corridor': plain(found['corridor']),
            'laser_count': found['laser_count'],
            'lasers': [
                {
                    'n': laser['n'],
                    'amount': money(laser['amount']),
                    'extra': money(laser['extra']),
                    'included': laser['included'],
                }  # fmt: skip
                for laser in found['lasers']
            ],
        }
    )
    return out
