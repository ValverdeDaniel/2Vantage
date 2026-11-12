"""Copies of a plan (plan.md §5.4; F81, F141, D-049): Create renewal and Duplicate (`copy_plan`).

Both take the plan's values and their sources through `values.apply`, without marks, confirmations or a read value
(a read value stays only on plans the reader made, F141), and never its star, recommendation or sale.
- Create renewal copies every value except the rate, contribution and level-funded groups and leads its plan's group.
- `copy_plan` is a standalone peer with every value, rates included (D-049; v1.1's rate-less "Copy as alternate",
  F77, retires). It is an alternate replacing what the original replaces (a current plan's copy replaces that plan,
  a renewal's copy replaces its current plan), carries the original's client name and file, and records where it came
  from (`derived_from`, `derived.kind` "duplicate"), so it may become current but never moves line alone (F59). The
  person names it; unnamed, it is "<name> — copy", as in the old app. It arrives right behind its original.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals.values import apply as apply_values
from deals.values import locked

from .. import fields, order, signals
from ..models import Plan
from ..selectors.state import line_data
from . import locks
from .plans import next_number, placed

COPY_DROPS = ('read_value', 'mark', 'confirmed')


def copied_source(original):
    """The source entry a copy takes for each key: its original's, without marks, approvals or a read value."""

    def make(key):
        entry = dict(original.sources.get(key) or {'origin': 'typed'})
        for name in COPY_DROPS:
            entry.pop(name, None)
        return entry

    return make


def new_plan(deal, original, role, **extra):
    """An unsaved plan with its original's carrier, names and line, last in the line's hand order."""
    shared = {
        'carrier': original.carrier,
        'name': original.name,
        'plan_number': original.plan_number,
        'client_name': original.client_name,
    }
    return Plan(deal=deal, line=original.line, role=role, sort_order=next_number(deal, original.line), **shared | extra)


def _save(plan, original, values, replaces=()):
    diff = apply_values(plan.values, plan.sources, values, copied_source(original))
    plan.save()
    plan.replaces.set(replaces)
    plan.replaces_ids = sorted(replaces)
    return diff


@transaction.atomic
def create_renewal(user, plan_id):
    deal = locks.plan_deal(plan_id)
    current = locked(Plan, plan_id)
    if current.role != 'current':
        raise ValidationError({'detail': 'Only a current plan can be renewed.'})
    if Plan.objects.filter(renews=current).exists():
        raise ValidationError({'detail': f'{current.name} already has a renewal.'})
    design = {
        k: v for k, v in current.values.items() if fields.BY_KEY.get(k, {}).get('group') not in fields.PRICE_GROUPS
    }
    plan = new_plan(deal, current, 'renewal', renews_id=current.id)
    diff = _save(plan, current, design)
    changes = [activity.change(f'plan:{plan.id}', diff), *placed(deal, plan)]
    summary = f'Created the renewal of {current.carrier} {current.name}'
    activity.record(deal, user, 'quotes', 'created', summary, changes=changes)
    signals.changed(deal.id, [plan.line])
    return plan


def replaces_of(original):
    """What a copy or priced version replaces: a current plan's copy that plan, a renewal's copy its current plan, an
    alternate's copy what the alternate replaces (`original.replaces_ids` set)."""
    if original.role == 'current':
        return [original.id]
    if original.role == 'renewal':
        return [original.renews_id] if original.renews_id else []
    return list(original.replaces_ids)


def copy_name(original, name=''):
    typed = (name or '').strip() if isinstance(name, str) else ''
    return (typed or f'{original.name} — copy')[:200]


def _side_by_side(deal, plan, original):
    """Activity changes of the plans the copy passes on its way to the place right behind its original."""
    rows, _data = locks.line(deal, plan.line)
    data = line_data(plan.line, list(rows.values()))
    numbers = order.numbering(data, order.behind(data, plan.id, original.id))
    moved = []
    for plan_id, number in numbers.items():
        moved.append(activity.change(f'plan:{plan_id}', {'plan.sort_order': [rows[plan_id].sort_order, number]}))
        rows[plan_id].sort_order = number
    Plan.objects.bulk_update([rows[plan_id] for plan_id in numbers], ['sort_order'])
    plan.sort_order = rows[plan.id].sort_order
    return [change for change in moved if change['t'] != f'plan:{plan.id}']


@transaction.atomic
def copy_plan(user, plan_id, name=''):
    """`plans/{id}/copy/` {name?}: Duplicate, keeping the rates. Returns the copy."""
    deal = locks.plan_deal(plan_id)
    rows, _data = locks.line(deal, Plan.objects.values_list('line', flat=True).get(pk=plan_id))
    original = rows[plan_id]
    replaces = replaces_of(original)
    derived = {'kind': 'duplicate', 'by': getattr(user, 'id', None), 'at': clock.now().isoformat()}
    plan = new_plan(
        deal,
        original,
        'alternate',
        name=copy_name(original, name),
        derived_from=original,
        derived=derived,
        source_document_id=original.source_document_id,
    )
    diff = _save(plan, original, dict(original.values), replaces)
    changes = [activity.change(f'plan:{plan.id}', diff), *_side_by_side(deal, plan, original)]
    summary = f'Duplicated {original.carrier} {original.name} as {plan.name}'
    activity.record(deal, user, 'quotes', 'created', summary, changes=changes)
    signals.changed(deal.id, [plan.line])
    return plan
