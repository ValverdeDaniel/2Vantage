"""One plan filed under two plan numbers, printed as one column (plan.md §5.4; D-219, J15, F137, O.6 #4; slice 33).
Pure, over `shapes.LineData`.

Florida Blue files one HSA plan as two plan numbers: 05182 holds the employee-only deductible, out-of-pocket maximum
and rate, 05183 the dependent tiers. The halves stay two plans (each value still traces to its own file, and every
working screen shows both); a pair is stored on its second half (`Plan.pair_of` names the first), and client files
print the two as one column under the first plan's id, place and option number (proposals' `pair_fold`), priced as
`package()` of the pair (`packages.folded`).

`found(line, ids)` is the one rule for which pairs print as one, read by `presented.room()` (a pair counts once
against the 16 columns), Pages and the three files:
- a stored pair prints as one where both halves are among `ids` (the plans the line presents), on this line, and of
  one kind: two current plans, or two quotes;
- when both current plans of a pair have a renewal among `ids`, the two renewals print as one too, derived on read and
  never stored (the old `plan_merge.groups`).
"""


def _side(plan):
    return plan.role == 'current'


def stored(line):
    """[(first id, second id)] stored on the line: a second half naming a live first of its own kind, which is not
    itself a second half. In the line's order of the first halves."""
    seconds = {}
    for plan in line.plans:
        first = line.by_id.get(plan.pair_of)
        if first is None or first.id == plan.id or first.pair_of is not None or _side(first) != _side(plan):
            continue
        seconds.setdefault(first.id, plan.id)
    return [(plan.id, seconds[plan.id]) for plan in line.plans if plan.id in seconds]


def _renewal_of(line, current_id, ids):
    return next((p.id for p in line.plans if p.id in ids and p.role == 'renewal' and p.renews == current_id), None)


def found(line, ids=None):
    """[(first id, second id)] that print as one column among `ids` (every plan on the line when None): the stored
    pairs with both halves there, then the renewal pair each current pair implies."""
    ids = {plan.id for plan in line.plans} if ids is None else set(ids)
    out, used = [], set()
    for first, second in stored(line):
        if first not in ids or second not in ids or {first, second} & used:
            continue
        out.append((first, second))
        used |= {first, second}
        if line.by_id[first].role == 'current':
            renewals = (_renewal_of(line, first, ids), _renewal_of(line, second, ids))
            if all(renewals) and not set(renewals) & used:
                out.append(renewals)
                used |= set(renewals)
    return out


def partner(line, plan_id):
    """The other half of the stored pair holding `plan_id`, or None."""
    for first, second in stored(line):
        if plan_id in (first, second):
            return second if plan_id == first else first
    return None


def follows(line, plan_id):
    """A renewal whose current plan is in a stored pair prints as one column with the other current plan's renewal:
    (that renewal's id) or None. Derived, so it has no Split of its own."""
    plan = line.by_id.get(plan_id)
    if plan is None or plan.role != 'renewal' or plan.renews is None:
        return None
    other = partner(line, plan.renews)
    if other is None or line.by_id[plan.renews].role != 'current':
        return None
    return _renewal_of(line, other, {p.id for p in line.plans})


def columns(line, ids):
    """How many columns `ids` print as: one per plan, a pair once."""
    ids = set(ids)
    return len(ids) - len(found(line, ids))
