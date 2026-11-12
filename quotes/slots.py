"""Put a plan in another plan's spot on the client's comparison (plan.md §5.4; F45, F46, J10, J11; D-221). Pure.

Daniel's rule (2026-11-10): the picked plan X takes the spot of the plan P that was there, its place, its star and the
current plans it replaces, and P takes X's. So:
- X off the proposal, P on it: X goes on and P comes off (a replacement), so the line's columns stay as they were and
  the 16 cap never refuses one; P loses its star and its recommendation (the plan that leaves loses its pick);
- both on (or both off, on the Advisor): they trade places and, on a line with two or more current plans, their
  whole `replaces` sets;
- a renewal stays beside the plan it renews, and a current plan or a priced version never takes a picked spot.
`beside` is "＋ Add a plan": X goes on the proposal (within `room()`), beside that current plan, last among the plans
compared with it. Stop-loss takes picks like every line (OQ13).

`prepare` returns a `Placement` and writes nothing; `services.ordering.put_in_slot` writes it under the Deal lock.
"""

from collections import namedtuple

from . import order, presented

# Plan ids gaining a star, losing one, losing their recommendation; {alternate id: [current ids it replaces]}; and the
# line's whole new order (plan ids).
Placement = namedtuple('Placement', 'stars_on stars_off unrecommend links order')


class Refused(ValueError):
    """A pick the line refuses; the message is shown as it is and names the plan."""


def _plain(line, plan):
    if plan.role == 'current':
        raise Refused(f'{plan.words} is a current plan: current plans lead each page, and their arrows move them.')
    if line.root(plan).id != plan.id:
        raise Refused(f'{plan.words} is a priced version: it moves with its plan.')
    return plan


def _links(plan):
    """The current plans a plan is linked to: a renewal's plan, or an alternate's `replaces`."""
    return {plan.renews} if plan.role == 'renewal' else set(plan.replaces)


def _relink(line, moves):
    """{alternate id: [current ids]} for `moves` [(plan, wanted set)]; Refused for a renewal asked to leave its plan."""
    slot = {p.id: i for i, p in enumerate(line.current)}
    links = {}
    for plan, wanted in moves:
        if wanted == _links(plan):
            continue
        if plan.role == 'renewal':
            current = line.by_id.get(plan.renews)
            name = current.words if current else 'its plan'
            raise Refused(f'{plan.words} is the renewal of {name}: it stays beside that plan.')
        links[plan.id] = sorted(wanted, key=lambda pid: slot.get(pid, len(slot)))
    return links


def _on(line):
    starred = presented.has_stars(line)
    return lambda plan: not starred or presented.is_held(plan)


def prepare(line, label, plan_id, at=None, beside=None):
    """The Placement for putting plan `plan_id` in plan `at`'s spot, or (no `at`) beside the current plan `beside`
    (None on a line with one current plan or none). `label` names the line in a refusal ("Medical")."""
    picked = line.by_id.get(plan_id)
    if picked is None:
        raise Refused('That plan is not on this line.')
    _plain(line, picked)
    try:
        if at is not None:
            return _swap(line, picked, line.by_id.get(at))
        return _add(line, label, picked, line.by_id.get(beside) if beside is not None else None, beside)
    except order.Refused as exc:
        raise Refused(str(exc)) from None


def _swap(line, picked, spot):
    if spot is None:
        raise Refused('That spot is not on this line.')
    if spot.id == picked.id:
        raise Refused(f'{picked.words} is already there.')
    _plain(line, spot)
    on = _on(line)
    stars_on, stars_off, unrecommend = [], [], []
    leaving = None
    if on(picked) != on(spot):
        coming, leaving = (picked, spot) if on(spot) else (spot, picked)
        stars_on = [coming.id] if not coming.starred else []
        stars_off = [leaving.id] if leaving.starred else []
        unrecommend = [leaving.id] if leaving.recommended else []
    links = {}
    if len(line.current) >= 2 and _links(picked) != _links(spot):
        # The picked plan joins the spot's current plans; the spot's plan joins the picked one's, unless it is leaving
        # the proposal, where its links no longer print.
        moves = [(picked, _links(spot))] + ([] if leaving is spot else [(spot, _links(picked))])
        links = _relink(line, moves)
    return Placement(stars_on, stars_off, unrecommend, links, order.swap(line, picked.id, spot.id))


def _add(line, label, picked, current, beside):
    if beside is not None and (current is None or current.role != 'current'):
        raise Refused('Add a plan beside a current plan on this line.')
    stars_on = []
    if not _on(line)(picked):
        refusal = presented.refusal(line, label, presented.added(line, [picked.id]))
        if refusal:
            raise Refused(refusal)
        stars_on = [picked.id]
    links = {}
    if len(line.current) >= 2 and current is not None and _links(picked) != {current.id}:
        if picked.role == 'renewal':
            raise Refused(f'{picked.words} is a renewal: it stays beside the plan it renews.')
        links = _relink(line, [(picked, {current.id})])
    return Placement(stars_on, [], [], links, order.last(line, picked.id))
