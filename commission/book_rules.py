"""The booked records' rules (plan.md §5.6; H26–H37, H120; H.6 `rules.py`). Pure: plain data in, plain data out.

- `earlier_years(dates, effective)`: the distinct years before `effective` among the client's other records that are
  not void, which `rules.year_number` counts (H30).
- `holes(facts, deal_id)`: what booking could not fill, listed, never guessed (H37).
- `stale_keys(facts, sources, today)`: the `sale` keys today's sale would book differently (H120).
- `match(records, targets)`: which record each target books into: (line, carrier) first, then shared plans on the line,
  so a carrier renamed on the plan updates the record instead of orphaning it (H28).
- `plan_label(names)`: the record's plan words.
- `facts(record)` / `split_facts(merged)`: a record's facts as one dict (the values and the four columns) and back, so
  `deals.values.apply` writes the columns with their `sources` entries too.
"""

from datetime import date

from deals import comp as comps

from . import vocab

COLUMNS = ('carrier', 'effective_date', 'term_end', 'status')
VALUES = ('premium_annual', 'rate', 'employees', 'plan_label', 'plan_ids', 'policy_number')
SALE_KEYS = ('carrier', 'effective_date', 'premium_annual', 'rate', 'employees', 'plan_label', 'plan_ids')
TYPED = 'typed'


def earlier_years(dates, effective):
    """How many distinct effective years before `effective` the client's other non-void records hold."""
    if effective is None:
        return 0
    return len({day.year for day in dates if day is not None and day < effective and day.year < effective.year})


def _iso(day):
    return day.isoformat() if isinstance(day, date) else day


def facts(record):
    """{key: value} over the record's values and its four columns (dates as ISO text)."""
    out = {key: record.values[key] for key in VALUES if key in record.values}
    for key in COLUMNS:
        value = _iso(getattr(record, key))
        if value not in (None, ''):
            out[key] = value
    return out


def split_facts(record, merged):
    """Write a merged facts dict back onto the record's values and columns."""
    record.values = {key: merged[key] for key in VALUES if key in merged}
    record.carrier = merged.get('carrier', '')
    for key in ('effective_date', 'term_end'):
        setattr(record, key, date.fromisoformat(merged[key]) if merged.get(key) else None)
    record.status = merged.get('status') or vocab.BOOKED


def origin(sources, key):
    return (sources.get(key) or {}).get('origin')


def typed(sources, key):
    return origin(sources, key) == TYPED


def holes(merged, sources, year_number, deal_id):
    """The holes of a record, in the Book's order (H37): premium, rate (none or the agency default), employees for a
    PEPM rate, year unknown, no effective date, no sold plan (a deal's record whose rate is not the in-force one)."""
    out = []
    if merged.get('premium_annual') in (None, ''):
        out.append('premium')
    rate = merged.get('rate')
    if not rate or origin(sources, 'rate') == 'agency':
        out.append('rate')
    if (rate or {}).get('type') == comps.PEPM and merged.get('employees') in (None, ''):
        out.append('employees')
    if year_number is None:
        out.append('year')
    if not merged.get('effective_date'):
        out.append('effective')
    if deal_id and not merged.get('plan_ids') and origin(sources, 'rate') != 'in_force':
        out.append('plan')
    return out


def stale_keys(merged, sources, today):
    """The `sale` keys whose value today differs from the booked one; typed keys are the person's and never stale."""
    out = []
    for key in SALE_KEYS:
        if typed(sources, key) or key not in today:
            continue
        if (merged.get(key) or None) != (today.get(key) or None):
            out.append(key)
    return out


def plan_label(names):
    """One plan's words, or "n plans: a · b" for several (one record per carrier on a line, OQ75)."""
    names = [name for name in names if name]
    if len(names) <= 1:
        return names[0] if names else ''
    return f'{len(names)} plans: ' + ' · '.join(names)


def match(records, targets):
    """[(target, record | None)] and the records left over: (line, carrier) first, then shared plans on the line."""
    free = list(records)
    pairs = []
    for wanted in targets:
        found = next((r for r in free if (r.line, r.carrier) == (wanted.line, wanted.carrier)), None)
        if found is None:
            ids = set(wanted.facts.get('plan_ids') or [])
            found = next((r for r in free if r.line == wanted.line and ids & set(r.values.get('plan_ids') or [])), None)
        if found is not None:
            free.remove(found)
        pairs.append((wanted, found))
    return pairs, free
