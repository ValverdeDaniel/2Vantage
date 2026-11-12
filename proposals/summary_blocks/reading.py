"""Reading one line of the summary's facts: its baseline, its one pick, its pairs (old Vantage 891f1b3
`exec_summary._line_sets`, `_recommended`, `_several_pairs`, `_pairs_sum`, `_cost_delta`). Pure.

A line's facts (`summary_read.line_facts`): {key, label, state, shopping, field_set, composite, no_people, people,
currents, options, quotes, picks, current_package}; a plan: {id, words, carrier, monthly, annual, change, bases,
credit, values}. Every sum and change is quotes' (`quotes.math`; rule 5). Refusal over guessing: a figure that cannot
be worked out honestly answers a reason, never a zero.
"""

from quotes import math as m

SEVERAL_CURRENT = 'This line has several current plans — this figure needs exactly one'
SEVERAL_PICKS = 'Several plans are recommended on this line — this figure needs one'
NO_PICK = 'No plan is recommended on this line yet'
NO_ENROLLMENT = 'No enrollment counted on this line'
CREDIT_EXCEEDS = "The first-year credit is larger than the plan's annual premium"
EXCEEDS = 'credit_exceeds_year'


class Refused(Exception):
    """A figure that cannot be worked out; its message is the reason the builder shows."""


def several(line):
    return len(line['currents']) >= 2


def current(line):
    """The line's one current plan, or None (none, or several)."""
    return line['currents'][0] if len(line['currents']) == 1 else None


def pick(line):
    """The line's one answer: a sold plan, else the recommended plan the client sees; a line kept as is keeps its
    current plan. None when nothing is picked; Refused when several are (one figure needs one plan)."""
    picks = line['picks']
    if len(picks) > 1:
        raise Refused(SEVERAL_PICKS)
    if picks:
        return picks[0]
    if line['state'] == 'presented':
        return current(line)
    return None


def baseline(line, plan):
    """The current plan a figure about `plan` reads against: the line's only one, else the one it is linked to."""
    found = current(line)
    if found or not plan or len(plan['bases']) != 1:
        return found
    return next((p for p in line['currents'] if p['id'] == plan['bases'][0]), None)


def monthly_change(line, plan):
    """{delta, pct} a month against what `plan` replaces, or None. Only where quotes compares the same people (its
    `change` is set), so a figure never measures two different groups against each other."""
    if not plan or plan['change'] is None:
        return None
    by_id = {p['id']: p for p in line['currents']}
    return m.monthly_change(plan['monthly'], [by_id[pid]['monthly'] for pid in plan['bases'] if pid in by_id])


def kept(plan, base):
    return plan['id'] == base['id']


CURRENT_UNPRICED = 'Each current plan on this line needs its own enrollment and rates for this figure'
TWO_FOR_ONE = 'Two plans are recommended for one current plan on this line — this figure needs one each'
UNANSWERED = 'A current plan on this line has no recommendation yet'


def pairs(line):
    """[(current plan, its answer)] on a line with several current plans: the keep-this-plan answer included, a
    current plan nothing links to staying as it is. Refused when the figures could not honestly add them: a current
    plan unpriced (its own enrollment unknown), two answers for one plan, or an answer missing."""
    if any(p['monthly'] is None for p in line['currents']):
        raise Refused(CURRENT_UNPRICED)
    out = []
    for base in line['currents']:
        answers = [p for p in line['picks'] if p['id'] == base['id'] or base['id'] in p['bases']]
        if len(answers) > 1:
            raise Refused(TWO_FOR_ONE)
        if answers:
            out.append((base, answers[0]))
        elif any(base['id'] in p['bases'] for p in line['options']):
            raise Refused(UNANSWERED)
        else:
            out.append((base, base))
    return out


def net_annual(plan):
    """The plan's year after its first-year credit (quotes' net), or its year; Refused when the credit is larger."""
    credit = plan.get('credit')
    if not credit:
        return plan['annual']
    if credit['reason'] == EXCEEDS:
        raise Refused(CREDIT_EXCEEDS)
    return credit['net_annual']


def credit_of(plan):
    credit = plan.get('credit')
    return (credit or {}).get('annual') or 0


def pairs_sum(found):
    """{was, now, was_annual, now_annual, credit} over a line's pairs (monthly billed, annual net of credits), or None
    when one is unpriced. Refused when a credit is larger than its plan's year."""
    if any(base['monthly'] is None or plan['monthly'] is None for base, plan in found):
        return None
    answers = [plan for base, plan in found]
    return {
        'was': m.add([base['monthly'] for base, _plan in found]),
        'now': m.add([plan['monthly'] for plan in answers]),
        'was_annual': m.add([base['annual'] for base, _plan in found]),
        'now_annual': m.add([net_annual(plan) for plan in answers]),
        'credit': m.add([credit_of(plan) for base, plan in found if not kept(plan, base)]),
    }


def priced(plans):
    return [p for p in plans if p['monthly'] is not None]


def cheapest(plans):
    return min(plans, key=lambda p: m.decimal(p['monthly']))


def dearest(plans):
    return max(plans, key=lambda p: m.decimal(p['monthly']))
