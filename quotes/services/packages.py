"""Member-built packages (plan.md §5.5, §6.7): a named set of plans on one line, totalled on read by `package()`.

Each write records Activity with the package's name and plans before and after; an unchanged edit writes nothing.
Packages are not reverted from the Activity drawer (their rows refuse with the owner's sentence).
"""

from django.db import IntegrityError, transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from deals import activity, lines
from deals.values import locked

from ..models import Package, Plan


def _plans(deal, line, plan_ids):
    try:
        ids = {int(pid) for pid in plan_ids or []}
    except (TypeError, ValueError) as exc:
        raise ValidationError({'plan_ids': ['Plan ids are numbers.']}) from exc
    plans = list(Plan.objects.filter(deal=deal, line=line, id__in=ids))
    if len(plans) != len(ids):
        raise ValidationError({'plan_ids': ['Every plan must be on this deal and line.']})
    return plans


def _name(name):
    name = (name or '').strip()
    if not name:
        raise ValidationError({'name': ['Name the package.']})
    return name[:100]


def _state(package):
    return {'name': package.name, 'plan_ids': sorted(package.plans.values_list('id', flat=True))}


def _record(deal, user, action, summary, before, after, package_id):
    diff = {key: [before.get(key), after.get(key)] for key in ('name', 'plan_ids') if before.get(key) != after.get(key)}
    changes = [activity.change(f'package:{package_id}', diff)] if diff else None
    activity.record(deal, user, 'quotes', action, summary, changes=changes, revertible=False)


@transaction.atomic
def create_package(user, deal, line, name, plan_ids):
    if line not in lines.BY_KEY:
        raise ValidationError({'line': ['Unknown line.']})
    plans = _plans(deal, line, plan_ids)
    last = Package.objects.filter(deal=deal, line=line).aggregate(top=Max('sort_order'))['top']
    try:
        with transaction.atomic():
            package = Package.objects.create(
                deal=deal, line=line, name=_name(name), created_by=user, sort_order=0 if last is None else last + 1
            )
    except IntegrityError as exc:
        raise ValidationError({'name': ['A package with this name already exists on this line.']}) from exc
    package.plans.set(plans)
    _record(deal, user, 'created', f'Built the package {package.name}', {}, _state(package), package.id)
    return package


@transaction.atomic
def update_package(user, package_id, data):
    package = locked(Package, package_id)
    before = _state(package)
    if 'name' in data:
        name = _name(data['name'])
        if Package.objects.filter(deal=package.deal, line=package.line, name=name).exclude(pk=package.pk).exists():
            raise ValidationError({'name': ['A package with this name already exists on this line.']})
        if name != package.name:
            package.name = name
            package.save(update_fields=['name', 'updated_at'])
    if 'plan_ids' in data:
        plans = _plans(package.deal, package.line, data['plan_ids'])
        if sorted(p.id for p in plans) != before['plan_ids']:
            package.plans.set(plans)
    after = _state(package)
    if after != before:
        _record(package.deal, user, 'updated', f'Edited the package {package.name}', before, after, package.id)
    return package


@transaction.atomic
def delete_package(user, package_id):
    package = locked(Package, package_id)
    deal, before, pid = package.deal, _state(package), package.id
    package.delete()
    _record(deal, user, 'deleted', f'Deleted the package {before["name"]}', before, {}, pid)
