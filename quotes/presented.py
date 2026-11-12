"""Which plans a line presents on the proposal, and how many more fit (plan.md §5.4; F50, F119, J1–J3; OQ11).

★ means "on the proposal" (D-210). `presented(line)` is the one membership rule: the line's current plans, its
recommended plans and its starred plans, or every plan when none is starred. So once a line has stars its renewal
prints only with its own star or a recommendation, as in the old app (OQ11 default). A line the coverage intent keeps
off the proposal presents nothing (J2; intake's intent arrives in slice 11, so `off` is the caller's).

`room(line)` is how many more columns stars and recommendations can add: 16 a line, counting every column the line
presents once it has stars (current, recommended and starred plans). A pair printed as one column counts once
(`pairs.found`; D-219, slice 33), so `added` is the columns a write would add, not the plans. With no stars a line
presents every plan and may pass 16; the PDF and PowerPoint then refuse (J3). Pure, over `shapes.LineData`.
"""

from . import pairs

MAX_COLUMNS = 16


def has_stars(line):
    return any(plan.starred for plan in line.plans)


def held(line):
    """The plans a starred line presents: current, recommended and starred, in the line's order."""
    return [plan for plan in line.plans if plan.role == 'current' or plan.recommended or plan.starred]


def presented(line, off=False):
    """The plans on the proposal, in the line's order."""
    if off:
        return []
    return held(line) if has_stars(line) else list(line.plans)


def is_held(plan):
    return plan.role == 'current' or plan.recommended or plan.starred


def columns(line):
    """The columns a starred line holds: its held plans, a pair printed as one counted once."""
    return pairs.columns(line, [plan.id for plan in held(line)])


def room(line):
    return max(0, MAX_COLUMNS - columns(line))


def added(line, ids):
    """How many columns holding the plans `ids` as well would add (a half whose partner is held adds none)."""
    now = {plan.id for plan in held(line)}
    return pairs.columns(line, now | set(ids)) - pairs.columns(line, now)


def _held_words(line):
    plans = held(line)
    seconds = {second for _first, second in pairs.found(line, [plan.id for plan in plans])}
    plans = [plan for plan in plans if plan.id not in seconds]
    current = sum(1 for p in plans if p.role == 'current')
    recommended = sum(1 for p in plans if p.role != 'current' and p.recommended)
    starred = len(plans) - current - recommended
    parts = [
        f'{current} current' if current else '',
        f'{recommended} recommended' if recommended else '',
        f'{starred} starred' if starred else '',
    ]
    return ', '.join(part for part in parts if part)


def refusal(line, label, adding, then='unstar one first'):
    """The sentence refusing `adding` more columns on a full line, else None. `label` names the line ("Medical")."""
    left = room(line)
    if adding <= left:
        return None
    holds = f'The {label} proposal holds {MAX_COLUMNS} plans ({_held_words(line)})'
    if adding == 1:
        return f'{holds} — {then}.'
    fits = f'only {left} more fit' if left else 'none fit'
    return f'{holds}: {adding} ticked, {fits}. Unstar some or tick fewer.'
