"""Option numbers: "Option n" per line, the name a client keeps for a plan from one round to the next (plan.md §5.4;
J159, OQ35, OQ36; ported from old Vantage 891f1b3 `pipeline/option_numbers.py`, D-175). Pure.

"The one with the $1,000 deductible" fails when three plans match, so each option gets a number that survives: the
order on screen cannot be it (the arrows move plans and a star changes what shows), so a number is stored once on
`Plan.option_number` and never changes. Issue stamps it (`services.numbers.stamp_option_numbers`), in the order the
client first reads the plans (`proposals.pages.reading_order`), so a first round reads 1, 2, 3; every screen and draft
before that shows the numbers Issue would stamp, worked out here the same way.

A number is never reused while its plan exists: the next one is past the highest stored on the line, starred or not,
removed plans included (Restore brings them back with theirs). Current plans and priced versions take none: a priced
version is its plan at another price and reads its own label. Renewals are numbered (OQ36).
"""


def takes_number(plan):
    """Whether a plan (`shapes.PlanData`) is numbered: not a current plan, not a priced version."""
    return plan.role != 'current' and plan.version_of is None


def numbers(plans, stored, top=0):
    """{plan id: n} for `plans` (PlanData, in reading order) that take a number: a stored number stays; each other one
    takes the next past the highest stored on the line. `stored` is {plan id: number} of the line's numbered plans;
    `top` the line's highest stored number when `stored` does not hold every plan that has one (removed plans)."""
    out = {}
    following = max([top or 0, *(n for n in stored.values() if n)], default=0)
    for plan in plans:
        if not takes_number(plan):
            continue
        if stored.get(plan.id):
            out[plan.id] = stored[plan.id]
        else:
            following += 1
            out[plan.id] = following
    return out
