"""The census's rollups for pricing and the other apps (plan.md §5.3.6, §5.3.7; C39–C46). Pure.

`compute(people)` is what `CensusFacts.rollup` stores, over employees' approved values only (dependents are never
counted): each tier column's counts (EE, ES, EC, FAM, waived, blank, and `unknown` for a word that is none of them),
the same counts per distinct plan text on medical, dental and vision — exactly the per-plan counts a person would
otherwise count and retype, which quotes matches to its current plans (§5.5) — each volume column's sum, and the
employee count. `for_line(rollup, line)` reads one line out of it (§4.1's "Priced from"):
- a composite line with its own tier column: that column's counts (C39), and the enrolled employees (C43);
- a worksite composite line: the medical tier counts, "Borrowed from medical" (`source` 'borrowed');
- a volume line: the sum of its column over employees (C42); a PEPM line: the employee count;
- stop-loss: the medical EE + ES + EC + FAM total, else the employee count (C44).
`fte` (C45) and `aged_65` (C46) are worked out on read from the people: they depend on the intake's hours threshold
and the deal's effective date, which change without a census write.
"""

from decimal import Decimal, InvalidOperation

from deals import lines

from . import fields
from .importer.words import is_waiver, tier_code
from .values import age_on, parse_date

BUCKETS = ('EE', 'ES', 'EC', 'FAM', 'waived', 'blank', 'unknown')
DEFAULT_FULL_TIME_HOURS = 30
MEDICARE_AGE = 65
BORROWED = 'borrowed'
CENSUS = 'census'


def _bucket(raw):
    text = (raw or '').strip()
    if not text:
        return 'blank'
    return tier_code(text) or ('waived' if is_waiver(text) else 'unknown')


def _number(raw):
    try:
        return Decimal(str(raw).replace('$', '').replace(',', '').strip())
    except (InvalidOperation, ValueError):
        return None


def _empty():
    return dict.fromkeys(BUCKETS, 0)


def compute(people):
    """The stored rollup over the people (dicts with `kind` and `values`)."""
    employees = [person['values'] for person in people if person['kind'] == fields.EMPLOYEE]
    tiers = {key: _empty() for key in fields.TIER_KEYS}
    by_plan = {line: {} for line in fields.PLAN_FIELDS}
    volumes = {}
    for values in employees:
        for key in fields.TIER_KEYS:
            tiers[key][_bucket(values.get(key))] += 1
        for line, plan_key in fields.PLAN_FIELDS.items():
            text = (values.get(plan_key) or '').strip()
            tier_key = lines.BY_KEY[line]['tier_field']
            by_plan[line].setdefault(text, _empty())[_bucket(values.get(tier_key))] += 1
        for key in set(fields.VOLUME_FIELDS.values()):
            amount = _number(values.get(key)) if values.get(key) else None
            if amount is not None:
                volumes[key] = volumes.get(key, Decimal(0)) + amount
    return {
        'employees': len(employees),
        'tiers': tiers,
        'by_plan': by_plan,
        'volumes': {key: str(total) for key, total in sorted(volumes.items())},
    }


def enrolled(counts):
    """Employees whose tier is a tier code: never Waived, blank or an unknown word (C43)."""
    return sum(counts.get(code, 0) for code in lines.TIER_CODES)


def for_line(rollup, line):
    """One line's census figures, or None when the census holds nothing for it (§4.1, §5.3.6)."""
    entry = lines.get(line)
    if entry is None or not rollup or not rollup.get('employees'):
        return None
    basis, tier_key = entry['rate_basis'], entry['tier_field']
    if basis == 'composite' and tier_key:
        counts = dict(rollup['tiers'][tier_key])
        out = {**counts, 'enrolled': enrolled(counts), 'source': BORROWED if entry['proxy'] else CENSUS}
        if line in fields.PLAN_FIELDS:
            out['by_plan'] = rollup['by_plan'][line]
        return out
    if line in fields.VOLUME_FIELDS:
        volume = rollup['volumes'].get(fields.VOLUME_FIELDS[line])
        return {'volume': volume, 'field': fields.VOLUME_FIELDS[line], 'source': CENSUS} if volume else None
    if basis == 'stop_loss':
        medical = enrolled(rollup['tiers']['medical_tier'])
        return {'lives': medical or rollup['employees'], 'source': CENSUS}
    return {'lives': rollup['employees'], 'source': CENSUS}


def fte(people, threshold=None):
    """Employees whose hours per week reach the threshold (default 30); blank hours never count. None with no
    employees: a blank a person can fill beats a confident zero (C45)."""
    employees = [person['values'] for person in people if person['kind'] == fields.EMPLOYEE]
    if not employees:
        return None
    line = Decimal(str(threshold or DEFAULT_FULL_TIME_HOURS))
    hours = [_number(values.get('hours_per_week')) for values in employees if values.get('hours_per_week')]
    return sum(1 for value in hours if value is not None and value >= line)


def age_at(dob, as_of):
    """Whole years from a stored birth date to `as_of`, or None outside 0–120 or with either date missing."""
    years = age_on(parse_date(dob), as_of)
    return years if years is not None and 0 <= years <= 120 else None


def aged_65(people, as_of):
    """People aged 65 or more at `as_of` (the deal's effective date), dependents on their own birth date (C46). Only
    the count leaves the server. None without a date."""
    if as_of is None:
        return None
    ages = (age_at(person['values'].get('dob'), as_of) for person in people)
    return sum(1 for age in ages if age is not None and age >= MEDICARE_AGE)
