"""Every write to plans (plan.md §5.4, §7.7). Marks (star, recommend, sold, enrollment) and packages: marks.py."""

from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from deals import activity, lines
from deals.values import apply as apply_values
from deals.values import locked, source

from . import fields
from . import values as cleaning
from .models import Plan

ROLES = {'current', 'renewal', 'alternate'}


def clean_values(line, raw_values):
    """{key: raw} → {key: cleaned}; all-or-nothing. Unknown keys and keys of another line are refused."""
    if not isinstance(raw_values, dict):
        raise ValidationError({'values': ['Values must be an object of field keys.']})
    allowed = set(fields.keys_for(line))
    cleaned, errors = {}, {}
    for key, raw in raw_values.items():
        if key not in allowed:
            errors[key] = f'"{key}" is not a field of this line'
            continue
        value, error = cleaning.clean(key, raw)
        if error:
            errors[key] = error
        else:
            cleaned[key] = value
    if errors:
        raise ValidationError({'values': errors})
    return cleaned


def _current_plans(deal, line, ids):
    ids = [int(pid) for pid in ids or []]
    found = list(Plan.objects.filter(deal=deal, line=line, role='current', id__in=ids))
    if len(found) != len(set(ids)):
        raise ValidationError({'links': ['Links must name current plans on this deal and line.']})
    return found


def _links(deal, line, role, renews_id, replaces_ids, plan=None):
    """(renews plan or None, [replaced current plans]) after the §5.4 role rules."""
    if role == 'current':
        return None, []
    if role == 'renewal':
        if not renews_id:
            raise ValidationError({'renews_id': ['A renewal must name the current plan it renews.']})
        (renews,) = _current_plans(deal, line, [renews_id])
        taken = Plan.objects.filter(renews=renews).exclude(pk=getattr(plan, 'pk', None)).exists()
        if taken:
            raise ValidationError({'renews_id': [f'{renews.name} already has a renewal.']})
        return renews, []
    return None, _current_plans(deal, line, replaces_ids)


def _check_text(name, value, label):
    value = (value or '').strip()
    if not value:
        raise ValidationError({name: [f'{label} is required.']})
    return value[:200]


@transaction.atomic
def create_plan(
    user,
    deal,
    *,
    line,
    role,
    carrier,
    name,
    plan_number='',
    renews_id=None,
    replaces_ids=(),
    values=None,
    source_origin='typed',
    document=None,
    cells=None,
):
    if line not in lines.BY_KEY:
        raise ValidationError({'line': ['Unknown line.']})
    if role not in ROLES:
        raise ValidationError({'role': ['Role must be current, renewal or alternate.']})
    carrier, name = _check_text('carrier', carrier, 'Carrier'), _check_text('name', name, 'Plan name')
    renews, replaces = _links(deal, line, role, renews_id, replaces_ids)
    cleaned = clean_values(line, values or {})
    last = Plan.objects.filter(deal=deal, line=line, role=role).aggregate(top=Max('sort_order'))['top']
    plan = Plan(
        deal=deal,
        line=line,
        role=role,
        carrier=carrier,
        name=name,
        plan_number=(plan_number or '').strip()[:100],
        renews=renews,
        sort_order=0 if last is None else last + 1,
        source_document=document,
    )
    apply_values(
        plan.values,
        plan.sources,
        cleaned,
        lambda key: source(source_origin, user, doc=getattr(document, 'id', None), cell=(cells or {}).get(key)),
    )
    plan.save()
    plan.replaces.set(replaces)
    activity.record(deal, user, 'quotes', 'created', f'Added {carrier} {name} ({role})')
    return plan


@transaction.atomic
def update_plan(user, plan_id, data, source_origin='typed', document=None, cells=None):
    plan = locked(Plan, plan_id)
    for key, label in (('carrier', 'Carrier'), ('name', 'Plan name')):
        if key in data:
            setattr(plan, key, _check_text(key, data[key], label))
    if 'plan_number' in data:
        plan.plan_number = (data['plan_number'] or '').strip()[:100]
    for key in ('starred', 'notes'):
        if key in data:
            setattr(plan, key, bool(data[key]) if key == 'starred' else str(data[key] or ''))
    if {'role', 'renews_id', 'replaces_ids'} & set(data):
        role = data.get('role', plan.role)
        if role not in ROLES:
            raise ValidationError({'role': ['Role must be current, renewal or alternate.']})
        renews_id = data.get('renews_id', plan.renews_id if role == 'renewal' else None)
        replaces_ids = data.get('replaces_ids', [p.id for p in plan.replaces.all()] if role == 'alternate' else [])
        renews, replaces = _links(plan.deal, plan.line, role, renews_id, replaces_ids, plan)
        if role != 'current' and plan.role == 'current':
            plan.renewal_set.update(renews=None, role='alternate')
            plan.replaced_by.clear()
        if role == 'current':
            plan.recommended = False
        plan.role, plan.renews = role, renews
        plan.replaces.set(replaces)
    changed = []
    if 'values' in data:
        cleaned = clean_values(plan.line, data['values'])
        changed = apply_values(
            plan.values,
            plan.sources,
            cleaned,
            lambda key: source(source_origin, user, doc=getattr(document, 'id', None), cell=(cells or {}).get(key)),
        )
    plan.save()
    if changed:
        activity.record(plan.deal, user, 'quotes', 'updated', 'Edited', len(changed), 'quotes:values', 'plan value')
    elif set(data) - {'values'}:
        activity.record(plan.deal, user, 'quotes', 'updated', 'Edited', 1, 'quotes:plans', 'plan detail')
    return plan, changed


@transaction.atomic
def delete_plan(user, plan_id):
    plan = locked(Plan, plan_id)
    if plan.role == 'current':
        plan.renewal_set.update(renews=None, role='alternate')
    deal, label = plan.deal, f'{plan.carrier} {plan.name}'
    plan.delete()
    activity.record(deal, user, 'quotes', 'deleted', f'Removed {label}')


def _copy(user, original, role, renews=None, replaces=()):
    copied = {
        k: v for k, v in original.values.items() if fields.BY_KEY.get(k, {}).get('group') not in fields.PRICE_GROUPS
    }
    last = Plan.objects.filter(deal=original.deal, line=original.line, role=role).aggregate(top=Max('sort_order'))
    plan = Plan.objects.create(
        deal=original.deal,
        line=original.line,
        role=role,
        carrier=original.carrier,
        name=original.name,
        plan_number=original.plan_number,
        renews=renews,
        values=copied,
        sources={k: v for k, v in original.sources.items() if k in copied},
        sort_order=(last['top'] or 0) + 1,
    )
    plan.replaces.set(replaces)
    return plan


@transaction.atomic
def create_renewal(user, plan_id):
    current = locked(Plan, plan_id)
    if current.role != 'current':
        raise ValidationError({'detail': 'Only a current plan can be renewed.'})
    if current.renewal_set.exists():
        raise ValidationError({'detail': f'{current.name} already has a renewal.'})
    plan = _copy(user, current, 'renewal', renews=current)
    activity.record(current.deal, user, 'quotes', 'created', f'Created the renewal of {current.carrier} {current.name}')
    return plan


@transaction.atomic
def copy_as_alternate(user, plan_id):
    original = locked(Plan, plan_id)
    if original.role == 'current':
        replaces = [original]
    elif original.role == 'renewal':
        replaces = [original.renews] if original.renews else []
    else:
        replaces = list(original.replaces.all())
    plan = _copy(user, original, 'alternate', replaces=replaces)
    activity.record(
        original.deal, user, 'quotes', 'created', f'Copied {original.carrier} {original.name} as an alternate'
    )
    return plan


@transaction.atomic
def order(user, deal, line, role, plan_ids):
    plans = {p.id: p for p in Plan.objects.select_for_update().filter(deal=deal, line=line, role=role)}
    if set(map(int, plan_ids)) != set(plans):
        raise ValidationError({'plan_ids': ['List every plan of this role on the line, once.']})
    for index, pid in enumerate(plan_ids):
        Plan.objects.filter(pk=int(pid)).update(sort_order=index)
    activity.record(deal, user, 'quotes', 'updated', 'Reordered', 1, 'quotes:order', 'plan list')
