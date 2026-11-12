"""The one plan order of a line (plan.md §5.4; F43–F48, F120, J4–J6; OQ13). Pure, over `shapes.LineData`.

`layout(line)` is the only reader of `Plan.sort_order`, one sequence per line: the current plans first, in their slot
order, then the priced versions of current plans; then the quotes grouped under the current plan they are compared
with (`LineData.base_ids`: a renewal under its plan, a consolidation under the first plan it replaces in slot order,
an unlinked alternate on a one-plan line under that plan), the groups in slot order; quotes compared with no plan
last. Inside a group the hand order (`sort_order`) holds, each priced version right behind its original; copies are
peers. Values never sort it, so a rate edit moves nothing. Stop-loss is ordered like every line (OQ13).

The moves (`move`, `swap`, `last`, `lead`, `reset`) return the line's new hand order, every plan id once;
`numbering` turns it into the `sort_order` values that change, and `layout` reads it back (a quote whose links change
in the same write, as in a slot pick, lands in its new group at its new place). A move a line refuses raises
`Refused` with the sentence.
"""

from collections import namedtuple

Unit = namedtuple('Unit', 'group ids')  # a quote with its priced versions, and the current plan it groups under


class Refused(ValueError):
    """A move the order refuses; the message is shown as it is and names the plan."""


def _key(plan):
    return (plan.sort_order, plan.id)


def _pinned(line):
    """Priced versions of current plans: they lead with the current plans and never take an arrow."""
    slot = {p.id: i for i, p in enumerate(line.current)}
    versions = [p for p in line.plans if p.role != 'current' and line.root(p).id in slot]
    return sorted(versions, key=lambda p: (slot[line.root(p).id], *_key(p)))


def _units(line):
    """The quote units in layout order."""
    slot = {p.id: i for i, p in enumerate(line.current)}
    members = {}
    for plan in sorted(line.plans, key=_key):
        root = line.root(plan)
        if root.role == 'current' or plan.role == 'current':
            continue
        members.setdefault(root.id, [])
        if plan.id != root.id:
            members[root.id].append(plan.id)
    units = []
    for root in sorted((line.by_id[root_id] for root_id in members), key=_key):
        bases = line.base_ids(root)
        units.append(Unit(bases[0] if bases else None, [root.id, *members[root.id]]))
    return sorted(units, key=lambda unit: slot.get(unit.group, len(slot)))  # stable: hand order inside a group


def _flat(currents, line, units):
    return [p.id for p in currents] + [p.id for p in _pinned(line)] + [pid for unit in units for pid in unit.ids]


def layout(line):
    """The line's plans, left to right."""
    return [line.by_id[pid] for pid in _flat(line.current, line, _units(line))]


def _plan(line, plan_id):
    plan = line.by_id.get(plan_id)
    if plan is None:
        raise Refused('That plan is not on this line.')
    return plan


def _unit_at(line, units, plan_id):
    """The index of the unit `plan_id` moves as, or Refused for what never takes a place by hand."""
    plan = _plan(line, plan_id)
    if plan.role == 'current':
        raise Refused(f'{plan.words} is a current plan: move it among the current plans.')
    root = line.root(plan)
    if root.role == 'current':
        raise Refused(f'{plan.words} is a priced version of a current plan: it moves with that plan.')
    return next(i for i, unit in enumerate(units) if unit.ids[0] == root.id)


def move(line, plan_id, step, among=None):
    """One place earlier (-1) or later (1). A quote moves inside its group, past the nearest plan in `among` (the ids
    on screen; None = every plan); a current plan moves among the current plans as a slot, and its group follows."""
    if step not in (-1, 1):
        raise Refused('Move a plan one place at a time.')
    plan = _plan(line, plan_id)
    where = 'first' if step < 0 else 'last'
    if plan.role == 'current':
        currents = list(line.current)
        at = currents.index(plan)
        to = at + step
        if not 0 <= to < len(currents):
            raise Refused(f'{plan.words} is already {where} among the current plans.')
        currents[at], currents[to] = currents[to], currents[at]
        return _flat(currents, line, _units(line))
    units = _units(line)
    me = _unit_at(line, units, plan_id)
    group, shown = units[me].group, None if among is None else set(among)
    to = me + step
    while 0 <= to < len(units) and units[to].group == group:
        if shown is None or any(pid in shown for pid in units[to].ids):
            break
        to += step
    else:
        current = line.by_id.get(group)
        beside = f' among the plans compared with {current.words}' if current else ''
        raise Refused(f'{plan.words} is already {where}{beside}.')
    units.insert(to, units.pop(me))  # earlier: in front of the neighbour; later: just past it
    return _flat(line.current, line, units)


def swap(line, a, b):
    """Quotes `a` and `b` trade places, each with its priced versions (a slot pick, F45). Which current plan each sits
    with is its links' business: the layout groups them after."""
    units = _units(line)
    i, j = _unit_at(line, units, a), _unit_at(line, units, b)
    if i == j:
        raise Refused(f'{line.by_id[a].words} and {line.by_id[b].words} are one quote.')
    units[i], units[j] = units[j], units[i]
    return _flat(line.current, line, units)


def last(line, plan_id):
    """The quote last in the line's hand order, so it lands last in whichever group its links put it ("＋ Add a plan"
    beside a current plan, F46)."""
    units = _units(line)
    units.append(units.pop(_unit_at(line, units, plan_id)))
    return _flat(line.current, line, units)


def lead(line, plan_id):
    """The quote first in its group: where a renewal arrives (a renewal leads its plan's group, F120)."""
    units = _units(line)
    me = _unit_at(line, units, plan_id)
    first = next(i for i, unit in enumerate(units) if unit.group == units[me].group)
    units.insert(first, units.pop(me))
    return _flat(line.current, line, units)


def reset(line):
    """ "Back to the default order" (F48): inside each group the renewal first, then the quotes as they were added,
    each priced version behind its original. The current plans keep their slot order."""
    units = _units(line)
    renewal_first = sorted(units, key=lambda unit: (line.by_id[unit.ids[0]].role != 'renewal', unit.ids[0]))
    slot = {p.id: i for i, p in enumerate(line.current)}
    units = sorted(
        (Unit(unit.group, [unit.ids[0], *sorted(unit.ids[1:])]) for unit in renewal_first),
        key=lambda unit: slot.get(unit.group, len(slot)),
    )
    return _flat(line.current, line, units)


def numbering(line, order):
    """{plan id: sort_order} for the plans whose number changes when the line takes `order`. Reuses the line's own
    numbers in rising order, so a move rewrites only the plans it passes; tied numbers are renumbered from 0."""
    numbers = sorted(plan.sort_order for plan in line.plans)
    if len(set(numbers)) < len(numbers):
        numbers = list(range(len(numbers)))
    return {pid: n for pid, n in zip(order, numbers, strict=True) if line.by_id[pid].sort_order != n}
