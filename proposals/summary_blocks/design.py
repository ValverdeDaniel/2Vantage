"""The summary's plan-design blocks for one line: the employee-only rate, the deductible and out-of-pocket moves, the
level-funded split and the stop-loss maximum annual liability (J64; old Vantage 891f1b3 `exec_summary._b_ee_only`,
`_move`, `_b_lf_claims_pct`, `_b_stop_loss_mal`). Pure; (facts, line) → body, or `Refused` with the reason.

The level-funded breakout and the stop-loss verdict are quotes' math (slice 36): until a plan carries them
(`lf_split`, `stop_loss`), those two blocks refuse with the old reasons.
"""

from quotes import math as m

from . import reading as r
from . import words as w

# Which field carries "the deductible" and "the exposure ceiling" per field set: a dental plan's annual maximum is
# not a medical out-of-pocket max (the old SLIDER_FIELDS_BY_SET).
MOVE_FIELDS = {
    'medical': ('deductible_single', 'Deductible (single)', 'oop_max_single', 'Out-of-pocket max (single)'),
    'dental': ('den_deductible', 'Deductible', 'den_annual_max', 'Annual maximum'),
    'vision': ('vis_exam_copay', 'Exam copay', 'vis_frame_allowance', 'Frame allowance'),
    'stop_loss': ('sl_spec_deductible', 'Specific deductible', None, None),
}
TIER_SETS = ('medical', 'dental', 'vision')  # a composite line prices per tier; the rest have one unit rate


def _line(facts, key):
    return next(line for line in facts['lines'] if line['key'] == key)


def _picked(line):
    plan = r.pick(line)
    if not plan:
        raise r.Refused(r.NO_PICK)
    return plan


def _moved(new, old):
    change = m.change(new, old) if old is not None else None
    return change['delta'] if change else None


def _places(raw):
    """The decimals a rate was stored with, 2 to 4 (D-077): a $0.085 fee is not $0.09."""
    text = str(raw or '')
    found = len(text.split('.', 1)[1]) if '.' in text else 0
    return min(4, max(2, found))


def ee_only(facts, key):
    """The number a client budgets in (Stephanie: "I need an $850 rate…"), not the group total."""
    line = _line(facts, key)
    field = 'rate_ee' if line['field_set'] in TIER_SETS else 'unit_rate'
    plan = _picked(line)
    base = r.baseline(line, plan)
    raw_new = plan['values'].get(field)
    new = m.decimal(raw_new)
    if new is None:
        raise r.Refused('The recommended plan has no employee-only rate')
    raw_old = base['values'].get(field) if base else None
    old = m.decimal(raw_old)
    delta = _moved(new, old)
    places = _places(raw_new)
    was = _places(raw_old) if old is not None else places
    return {
        'value': m.plain(new),
        'value_label': f'{w.money(new, places)}/mo',
        'sub': f'was {w.money(old, was)}' if old is not None else 'employee-only rate',
        'delta': delta,
        'delta_label': w.money(delta, max(places, was)) if delta is not None else '',
        'delta_dir': w.direction(delta),
    }


def _move(facts, key, which):
    line = _line(facts, key)
    spec = MOVE_FIELDS.get(line['field_set'])
    field, label = None, None
    if spec:
        field, label = spec[:2] if which == 'deductible' else spec[2:]
    if not field:
        raise r.Refused('This line has no comparable design figure')
    plan = _picked(line)
    base = r.baseline(line, plan)
    new = m.decimal(plan['values'].get(field))
    if new is None:
        raise r.Refused(f'The recommended plan has no {label.lower()}')
    old = m.decimal(base['values'].get(field)) if base else None
    delta = _moved(new, old)
    return {
        'label': label,
        'value': m.plain(new),
        'value_label': w.money(new),
        'sub': f'was {w.money(old)}' if old is not None else label,
        'delta': delta,
        'delta_label': w.money(delta) if delta is not None else '',
        'delta_dir': w.direction(delta),
    }


def deductible_move(facts, key):
    return _move(facts, key, 'deductible')


def oop_move(facts, key):
    return _move(facts, key, 'oop')


def lf_claims_pct(facts, key):
    """How much of a level-funded premium can come back as surplus."""
    plan = r.pick(_line(facts, key))
    if not plan:
        raise r.Refused(r.NO_PICK)
    split = plan.get('lf_split')
    if not split:
        raise r.Refused('The recommended plan has no level-funded breakout')
    return {
        'value': split['pct_to_claims'],
        'value_label': f'{split["pct_to_claims"]}% to claims',
        'sub': f'{w.money(split["claim_funding"])} claim funding · {w.money(split["fixed_costs"])} fixed',
    }


def stop_loss_mal(facts, key):
    plan = r.pick(_line(facts, key))
    if not plan:
        raise r.Refused('No contract is recommended yet')
    verdict = plan.get('stop_loss') or {}
    if verdict.get('max_annual_liability') is None:
        raise r.Refused('The recommended contract is missing a term the verdict needs')
    against = verdict.get('vs_current')
    return {
        'value': verdict['max_annual_liability'],
        'value_label': w.money(verdict['max_annual_liability']),
        'sub': f'maximum annual liability · {plan["words"]}',
        'delta': against,
        'delta_label': w.money(against) if against is not None else '',
        'delta_dir': w.direction(against),
    }
