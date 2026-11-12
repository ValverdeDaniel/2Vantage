"""Typed enrollment per plan (plan.md §5.5; F85, F88). One door until slice 13 brings `LineEnrollment`.

All or nothing; locks the Deal, then the plans by id (never in the order the items arrive, which could deadlock);
an unchanged plan is not saved and records nothing (§3.7).
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, lines

from .. import math as m
from .. import signals
from . import locks


def _clean(plan, raw):
    keys = m.enrollment_keys(lines.BY_KEY[plan.line]['rate_basis'])
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


def _diff(plan, enrollment, on):
    """{"enrollment.EE": [before, after], "enrollment_on": [...]} for Activity (§3.7)."""
    tiers = list(plan.enrollment) + [key for key in enrollment if key not in plan.enrollment]
    diff = {
        f'enrollment.{key}': [plan.enrollment.get(key), enrollment.get(key)]
        for key in tiers
        if plan.enrollment.get(key) != enrollment.get(key)
    }
    if on != plan.enrollment_on:
        diff['enrollment_on'] = [plan.enrollment_on, on]
    return diff


def _ids(items):
    try:
        return [int(item.get('id')) for item in items]
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValidationError({'plans': ['Each row names a plan id.']}) from exc


@transaction.atomic
def set_enrollment(user, deal, items):
    """items: [{id, enrollment: {...}, on}]. Each returned plan carries `activity_id`, the row a Revert would undo
    (None when nothing changed)."""
    if not isinstance(items, list):
        raise ValidationError({'plans': ['Send a list of plans.']})
    deal = locks.deal(deal.id)
    plans = {plan.id: plan for plan in locks.plans(deal, _ids(items))}
    changes, changed = [], []
    for item, plan_id in zip(items, _ids(items), strict=True):
        plan = plans[plan_id]
        enrollment, on = _clean(plan, item.get('enrollment', {})), bool(item.get('on', True))
        diff = _diff(plan, enrollment, on)
        if diff:
            plan.enrollment, plan.enrollment_on = enrollment, on
            plan.save(update_fields=['enrollment', 'enrollment_on', 'updated_at'])
            changes.append(activity.change(f'plan:{plan.id}', diff))
            changed.append(plan)
    row = None
    if changes:
        row = activity.record(
            deal,
            user,
            'quotes',
            'updated',
            'Edited enrollment on',
            len(changes),
            'quotes:enrollment',
            'plan',
            changes=changes,
        )
        signals.changed(deal.id, [plan.line for plan in changed])
    result = [plans[plan_id] for plan_id in dict.fromkeys(_ids(items))]
    for plan in result:
        plan.activity_id = getattr(row, 'id', None)
    return result
