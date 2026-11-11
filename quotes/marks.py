"""Marks on plans (star, recommend, sold), typed enrollment and member-built packages (plan.md §5.4, §5.5)."""

from django.db import IntegrityError, transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from deals import activity, clock, lines
from deals.models import Deal
from deals.services import advance
from deals.values import locked

from . import math as m
from .models import Package, Plan


@transaction.atomic
def star(user, deal, plan_ids, starred):
    count = Plan.objects.filter(deal=deal, id__in=plan_ids).update(starred=bool(starred))
    activity.record(
        deal, user, 'quotes', 'updated', 'Starred' if starred else 'Unstarred', count, 'quotes:star', 'plan'
    )
    return count


@transaction.atomic
def set_recommended(user, plan_id, recommended):
    plan = locked(Plan, plan_id)
    if recommended and plan.role == 'current':
        raise ValidationError(
            {'detail': "A current plan can't be recommended — recommend its renewal to keep what they have."}
        )
    if plan.recommended != bool(recommended):
        plan.recommended = bool(recommended)
        plan.save(update_fields=['recommended', 'updated_at'])
        verb = 'Recommended' if recommended else 'Removed the recommendation of'
        activity.record(plan.deal, user, 'quotes', 'updated', f'{verb} {plan.carrier} {plan.name}')
    return plan


@transaction.atomic
def set_sold(user, plan_id, sold):
    plan = locked(Plan, plan_id)
    deal = locked(Deal, plan.deal_id)
    if plan.sold == bool(sold):
        return plan, deal
    plan.sold = bool(sold)
    plan.sold_at = clock.now() if sold else None
    plan.save(update_fields=['sold', 'sold_at', 'updated_at'])
    if sold:
        activity.record(deal, user, 'quotes', 'sold', f'Marked {plan.carrier} {plan.name} sold')
        advance(deal, user, 'sold', 'a plan was sold')
        if deal.client.relationship != 'existing':
            deal.client.relationship = 'existing'
            deal.client.save(update_fields=['relationship', 'updated_at'])
    else:
        activity.record(deal, user, 'quotes', 'sold', f'Un-sold {plan.carrier} {plan.name}')
        if deal.stage == 'sold' and not deal.plans.filter(sold=True).exists():
            deal.stage = 'proposal'
            deal.save(update_fields=['stage', 'updated_at'])
    return plan, deal


def _clean_enrollment(plan, raw):
    basis = lines.BY_KEY[plan.line]['rate_basis']
    keys = m.enrollment_keys(basis)
    if not isinstance(raw, dict):
        raise ValidationError({'enrollment': ['Enrollment must be an object.']})
    unknown = set(raw) - set(keys)
    if unknown:
        raise ValidationError(
            {'enrollment': [f'{plan.name} takes {", ".join(keys)}, not {", ".join(sorted(unknown))}']}
        )
    cleaned = {}
    for key in keys:
        value = raw.get(key, 0)
        try:
            number = float(str(value).replace(',', '') or 0)
        except ValueError as exc:
            raise ValidationError({'enrollment': [f'{key} takes a number, not "{value}"']}) from exc
        if number < 0 or (key != 'volume' and number != int(number)):
            raise ValidationError({'enrollment': [f'{key} takes a whole number of 0 or more']})
        cleaned[key] = int(number) if number == int(number) else number
    return cleaned


@transaction.atomic
def set_enrollment(user, deal, items):
    """items: [{id, enrollment: {...}, on}] — all-or-nothing."""
    plans = []
    for item in items:
        plan = locked(Plan, int(item.get('id', 0)))
        if plan.deal_id != deal.id:
            raise ValidationError({'plans': ['A plan is not on this deal.']})
        plan.enrollment = _clean_enrollment(plan, item.get('enrollment', {}))
        plan.enrollment_on = bool(item.get('on', True))
        plan.save(update_fields=['enrollment', 'enrollment_on', 'updated_at'])
        plans.append(plan)
    if plans:
        activity.record(
            deal, user, 'quotes', 'updated', 'Edited enrollment on', len(plans), 'quotes:enrollment', 'plan'
        )
    return plans


def _package_plans(deal, line, plan_ids):
    ids = {int(pid) for pid in plan_ids or []}
    plans = list(Plan.objects.filter(deal=deal, line=line, id__in=ids))
    if len(plans) != len(ids):
        raise ValidationError({'plan_ids': ['Every plan must be on this deal and line.']})
    return plans


def _package_name(name):
    name = (name or '').strip()
    if not name:
        raise ValidationError({'name': ['Name the package.']})
    return name[:100]


@transaction.atomic
def create_package(user, deal, line, name, plan_ids):
    if line not in lines.BY_KEY:
        raise ValidationError({'line': ['Unknown line.']})
    plans = _package_plans(deal, line, plan_ids)
    last = Package.objects.filter(deal=deal, line=line).aggregate(top=Max('sort_order'))['top']
    try:
        with transaction.atomic():
            package = Package.objects.create(
                deal=deal,
                line=line,
                name=_package_name(name),
                created_by=user,
                sort_order=0 if last is None else last + 1,
            )
    except IntegrityError as exc:
        raise ValidationError({'name': ['A package with this name already exists on this line.']}) from exc
    package.plans.set(plans)
    activity.record(deal, user, 'quotes', 'created', f'Built the package {package.name}')
    return package


@transaction.atomic
def update_package(user, package_id, data):
    package = locked(Package, package_id)
    if 'name' in data:
        name = _package_name(data['name'])
        if Package.objects.filter(deal=package.deal, line=package.line, name=name).exclude(pk=package.pk).exists():
            raise ValidationError({'name': ['A package with this name already exists on this line.']})
        package.name = name
        package.save(update_fields=['name', 'updated_at'])
    if 'plan_ids' in data:
        package.plans.set(_package_plans(package.deal, package.line, data['plan_ids']))
    activity.record(package.deal, user, 'quotes', 'updated', f'Edited the package {package.name}')
    return package


@transaction.atomic
def delete_package(user, package_id):
    package = locked(Package, package_id)
    deal, name = package.deal, package.name
    package.delete()
    activity.record(deal, user, 'quotes', 'deleted', f'Deleted the package {name}')
