"""The summary's cost blocks for one line: what you pay today, the lowest quote, our recommendation, the range of
quotes and the annual impact (J64; old Vantage 891f1b3 `exec_summary._b_current_cost`, `_b_best_option`,
`_b_recommended`, `_b_spread`, `_b_annual_delta`). Pure; each takes (facts, line) and answers the block's body or
raises `Refused` with the reason.

Monthly figures stay billed; annual ones go net of a first-year credit, and every netted sub-line names it (D-040).
"""

from quotes import math as m

from . import reading as r
from . import words as w


def _line(facts, key):
    return next(line for line in facts['lines'] if line['key'] == key)


def _unpriced(line, otherwise):
    raise r.Refused(r.NO_ENROLLMENT if line['no_people'] else otherwise)


def current_cost(facts, key):
    line = _line(facts, key)
    if r.several(line):
        package = line['current_package']
        if not package or package['monthly'] is None:
            raise r.Refused(r.SEVERAL_CURRENT)
        count = len(line['currents'])
        return {
            'value': package['monthly'],
            'value_label': w.per_month(package['monthly']),
            'sub': f'{count} current plans · {w.per_year(package["annual"])}',
        }
    base = r.current(line)
    if not base:
        if line['state'] == 'gap':
            raise r.Refused('Not in force today — this line is a proposed addition')
        raise r.Refused('No current plan is set on this line')
    if base['monthly'] is None:
        _unpriced(line, 'The current plan has no complete rates')
    return {
        'value': base['monthly'],
        'value_label': w.per_month(base['monthly']),
        'sub': f'{base["words"]} · {w.per_year(base["annual"])}',
    }


def _change_body(change):
    return {
        'delta': change['delta'] if change else None,
        'delta_label': w.monthly_delta(change),
        'delta_dir': w.direction(change['delta']) if change else '',
    }


def best_option(facts, key):
    line = _line(facts, key)
    found = r.priced(line['options'])
    if not found:
        if line['options']:
            _unpriced(line, 'No quoted plan has complete rates')
        raise r.Refused('No quoted plan has complete rates')
    plan = r.cheapest(found)
    credit = r.credit_of(plan)
    sub = plan['words'] + (f' · {w.money(credit)} first-year credit' if credit else '')
    return {
        'value': plan['monthly'],
        'value_label': w.per_month(plan['monthly']),
        'sub': sub,
        **_change_body(r.monthly_change(line, plan)),
    }


def _several_sum(line):
    """(pairs, their sums) on a line with several current plans, else (None, None); Refused with the reason the pairs
    cannot be added."""
    if not r.several(line):
        return None, None
    found = r.pairs(line)
    summed = r.pairs_sum(found)
    if summed is None:
        _unpriced(line, 'A recommended plan on this line has no complete rates')
    return found, summed


def recommended(facts, key):
    line = _line(facts, key)
    found, summed = _several_sum(line)
    if summed:
        change = m.monthly_change(summed['now'], [summed['was']])
        return {
            'value': summed['now'],
            'value_label': w.per_month(summed['now']),
            'sub': ' · '.join(plan['words'] for _base, plan in found),
            **_change_body(change),
        }
    plan = r.pick(line)
    if not plan:
        raise r.Refused(r.NO_PICK)
    if plan['monthly'] is None and line['no_people']:
        raise r.Refused(r.NO_ENROLLMENT)
    credit = r.credit_of(plan)
    sub = plan['words'] + (f' · after {w.money(credit)} first-year credit' if credit else '')
    return {
        'value': plan['monthly'],
        'value_label': w.per_month(plan['monthly']) if plan['monthly'] is not None else '—',
        'sub': sub,
        **_change_body(r.monthly_change(line, plan)),
    }


def spread(facts, key):
    line = _line(facts, key)
    found = r.priced(line['options'])
    if len(found) < 2:
        if len(line['options']) >= 2:
            _unpriced(line, 'Needs at least two priced quotes')
        raise r.Refused('Needs at least two priced quotes')
    low, high = r.cheapest(found), r.dearest(found)
    return {
        'value': None,
        'value_label': f'{w.money(low["monthly"])} – {w.per_month(high["monthly"])}',
        'sub': f'{low["words"]} … {high["words"]}',
    }


def _annual(change, sub):
    return {
        'value': change['delta'],
        'value_label': w.saved_or_more(change['delta']),
        'sub': sub,
        'delta': change['delta'],
        'delta_dir': w.direction(change['delta']),
    }


def annual_delta(facts, key):
    line = _line(facts, key)
    _found, summed = _several_sum(line)
    if summed:
        change = m.change(summed['now_annual'], summed['was_annual'])
        credit = summed['credit']
        tail = f', after {w.money(credit)} first-year credit' if credit else ''
        return _annual(change, f'over 12 months vs the current plans{tail}')
    plan = r.pick(line)
    if not plan:
        raise r.Refused(r.NO_PICK)
    base = r.baseline(line, plan)
    change = plan['change']
    if base and r.kept(plan, base) and plan['annual'] is not None:
        change = m.change(plan['annual'], base['annual'])  # keeping the plan: no change, as the old tile read
    if change is None or base is None:
        if r.several(line):
            raise r.Refused(r.SEVERAL_CURRENT)
        _unpriced(line, 'Needs a current plan and a recommendation with rates')
    credit = plan.get('credit')
    if credit:
        r.net_annual(plan)  # refuses when the credit is larger than the year
        net = credit['change']
        return _annual(
            net,
            f'over 12 months vs the current plan ({w.pct(net["pct"])}), after {w.money(credit["annual"])} '
            'first-year credit',
        )
    return _annual(change, f'over 12 months vs the current plan ({w.pct(change["pct"])})')
