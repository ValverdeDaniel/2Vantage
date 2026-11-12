"""Roles and links, each through its own door (plan.md §5.4; F52, F53, J12): `plans/role/` and `plans/links/`.

- `current` is in force today and has no links. A plan that turns current loses its star and its links, and joins
  the end of the line's current plans; a recommendation stays, meaning "Keep this plan" (OQ37, as in the old app).
  A sold plan or a priced version never becomes current.
- `renewal` renews one current plan on the same line, at most one renewal each; it leads that plan's group.
- `alternate` replaces none, one or several current plans on the same line (several: a consolidation).
- A current plan that stops being current turns its renewal into an alternate and leaves every `replaces` list.
Both doors lock the Deal, then the line's plans by id, and record one revertible Activity row with before and after.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, lines

from .. import columns, order, signals
from ..selectors.state import line_data
from . import locks
from .batch import Batch

ROLES = ('current', 'renewal', 'alternate')
STAR_AND_PICK = (*columns.STAR, 'plan.recommended')
KEYS = (*columns.LINKS, *STAR_AND_PICK, 'plan.sort_order')
ROLE_WORDS = {'current': 'current', 'renewal': 'a renewal', 'alternate': 'an alternate'}
ROLES_WORDS = {'current': 'current', 'renewal': 'renewals', 'alternate': 'alternates'}


def check_role(role):
    if role not in ROLES:
        raise ValidationError({'role': ['Role must be current, renewal or alternate.']})
    return role


def _currents(rows, ids, exclude=None):
    ids = list(dict.fromkeys(ids or []))
    found = [rows[pid] for pid in ids if pid in rows and rows[pid].role == 'current' and pid != exclude]
    if len(found) != len(ids):
        raise ValidationError({'links': ['Links must name current plans on this deal and line.']})
    return [plan.id for plan in found]


def links_for(rows, role, renews_id=None, replaces_ids=(), plan_id=None):
    """(renews id or None, [replaced ids]) a plan with `role` takes on this line (`rows`: {id: plan}); 400 when they
    break §5.4's rules."""
    if role == 'current':
        return None, []
    if role == 'renewal':
        if not renews_id:
            raise ValidationError({'renews_id': ['A renewal must name the current plan it renews.']})
        (renews,) = _currents(rows, [renews_id])
        taken = [p for p in rows.values() if p.role == 'renewal' and p.renews_id == renews and p.id != plan_id]
        if taken:
            raise ValidationError({'renews_id': [f'{rows[renews].name} already has a renewal.']})
        return renews, []
    return None, _currents(rows, replaces_ids, exclude=plan_id)


def _words(plan):
    return f'{plan.carrier} {plan.name}'


def no_longer_current(rows, plan):
    """Its renewal becomes an alternate and it leaves every `replaces` list (§5.4)."""
    for other in rows.values():
        if other.role == 'renewal' and other.renews_id == plan.id:
            other.role, other.renews_id, other.replaces_ids = 'alternate', None, []
        if plan.id in other.replaces_ids:
            other.replaces_ids = [pid for pid in other.replaces_ids if pid != plan.id]


def _turn_current(rows, plan):
    refusals = {
        'sold': f"{_words(plan)} is sold: the plan the client is buying can't also be the plan they have in force "
        'today.',
        'version': f"{_words(plan)} is a priced version: the plan in force is the carrier's own column.",
    }
    if plan.sold:
        raise activity.Refused(refusals['sold'])
    if plan.derived_from_id and plan.derived.get('kind') != 'duplicate':
        raise activity.Refused(refusals['version'])
    plan.starred, plan.star_reason, plan.starred_by_id, plan.starred_at = False, '', None, None
    plan.sort_order = max(p.sort_order for p in rows.values()) + 1  # last among the current plans


def lead_renewals(line_key, rows, renewals):
    """Put each new renewal first in its plan's group (F120)."""
    for plan in renewals:
        data = line_data(line_key, list(rows.values()))
        for plan_id, number in order.numbering(data, order.lead(data, plan.id)).items():
            rows[plan_id].sort_order = number


def _record(user, deal, line_key, summary, changed, changes):
    if not changes:
        return None
    signals.changed(deal.id, [line_key])
    return activity.record(deal, user, 'quotes', 'updated', summary, len(changed), changes=changes)


@transaction.atomic
def set_role(user, deal, plan_ids, role, renews_id=None, replaces_ids=()):
    """`plans/role/` (Mark current, Remove current, or a renewal or alternate with the links the role needs).
    Returns (changed plans, Activity row or None); a plan already in `role` is left as it is."""
    check_role(role)
    if role == 'renewal' and len(set(plan_ids)) != 1:
        raise ValidationError({'plan_ids': ['Make one plan at a time a renewal.']})
    deal = locks.deal(deal.id)
    targets = locks.plans(deal, plan_ids)
    line_keys = {plan.line for plan in targets}
    if len(line_keys) != 1:
        raise ValidationError({'plan_ids': ['Change the roles of plans on one line at a time.']})
    (line_key,) = line_keys
    rows, _data = locks.line(deal, line_key)
    batch = Batch(rows.values(), KEYS)
    moving = [rows[plan.id] for plan in targets if rows[plan.id].role != role]
    renewals = []
    for plan in moving:
        renews, replaces = links_for(rows, role, renews_id, replaces_ids, plan.id)
        if role == 'current':
            _turn_current(rows, plan)
        if plan.role == 'current':
            no_longer_current(rows, plan)
        plan.role, plan.renews_id, plan.replaces_ids = role, renews, replaces
        if role == 'renewal':
            renewals.append(plan)
    lead_renewals(line_key, rows, renewals)
    changed, changes = batch.write()
    if len(moving) == 1:
        summary = f'Made {_words(moving[0])} {ROLE_WORDS[role]}'
    else:
        summary = f'Made {len(moving)} {lines.label(line_key)} plans {ROLES_WORDS[role]}'
    return changed, _record(user, deal, line_key, summary, changed, changes)


@transaction.atomic
def set_links(user, deal, plan_id, replaces_ids=None, renews_id=None):
    """`plans/links/`: the current plans an alternate replaces, or the one a renewal renews.
    Returns (changed plans, Activity row or None)."""
    deal = locks.deal(deal.id)
    (target,) = locks.plans(deal, [plan_id])
    rows, _data = locks.line(deal, target.line)
    plan = rows[target.id]
    if plan.role == 'current':
        raise activity.Refused(f'{_words(plan)} is a current plan: only a proposed plan takes a link.')
    batch = Batch(rows.values(), KEYS)
    if plan.role == 'renewal':
        if replaces_ids:
            current = rows.get(plan.renews_id)
            name = _words(current) if current else 'its plan'
            raise activity.Refused(f'{_words(plan)} is the renewal of {name}: it compares with that plan.')
        if renews_id is not None and renews_id != plan.renews_id:
            plan.renews_id, _ = links_for(rows, 'renewal', renews_id, (), plan.id)
            lead_renewals(target.line, rows, [plan])
    elif replaces_ids is not None:
        _, plan.replaces_ids = links_for(rows, 'alternate', None, replaces_ids, plan.id)
    changed, changes = batch.write()
    names = [_words(rows[pid]) for pid in ([plan.renews_id] if plan.role == 'renewal' else plan.replaces_ids)]
    summary = f'Linked {_words(plan)} to {" and ".join(names)}' if names else f'Unlinked {_words(plan)}'
    return changed, _record(user, deal, target.line, summary, changed, changes)
