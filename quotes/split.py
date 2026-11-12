"""One plan under two plan numbers (plan.md §5.4; D116, D-219, O.6 #4, OQ42; slice 22). Pure: plans and dicts in.

A carrier may file one plan as two plan numbers: Florida Blue's HSA 05182 holds the employee-only deductible,
out-of-pocket maximum and rate, 05183 the dependent tiers. **The halves stay two plans** (D-219: each value still
traces to its own file; slice 33 prints a pair as one column and slice 37 lets Claude pair them): a read never
combines them, and Claude's `merge_plans` refuses to.
- `halves(a, b)`: whether two plans are the halves of one: one line, one side, one carrier, and either plan numbers
  that differ only in a last digit one apart (05182 / 05183), or one priced for employees only and the other for the
  dependent tiers only (the old proposal check `split_plan`).
- `pairs(plans)`: the pairs among a read's plans, in reading order, each plan in one pair at most.
- **"A / B" plans take both halves** (D116): a deal's one plan entered under both numbers ("05182 / 05183") takes
  both halves of a read. `prepare(found, deal_plans)` folds such a pair into one found plan (`fold`): each tier's rate
  from the half that prints it, every other value where the halves agree or only one prints it; where they disagree
  the employee-only half's stays and a finding says so. Fresh halves (no such plan on the deal) stay two, with a
  finding that they are halves of one plan.
"""

import re

from ai import codes

from . import pairs as printed
from .fields import BY_KEY, TIER_RATE_KEYS
from .reader.match import match
from .reader.merge import norm

DEPENDENT = ('rate_es', 'rate_ec', 'rate_fam')
FRESH = (
    '{a} and {b} look like one plan filed under two numbers (one prices employees only, the other the dependent '
    'tiers): they stay two plans, each with its own values; pair them to print as one column.'
)
DISAGREE = '{plan}: its two halves print {label} as {first} and {second}; the employee-only half’s {first} is kept.'


def _number(value):
    parts = codes.number_parts(value)
    return next(iter(parts)) if len(parts) == 1 else ''


def _siblings(first, second):
    """05182 and 05183: one length, equal but for the last digit, one apart."""
    a, b = _number(first), _number(second)
    if not a or not b or len(a) != len(b) or a[:-1] != b[:-1] or not (a[-1] + b[-1]).isdigit():
        return False
    return abs(int(a[-1]) - int(b[-1])) == 1


def _priced(values, key):
    value = str((values or {}).get(key) or '').strip()
    return bool(value) and re.sub(r'[0.]', '', value) != ''


def _tiers(first, second):
    """One prices only employees, the other only the dependent tiers."""

    def employee_only(values):
        return _priced(values, 'rate_ee') and not any(_priced(values, key) for key in DEPENDENT)

    def dependents_only(values):
        return not _priced(values, 'rate_ee') and any(_priced(values, key) for key in DEPENDENT)

    a, b = first.get('values') or {}, second.get('values') or {}
    return (employee_only(a) and dependents_only(b)) or (employee_only(b) and dependents_only(a))


def halves(first, second):
    """`first`, `second`: {line, side, carrier, plan_number, values: {key: value}} (a read's plan, or `shape(plan)`)."""
    if first.get('line') != second.get('line') or first.get('side') != second.get('side'):
        return False
    if norm(first.get('carrier')) != norm(second.get('carrier')):
        return False
    return _siblings(first.get('plan_number'), second.get('plan_number')) or _tiers(first, second)


def shape(plan):
    """A Plan as `halves` reads it."""
    return {
        'line': plan.line,
        'side': plan.role,
        'carrier': plan.carrier,
        'plan_number': plan.plan_number,
        'values': dict(plan.values or {}),
    }


def _flat(found):
    return {**found, 'values': {key: entry['value'] for key, entry in found['values'].items()}}


def pairs(found):
    """[(first, second)] among a read's plans (merge.py's dicts), in reading order."""
    out, taken = [], set()
    for index, first in enumerate(found):
        if first['key'] in taken:
            continue
        for second in found[index + 1 :]:
            if second['key'] not in taken and halves(_flat(first), _flat(second)):
                out.append((first, second))
                taken |= {first['key'], second['key']}
                break
    return out


def _employee_half(first, second):
    """(the half that prices employees, the other); in reading order when neither or both do."""
    if _priced(_flat(second)['values'], 'rate_ee') and not _priced(_flat(first)['values'], 'rate_ee'):
        return second, first
    return first, second


def fold(first, second):
    """(one found plan, [finding texts]): both halves as the deal's one "A / B" plan."""
    lead, other = _employee_half(first, second)
    values, said = dict(lead['values']), []
    for key, entry in other['values'].items():
        held = values.get(key)
        if held is None or (key in TIER_RATE_KEYS and not _priced({key: held['value']}, key)):
            values[key] = entry
        elif held['value'] != entry['value'] and key not in TIER_RATE_KEYS:
            label = BY_KEY.get(key, {}).get('label', key)
            plan = f'{lead["carrier"]} {lead["name"]}'
            said.append(DISAGREE.format(plan=plan, label=label, first=held['value'], second=entry['value']))
    folded = {
        **lead,
        'plan_number': f'{lead["plan_number"]} / {other["plan_number"]}'.strip(' /'),
        'codes': sorted(set(lead['codes']) | set(other['codes'])),
        'docs': list(dict.fromkeys([*lead['docs'], *other['docs']])),
        'order': min(lead['order'], other['order']),
        'values': values,
        'unmapped': [*lead['unmapped'], *other['unmapped']],
    }
    return folded, said


def prepare(found, deal_plans):
    """(plans to stage in reading order, {merged key: the key it folded into}, [findings]) for a quote read."""
    out, aliases, findings = list(found), {}, []
    for first, second in pairs(found):
        hit_a, how_a = match(first, deal_plans)
        hit_b, how_b = match(second, deal_plans)
        if hit_a is not None and hit_a is hit_b and how_a == how_b == 'number':
            folded, said = fold(first, second)
            out[out.index(first)] = folded
            out.remove(second)
            aliases.update({half['key']: folded['key'] for half in (first, second) if half['key'] != folded['key']})
            findings += [{'text': text, 'hard': False} for text in said]
        elif hit_a is None and hit_b is None:
            names = [f'{plan["carrier"]} {plan["name"]}' for plan in (first, second)]
            findings.append({'text': FRESH.format(a=names[0], b=names[1]), 'hard': False})
    return out, aliases, findings


def unpaired(line, ids):
    """[(the plan priced for employees only, the plan priced for the dependent tiers only)] among `ids` on `line` (a
    `shapes.LineData`): one carrier, one kind (current or not), neither in a pair yet nor a renewal following one, each
    plan in one at most, in the line's order (the old proposal check `split_plan`; slice 33)."""
    taken = {pid for pair in printed.stored(line) for pid in pair}
    shown = [p for p in line.plans if p.id in set(ids) and p.id not in taken and not printed.follows(line, p.id)]

    def employee_only(plan):
        return _priced(plan.values, 'rate_ee') and not any(_priced(plan.values, key) for key in DEPENDENT)

    def dependents_only(plan):
        return not _priced(plan.values, 'rate_ee') and any(_priced(plan.values, key) for key in DEPENDENT)

    out, used = [], set()
    for first in (p for p in shown if employee_only(p)):
        for second in (p for p in shown if dependents_only(p) and p.id not in used):
            if norm(first.carrier) == norm(second.carrier) and (first.role == 'current') == (second.role == 'current'):
                out.append((first, second))
                used.add(second.id)
                break
    return out
