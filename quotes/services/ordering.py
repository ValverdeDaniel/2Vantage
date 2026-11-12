"""Writing a line's plan order (plan.md §5.4; F43–F48, J5–J11; OQ13): `plans/order/` and `plans/slot/`.

`arrange` moves one plan a place (passing hidden plans), swaps two quotes or puts the line back in its default order;
`put_in_slot` is a pick on "What the client will see": the picked plan takes the spot's place, star and links (F45),
or "＋ Add a plan" beside a current plan (F46). The rules are the pure `order` and `slots`; here they are written:
the Deal row locked, then the line's plans by id, only the columns that change saved with one `bulk_update`, one
revertible Activity row. Stop-loss is ordered like every line (OQ13). A refused move answers 409 with its sentence.
"""

from django.db import transaction

from deals import activity, clock, lines

from .. import columns, order, signals, slots
from ..selectors.state import line_data
from . import locks
from .batch import Batch
from .marks import HAND_PICKED

SLOT_KEYS = (*columns.STAR, 'plan.recommended', columns.REPLACES, 'plan.sort_order')


def _words(plan):
    return f'{plan.carrier} {plan.name}'


def _layout(line_key, rows):
    """The line's order as the screens read it once the write is made (plan ids)."""
    return [plan.id for plan in order.layout(line_data(line_key, list(rows.values())))]


def _summary(how, rows, label):
    kind = how[0]
    if kind == 'move':
        return f'Moved {_words(rows[how[1]])} {"earlier" if how[2] < 0 else "later"} on {label}'
    if kind == 'swap':
        return f'Swapped {_words(rows[how[1]])} and {_words(rows[how[2]])} on {label}'
    return f'Put {label} back in the default order'


@transaction.atomic
def arrange(user, deal, line_key, how):
    """`how`: ('move', plan id, step, among or None) | ('swap', a, b) | ('reset',).
    Returns (the line's order as the screens read it, plan ids; Activity row or None)."""
    deal = locks.deal(deal.id)
    rows, data = locks.line(deal, line_key)
    try:
        if how[0] == 'move':
            new_order = order.move(data, how[1], how[2], how[3])
        elif how[0] == 'swap':
            new_order = order.swap(data, how[1], how[2])
        else:
            new_order = order.reset(data)
    except order.Refused as exc:
        raise activity.Refused(str(exc)) from None
    numbers = order.numbering(data, new_order)
    batch = Batch([rows[pid] for pid in numbers], ('plan.sort_order',))
    for plan_id, number in numbers.items():
        rows[plan_id].sort_order = number
    _changed, changes = batch.write()
    if not changes:
        return _layout(line_key, rows), None
    signals.changed(deal.id, [line_key])
    summary = _summary(how, rows, lines.label(line_key))
    return _layout(line_key, rows), activity.record(
        deal, user, 'quotes', 'updated', summary, len(changes), changes=changes
    )


@transaction.atomic
def put_in_slot(user, deal, line_key, plan_id, at=None, beside=None):
    """Returns (changed plans, the line's order as plan ids, Activity row or None)."""
    deal = locks.deal(deal.id)
    rows, data = locks.line(deal, line_key)
    label = lines.label(line_key)
    try:
        placement = slots.prepare(data, label, plan_id, at=at, beside=beside)
    except slots.Refused as exc:
        raise activity.Refused(str(exc)) from None
    numbers = order.numbering(data, placement.order)
    touched = {*placement.stars_on, *placement.stars_off, *placement.unrecommend, *placement.links, *numbers}
    batch = Batch([rows[pid] for pid in sorted(touched)], SLOT_KEYS)
    now = clock.now()
    for pid in placement.stars_off:
        plan = rows[pid]
        plan.starred, plan.star_reason, plan.starred_by_id, plan.starred_at = False, '', None, None
    for pid in placement.stars_on:
        plan = rows[pid]
        plan.starred, plan.star_reason, plan.starred_by_id, plan.starred_at = True, HAND_PICKED, user.id, now
    for pid in placement.unrecommend:
        rows[pid].recommended = False
    for pid, replaces in placement.links.items():
        rows[pid].replaces_ids = replaces
    for pid, number in numbers.items():
        rows[pid].sort_order = number
    changed, changes = batch.write()
    if not changes:
        return [], _layout(line_key, rows), None
    signals.changed(deal.id, [line_key])
    picked = _words(rows[plan_id])
    if at is not None:
        summary = f'Put {picked} in the place of {_words(rows[at])} on the {label} proposal'
    elif beside is not None:
        summary = f'Added {picked} to the {label} proposal beside {_words(rows[beside])}'
    else:
        summary = f'Added {picked} to the {label} proposal'
    row = activity.record(deal, user, 'quotes', 'updated', summary, len(changed), changes=changes)
    return changed, _layout(line_key, rows), row
