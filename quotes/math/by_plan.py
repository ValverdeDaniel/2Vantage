"""The census by plan name (plan.md §5.5 step 4, §5.3.6; F90, C41). Pure, over `shapes.LineData`.

The census counts tiers per distinct plan text on medical, dental and vision (`census.rollup`), and census does not
know the deal's plans, so quotes matches the texts to the line's current plans: by hand first (`Plan.census_names`,
confirmed in the Advisor's counts card), else automatically when a text is exactly one current plan's name, carrier
and name, or plan number (case and spacing aside). Only texts some enrolled employee names count: waivers and blank
tiers never price a plan. The census prices a plan by plan only once every such text is matched; then a current plan
counts its own texts, and a renewal or alternate counts its comparison base's.
"""

from decimal import Decimal

from deals import lines

TIERS = lines.TIER_CODES
HAND, NAME, NUMBER = 'hand', 'name', 'number'


def norm(text):
    return ' '.join(str(text or '').split()).casefold()


def enrolled(counts):
    return sum(counts.get(tier, 0) for tier in TIERS)


def _auto(text, current):
    """(plan id, how) when exactly one current plan's name, carrier and name, or plan number is the text."""
    wanted = norm(text)
    by_name = [p.id for p in current if wanted in (norm(p.name), norm(f'{p.carrier} {p.name}'))]
    if len(by_name) == 1:
        return by_name[0], NAME
    by_number = [p.id for p in current if p.plan_number and norm(p.plan_number) == wanted]
    if len(by_number) == 1 and not by_name:
        return by_number[0], NUMBER
    return None, None


def matched(line):
    """[{text, counts, enrolled, plan_id, how}] for the line's census plan texts that name enrolled employees, in the
    census's order, or None when the census has no plan column for the line. Worked out once per line."""
    if hasattr(line, '_by_plan'):
        return line._by_plan
    census = line.people.census
    found = census.get('by_plan') if census and line.rate_basis == 'composite' else None
    rows = None
    if found is not None:
        hand = {}
        for plan in line.current:
            for text in plan.census_names:
                hand.setdefault(norm(text), plan.id)
        rows = []
        for text, counts in found.items():
            people = enrolled(counts)
            if not people:
                continue
            plan_id, how = (hand[norm(text)], HAND) if norm(text) in hand else _auto(text, line.current)
            row = {'text': text, 'counts': {t: counts.get(t, 0) for t in TIERS}, 'enrolled': people}
            rows.append({**row, 'plan_id': plan_id, 'how': how})
    line._by_plan = rows
    return rows


def complete(line):
    """Whether every enrolled plan text is matched to a current plan (step 4 applies)."""
    rows = matched(line)
    return bool(rows) and bool(line.current) and all(row['plan_id'] is not None for row in rows)


def figures(plan, line):
    """The census counts of the texts matched to the plan (a current plan) or to its comparison base, or None."""
    if not complete(line):
        return None
    ids = {plan.id} if plan.role == 'current' else set(line.base_ids(plan))
    if not ids:
        return None
    picked = [row['counts'] for row in matched(line) if row['plan_id'] in ids]
    out = {tier: Decimal(sum(counts[tier] for counts in picked)) for tier in TIERS}
    return out if any(out.values()) else None
