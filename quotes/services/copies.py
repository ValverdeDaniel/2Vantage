"""Copies of a plan (plan.md §5.4; F141): Create renewal and Copy as alternate.

A copy takes the plan's values and their sources through `values.apply`, without marks, confirmations or a read
value (a read value stays only on plans the reader made, F141), and never its star, recommendation or sale. Create
renewal copies every value except the rate, contribution and level-funded groups and leads its plan's group; Copy as
alternate (without rates until slice 8's `copy_plan`) replaces what the original replaces and lands last.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity
from deals.values import apply as apply_values
from deals.values import locked

from .. import fields, signals
from ..models import Plan
from . import locks
from .plans import next_number, placed

COPY_DROPS = ('read_value', 'mark', 'confirmed')


def _copied_source(original):
    def make(key):
        entry = dict(original.sources.get(key) or {'origin': 'typed'})
        for name in COPY_DROPS:
            entry.pop(name, None)
        return entry

    return make


def _copy(user, deal, original, role, renews=None, replaces=()):
    copied = {
        k: v for k, v in original.values.items() if fields.BY_KEY.get(k, {}).get('group') not in fields.PRICE_GROUPS
    }
    plan = Plan(
        deal=deal,
        line=original.line,
        role=role,
        carrier=original.carrier,
        name=original.name,
        plan_number=original.plan_number,
        client_name=original.client_name,
        renews_id=renews,
        sort_order=next_number(deal, original.line),
    )
    diff = apply_values(plan.values, plan.sources, copied, _copied_source(original))
    plan.save()
    plan.replaces.set(replaces)
    plan.replaces_ids = sorted(replaces)
    return plan, [activity.change(f'plan:{plan.id}', diff), *placed(deal, plan)]


@transaction.atomic
def create_renewal(user, plan_id):
    deal = locks.plan_deal(plan_id)
    current = locked(Plan, plan_id)
    if current.role != 'current':
        raise ValidationError({'detail': 'Only a current plan can be renewed.'})
    if Plan.objects.filter(renews=current).exists():
        raise ValidationError({'detail': f'{current.name} already has a renewal.'})
    plan, changes = _copy(user, deal, current, 'renewal', renews=current.id)
    summary = f'Created the renewal of {current.carrier} {current.name}'
    activity.record(deal, user, 'quotes', 'created', summary, changes=changes)
    signals.changed(deal.id, [plan.line])
    return plan


@transaction.atomic
def copy_as_alternate(user, plan_id):
    deal = locks.plan_deal(plan_id)
    original = locked(Plan, plan_id)
    if original.role == 'current':
        replaces = [original.id]
    elif original.role == 'renewal':
        replaces = [original.renews_id] if original.renews_id else []
    else:
        replaces = list(original.replaces.values_list('id', flat=True))
    plan, changes = _copy(user, deal, original, 'alternate', replaces=replaces)
    summary = f'Copied {original.carrier} {original.name} as an alternate'
    activity.record(deal, user, 'quotes', 'created', summary, changes=changes)
    signals.changed(deal.id, [plan.line])
    return plan
