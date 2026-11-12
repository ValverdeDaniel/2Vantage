"""Which enrollment prices a plan (plan.md §5.5, O.6 #24; F86–F92, F98). Pure, over `shapes.LineData`.

The shape follows the line's rate basis (`deals.lines.ENROLLMENT_KEYS`): tier counts `{EE, ES, EC, FAM}` for composite
lines, `{volume}` for volume_1000, weekly_10 and payroll_100, `{lives}` for pepm and stop_loss. Figures are Decimals.

`enrollment_for(plan, line)` takes the first step that gives figures:
1. the plan's own typed counts (`typed`);
2. a priced version: its original's enrollment, so "5% off" prices the same people (`from original plan`; F87);
3. a renewal: its current plan's typed counts (`from current plan`); an alternate with a comparison base: the sum of
   its base plans' typed counts (`from replaced plan`);
4. the census by plan, on medical, dental and vision, once every enrolled plan text is matched (`census`; F90);
5. two or more current plans: stop (`per_plan_counts_needed`; the Advisor asks for the split or the link, OQ20);
6. the figure typed for the whole line (`line`; F88);
7. the census for the line (`census`); a worksite tier-rated line's are medical's (`proxy`); stop-loss lives are the
   medical enrolled employees (`medical`; F98);
8. a worksite tier-rated line borrows medical's people (`proxy`; OQ19); dental and vision never borrow;
9. nothing (`no_enrollment`).
Typed counts sit under the line's one switch (`People.on`). Counts typed before the latest census import give way to
the census wherever it can price the plan (steps 4 and 7; F91, OQ18).
"""

from decimal import Decimal

from deals import lines

from . import by_plan
from .rounding import decimal, plain

TIERS = lines.TIER_CODES
ORIGINAL = 'from original plan'
CENSUS = 'census'
PROXY = 'proxy'
MEDICAL = 'medical'
LINE = 'line'
# Every source in words, on every screen that shows a premium (F86, J83); `mark` is the board's marker beside a
# total ('' = none: the census is the default a person expects).
SOURCES = {
    'typed': {'label': 'Typed for this plan', 'mark': '✎ counts'},
    ORIGINAL: {'label': 'The people of the plan this version prices', 'mark': '✎ counts'},
    'from current plan': {'label': 'Typed for the current plan it renews', 'mark': '✎ counts'},
    'from replaced plan': {'label': 'Typed for the plan it replaces', 'mark': '✎ counts'},
    LINE: {'label': 'Typed for the whole line', 'mark': '✎ counts'},
    CENSUS: {'label': 'From the census', 'mark': ''},
    PROXY: {'label': 'Borrowed from medical', 'mark': 'borrowed'},
    MEDICAL: {'label': 'From medical enrollment', 'mark': 'from medical'},
}


def enrollment_keys(basis):
    return list(lines.ENROLLMENT_KEYS[basis])


def figures_of(raw, keys):
    """Stored figures as Decimals when any is above zero, else None."""
    figures = {key: decimal((raw or {}).get(key)) or Decimal(0) for key in keys}
    return figures if any(figures.values()) else None


def typed(plan, keys):
    """The plan's own typed figures when any is above zero, else None (the line's switch is checked by the caller)."""
    return figures_of(plan.enrollment, keys)


def total(enrollments, keys):
    """Several plans' figures summed key by key (a consolidation carries the people of every plan it replaces)."""
    return {key: sum((e[key] for e in enrollments), Decimal(0)) for key in keys}


def _census_line(line, keys):
    """Step 7: the census for the line, (figures, source) or None."""
    found = line.people.census
    if line.rate_basis == 'stop_loss':
        medical = line.people.medical
        if medical:
            return {'lives': sum(medical[0].values(), Decimal(0))}, MEDICAL
    if not found:
        return None
    figures = figures_of(found, keys)
    if figures is None:
        return None
    return figures, PROXY if found.get('source') == 'borrowed' else CENSUS


def census_for(plan, line):
    """What the census alone gives the plan (steps 4 and 7), (figures, source) or None."""
    keys = enrollment_keys(line.rate_basis)
    found = by_plan.figures(plan, line)
    if found is not None:
        return found, CENSUS
    if len(line.current) >= 2:
        return None
    return _census_line(line, keys)


def _typed_steps(plan, line, keys):
    """Steps 1, 3 and 6 without the census: (figures, source) or None."""
    if not line.people.on:
        return None
    own = typed(plan, keys)
    if own:
        return own, 'typed'
    bases = [line.by_id[pid] for pid in line.base_ids(plan)]
    if plan.role in ('renewal', 'alternate') and bases:
        figures = [typed(base, keys) for base in bases]
        if all(figures):
            return total(figures, keys), 'from current plan' if plan.role == 'renewal' else 'from replaced plan'
    return None


def enrollment_for(plan, line):
    """(figures, source) or (None, reason)."""
    keys = enrollment_keys(line.rate_basis)
    original = line.by_id.get(plan.version_of)
    if original is not None and original.id != plan.id and not (line.people.on and typed(plan, keys)):
        figures, how = enrollment_for(original, line)
        return (figures, ORIGINAL) if figures is not None else (None, how)
    stale = line.people.stale
    found = _typed_steps(plan, line, keys)
    if found:
        census = census_for(plan, line) if stale else None
        return census or found
    census = by_plan.figures(plan, line)
    if census is not None:
        return census, CENSUS
    if len(line.current) >= 2:
        return None, 'per_plan_counts_needed'
    figure = figures_of(line.people.figure, keys) if line.people.on else None
    rollup = _census_line(line, keys)
    if figure and not (stale and rollup):
        return figure, LINE
    if rollup:
        return rollup
    if lines.BY_KEY.get(line.key, {}).get('proxy') and line.people.medical:
        return dict(line.people.medical[0]), PROXY
    return None, 'no_enrollment'


def gave_way(plan, line):
    """True when typed counts would price the plan but the census does, because they were typed before the latest
    import (F91): the counts card's "Priced from the census now · Keep my typed counts"."""
    if not line.people.stale:
        return False
    keys = enrollment_keys(line.rate_basis)
    root = line.root(plan)
    typed_figures = _typed_steps(root, line, keys)
    if typed_figures is None and line.people.on and len(line.current) < 2:
        typed_figures = figures_of(line.people.figure, keys)
    return bool(typed_figures) and census_for(root, line) is not None


def people(line, results):
    """The line's enrolled people as one figure, (figures, source) or None: its current plans' enrollment summed when
    every one has some (from any source), else the line figure (unless it gave way to the census), else the census
    for the line. Medical's is what worksite lines borrow, stop-loss counts and the headcount reads (§5.7)."""
    keys = enrollment_keys(line.rate_basis)
    used = [results[plan.id]['enrollment_used'] for plan in line.current]
    if used and all(used):
        sources = {results[plan.id]['enrollment_source'] for plan in line.current}
        return total([{k: decimal(u[k]) for k in keys} for u in used], keys), sources.pop() if len(sources) == 1 else ''
    rollup = _census_line(line, keys)
    figure = figures_of(line.people.figure, keys) if line.people.on else None
    if figure and not (line.people.stale and rollup):
        return figure, LINE
    return rollup


def same_people(a, b):
    """Whether two enrollments count the same people, key by key (§5.5's "apples to apples")."""
    if a is None or b is None:
        return False
    return all(decimal(a[key]) == decimal(b.get(key, 0)) for key in a)


def as_plain(figures):
    """Figures as the API's numbers."""
    return None if figures is None else {key: plain(value) for key, value in figures.items()}


def meta():
    """/api/meta/ `enrollment`: the sources in words, each basis's keys and their labels (F86, F92)."""
    return {
        'sources': [{'key': key, **words} for key, words in SOURCES.items()],
        'keys': {basis: list(keys) for basis, keys in lines.ENROLLMENT_KEYS.items()},
        'labels': {**dict(lines.TIERS), 'volume': 'Volume ($)', 'lives': 'Lives'},
    }
