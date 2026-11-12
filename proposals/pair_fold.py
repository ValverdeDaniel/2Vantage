"""Two plans printed as one column in the client files and on Pages (plan.md §5.4, §9.4; D-219, J15, F137, O.3.6,
OQ42; slice 33; the old `pipeline/plan_merge.py` at 891f1b3). Pure.

Florida Blue files one HSA plan as two plan numbers: 05182 holds the employee-only deductible, out-of-pocket maximum
and rate, 05183 the dependent tiers. Quotes keeps them two plans (`Plan.pair_of`, `quotes.pairs`); `fold` gives a
line's state with each pair the line presents as one column, under the first plan's id (its place, its marks, its
option number), so Pages, the PDF, the PowerPoint and the spreadsheet print one column. Every working screen keeps both.

The column's values are worked out by code from the two halves, never typed (the old rules):
- the single-coverage amounts (deductible and out-of-pocket, in and out of network) print both when they differ,
  "EE $2,500 / PP $5,000": employee-only from the half that carries the employee-only rate, per person from the other
  (OQ42's default: both figures);
- the family amounts come from the dependent half;
- each tier's rate and contribution from the half that carries it, and a quoted monthly premium is the two added;
- the plan numbers are joined, "05182 / 05183", and the names share their common words, "… 05182 + 05183";
- any other value prints once when the two agree, else both, "EE only $10 / with dependents $20".
Its figures are quotes': the pair priced as `package()` of the halves (`quotes.packages.folded`, rule 5).
"""

import copy
from dataclasses import replace

from quotes import fields, pairs
from quotes import math as m
from quotes import packages as pk
from quotes.shapes import LineData
from quotes.values import as_float

from . import formatting as fmt

SINGLE_KEYS = ('deductible_single', 'deductible_single_oon', 'oop_max_single', 'oop_max_single_oon')
FAMILY_KEYS = ('deductible_family', 'deductible_family_oon', 'oop_max_family', 'oop_max_family_oon')
CARRIED_KEYS = (*fields.TIER_RATE_KEYS, *fields.CONTRIB_KEYS)  # from the half that carries it
DEPENDENT_RATES = ('rate_es', 'rate_ec', 'rate_fam')
SUM_KEYS = ('group_premium_monthly',)
FIRST_KEYS = ('sbc_url',)  # a link, never a benefit row: the first half's, else the other's
NUMERIC = ('amount', 'rate', 'rate4', 'percent', 'number')


def _text(raw):
    return str('' if raw is None else raw).strip()


def _carries(values, key):
    number = as_float(values.get(key))
    return number not in (None, 0.0)


def employee_half(first, second):
    """(the employee-only half, the dependent half): the plan carrying the employee-only rate and no dependent tier
    first; the stored order when the rates do not say (the old `employee_half`)."""

    def only_employee(plan):
        return _carries(plan.values, 'rate_ee') and not any(_carries(plan.values, key) for key in DEPENDENT_RATES)

    if only_employee(second) and not only_employee(first):
        return second, first
    return first, second


def _same(key, left, right):
    if left == right:
        return True
    kind = fields.BY_KEY.get(key, {}).get('type')
    a, b = as_float(left), as_float(right)
    return kind in NUMERIC and a is not None and a == b


def merged_value(key, ee, dep, first):
    """The one column's value for `key` from the employee-only half's values `ee`, the dependent half's `dep` and the
    first half's `first` (the module's rules); '' when neither half has one."""
    left, right = _text(ee.get(key)), _text(dep.get(key))
    if key in CARRIED_KEYS:
        found = next((value for value in (left, right) if _carries({key: value}, key)), None)
        return found if found is not None else left or right
    if key in SUM_KEYS:
        total = m.add([left, right]) if left and right else None
        return str(total) if total is not None else left or right
    if key in FIRST_KEYS:
        return _text(first.get(key)) or left or right
    if key in FAMILY_KEYS:
        return right or left
    if not left or not right or _same(key, left, right):
        return left or right
    shown_left, shown_right = fmt.value(key, left) or left, fmt.value(key, right) or right
    if key in SINGLE_KEYS:
        return f'EE {shown_left} / PP {shown_right}'
    return f'EE only {shown_left} / with dependents {shown_right}'


def merged_values(ee, dep, first):
    keys = dict.fromkeys([*ee.values, *dep.values])
    out = {key: merged_value(key, ee.values, dep.values, first.values) for key in keys}
    return {key: value for key, value in out.items() if value != ''}


def merged_name(first, second):
    """'BlueOptions HSA Compatible 05182 + 05183': the words the two names share, then the first word on which each
    differs; both names whole when they share none (the old `merged_name`)."""
    a, b = str(first or '').split(), str(second or '').split()
    common = 0
    while common < min(len(a), len(b)) and a[common] == b[common]:
        common += 1
    if not common:
        return f'{first} + {second}'
    head = ' '.join(a[:common])
    tails = [words[common] for words in (a, b) if len(words) > common]
    return f'{head} {" + ".join(tails)}' if len(tails) == 2 else head


def _number(ee, dep):
    left, right = _text(ee.plan_number), _text(dep.plan_number)
    if not left or not right or left == right:
        return left or right
    return f'{left} / {right}'


def column(first, second):
    """The pair's one column as a model row: a copy of the first half (never saved) with the merged values, names and
    number, and the marks either half carries. `pair` names both halves, the employee-only one first, and
    `own_name` is the first half's own name (Pages shows it with "+ the other (one column)", F137)."""
    ee, dep = employee_half(first, second)
    row = copy.copy(first)
    row.values = merged_values(ee, dep, first)
    row.name = merged_name(ee.name, dep.name)
    named = first.client_name or second.client_name
    row.client_name = merged_name(ee.client_name or ee.name, dep.client_name or dep.name) if named else ''
    row.plan_number = _number(ee, dep)
    row.recommended = first.recommended or second.recommended
    row.starred = first.starred or second.starred
    row.sold = first.sold or second.sold
    row.pair = (ee.id, dep.id)
    row.own_name = first.client_name or first.name
    row.partner_name = second.client_name or second.name
    return row


def _moved(plan, gone):
    renews = gone.get(plan.renews, plan.renews)
    replaces = tuple(dict.fromkeys(gone.get(pid, pid) for pid in plan.replaces))
    version_of = gone.get(plan.version_of, plan.version_of)
    if (renews, replaces, version_of) == (plan.renews, plan.replaces, plan.version_of):
        return plan
    return replace(plan, renews=renews, replaces=replaces, version_of=version_of)


def fold(state, ids):
    """(the line's `LineState` with each pair among `ids` as one column, {first id: second id}). The state is
    returned as it is when no pair folds. Links, renewals and versions naming a second half now name the first."""
    data = state.data
    found = pairs.found(data, ids)
    if not found:
        return state, {}
    gone = {second: first for first, second in found}
    rows = {row.id: row for row in state.plans}
    columns = {first: column(rows[first], rows[second]) for first, second in found}
    results = pk.folded(data, state.results, found)
    plans = []
    for plan in data.plans:
        if plan.id in gone:
            continue
        row = columns.get(plan.id)
        if row is not None:
            plan = replace(
                plan,
                name=row.name,
                plan_number=row.plan_number,
                values=row.values,
                recommended=row.recommended,
                starred=row.starred,
                sold=row.sold,
                enrollment=results[plan.id]['enrollment_used'] or {},
            )
        plans.append(_moved(plan, gone))
    line = LineData(data.rate_basis, plans, key=data.key, people=data.people)
    kept = [columns.get(row.id, row) for row in state.plans if row.id not in gone]
    return state._replace(plans=kept, data=line, results=results), dict(found)
