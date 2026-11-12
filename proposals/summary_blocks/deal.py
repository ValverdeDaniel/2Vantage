"""The summary's whole-deal blocks: total cost today, total as recommended, the annual impact of every line, what we
marketed, the first-year cost and the proposed additions (J64; old Vantage 891f1b3 `exec_summary._deal_totals`,
`_current_total`, `_b_total_*`, `_b_lines_shopped`, `_b_first_year_cost`, `_b_lines_proposed`). Pure; (facts, None)
→ body, or `Refused` with the reason.

"Refuses to half-add": a line with neither a current plan nor a pick is simply not part of a total, but a line with
one and not the other, or a missing price, makes a sum that looks complete and is not, so the total refuses.
"""

from quotes import math as m

from . import reading as r
from . import words as w

DEAL_SEVERAL_CURRENT = 'A line on this deal has several current plans — the total needs exactly one per line'
DEAL_SEVERAL_PICKS = 'A line on this deal has several recommended plans — the total needs one per line'
DEAL_NO_ENROLLMENT = 'A line on this deal has no enrollment counted'
DEAL_CREDIT_EXCEEDS = "A first-year credit on this deal is larger than its plan's annual premium"
DEAL_UNPRICED = 'Not every line has a priced recommendation'
DEAL_TWO_FOR_ONE = 'A line on this deal has two plans recommended for one current plan — the total needs one each'
DEAL_REASONS = {r.CURRENT_UNPRICED: DEAL_SEVERAL_CURRENT, r.TWO_FOR_ONE: DEAL_TWO_FOR_ONE}


def _unpriced(line):
    return r.Refused(DEAL_NO_ENROLLMENT if line['no_people'] else DEAL_UNPRICED)


def _pick(line):
    try:
        return r.pick(line)
    except r.Refused as exc:
        raise r.Refused(DEAL_SEVERAL_PICKS) from exc


def _credit(plan):
    try:
        r.net_annual(plan)
    except r.Refused as exc:
        raise r.Refused(DEAL_CREDIT_EXCEEDS) from exc
    return r.credit_of(plan)


def _line_pair(line):
    """[(today's plan, the answer)] for one line, [] when the line is not part of the totals."""
    if r.several(line):
        try:
            return r.pairs(line)
        except r.Refused as exc:
            raise r.Refused(DEAL_REASONS.get(str(exc), DEAL_UNPRICED)) from exc
    base, plan = r.current(line), _pick(line)
    if line['state'] == 'presented':
        return [(base, base)] if base else []  # kept as is: today IS the recommendation
    if not base and not plan:
        return []
    if not base or not plan:
        raise r.Refused(DEAL_UNPRICED)
    return [(base, plan)]


def totals(facts):
    """{was, now, was_annual, now_annual, credit} across every line (monthly billed, annual net of credits)."""
    found = []
    for line in facts['lines']:
        pairs = _line_pair(line)
        if any(base['monthly'] is None or plan['monthly'] is None for base, plan in pairs):
            raise _unpriced(line)
        found += pairs
    if not found:
        raise r.Refused(DEAL_UNPRICED)
    answers = [plan for _base, plan in found]
    credits = [_credit(plan) for base, plan in found if not r.kept(plan, base)]
    return {
        'was': m.add([base['monthly'] for base, _plan in found]),
        'now': m.add([plan['monthly'] for plan in answers]),
        'was_annual': m.add([base['annual'] for base, _plan in found]),
        'now_annual': m.add([r.net_annual(plan) for plan in answers]),
        'credit': m.add(credits) if credits else 0,
    }


def total_current(facts, _key=None):
    """What the client pays today across every line that has a current plan: needs no recommendation."""
    monthly, annual = [], []
    for line in facts['lines']:
        if r.several(line):
            package = line['current_package']
            if not package or package['monthly'] is None:
                raise r.Refused(DEAL_SEVERAL_CURRENT)
            monthly.append(package['monthly'])
            annual.append(package['annual'])
            continue
        base = r.current(line)
        if not base:
            continue
        if base['monthly'] is None:
            raise r.Refused(
                DEAL_NO_ENROLLMENT if line['no_people'] else 'No current plan on this deal has complete rates'
            )
        monthly.append(base['monthly'])
        annual.append(base['annual'])
    if not monthly:
        raise r.Refused('No current plan on this deal has complete rates')
    was = m.add(monthly)
    return {
        'value': was,
        'value_label': w.per_month(was),
        'sub': f'{w.per_year(m.add(annual))} across every line in force',
    }


def total_recommended(facts, _key=None):
    found = totals(facts)
    change = m.monthly_change(found['now'], [found['was']])
    tail = f', after {w.money(found["credit"])} in first-year credits' if found['credit'] else ''
    return {
        'value': found['now'],
        'value_label': w.per_month(found['now']),
        'sub': f'{w.per_year(found["now_annual"])} across every line{tail}',
        'delta': change['delta'] if change else None,
        'delta_label': w.monthly_delta(change),
        'delta_dir': w.direction(change['delta']) if change else '',
    }


def total_annual_delta(facts, _key=None):
    found = totals(facts)
    change = m.change(found['now_annual'], found['was_annual'])
    tail = f', after {w.money(found["credit"])} in first-year credits' if found['credit'] else ''
    return {
        'value': change['delta'],
        'value_label': w.saved_or_more(change['delta']),
        'sub': f'over 12 months, every line together{tail}',
        'delta': change['delta'],
        'delta_dir': w.direction(change['delta']),
    }


def lines_shopped(facts, _key=None):
    """What actually went to market, by the intent's state: a line kept as is was never marketed."""
    found = facts['lines']
    if not found:
        raise r.Refused('No lines on this deal')
    shopped = [line for line in found if line['shopping']]
    kept = [line for line in found if line['state'] == 'presented']
    gaps = [line for line in found if line['state'] == 'gap']
    if facts['markets']['has_asks']:
        names = {
            row['id']
            for entry in facts['markets']['lines']
            for row in entry['rows']
            if not row['current'] and not row['hidden']
        }
    else:
        names = {plan['carrier'] for line in found for plan in line['quotes'] if plan['carrier']}
    parts = [f'{len(names)} {w.plural(len(names), "carrier")} approached' if names else 'no quotes in yet']
    if kept:
        parts.append(f'{len(kept)} presented as in force')
    if gaps:
        parts.append(f'{len(gaps)} proposed {w.plural(len(gaps), "addition")}')
    count = len(shopped)
    return {'value': count, 'value_label': f'{count} {w.plural(count, "line")} marketed', 'sub': ' · '.join(parts)}


def first_year_cost(facts, _key=None):
    """What the client would pay as proposed: needs no current plan, so a brand-new group gets a number."""
    monthly, annual, credits = [], [], []
    for line in facts['lines']:
        plan = _pick(line) if line['state'] != 'presented' else None
        if not plan:
            continue
        if plan['monthly'] is None:
            raise r.Refused(DEAL_NO_ENROLLMENT if line['no_people'] else 'A recommended plan is missing rates')
        credits.append(_credit(plan))
        monthly.append(plan['monthly'])
        annual.append(r.net_annual(plan))
    if not monthly:
        raise r.Refused('No line has a priced recommendation yet')
    now, credit = m.add(monthly), m.add(credits)
    tail = f', after {w.money(credit)} in credits' if credit else ''
    return {'value': now, 'value_label': w.per_month(now), 'sub': f'{w.per_year(m.add(annual))} as proposed{tail}'}


def lines_proposed(facts, _key=None):
    """The coverage being added: on new business every line; otherwise the lines not in force today."""
    if facts['new_business']:
        chosen, note = facts['lines'], 'new group — every line is proposed coverage'
    else:
        chosen, note = [line for line in facts['lines'] if line['state'] == 'gap'], 'not in force today'
    if not chosen:
        raise r.Refused('No proposed additions on this deal')
    count = len(chosen)
    return {
        'value': count,
        'value_label': f'{count} {w.plural(count, "line")} proposed',
        'sub': f'{", ".join(line["label"] for line in chosen)} — {note}',
    }
