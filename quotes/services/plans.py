"""Creating and editing plans (plan.md §5.4, §7.8; F71, F141).

- `create_plan`: under the Deal lock, last on its line (a renewal first in its plan's group, F120).
- `update_plan` (PATCH): only the carrier, name, plan number, client name, notes, bundling (F78) and values; roles,
  links, stars, recommendations, order and the sale each have their own door (F71, J14). `expect` holds the values
  the person last saw: a stored value that differs refuses the whole write (409 naming the keys; J74, O.6 #33).
  Locks only its plan.
- Copies (Create renewal, Duplicate) are `copies.py`; removing plans `removal.py`; moving them `moves.py`; merging
  two into one `merge.py`.
Values only ever change through `deals.values.apply`; every write records Activity with before and after.
"""

from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from deals import activity, lines
from deals.values import apply as apply_values
from deals.values import locked, source

from .. import columns, fields, signals
from .. import values as cleaning
from ..models import Plan
from . import locks
from .roles import check_role, lead_renewals, links_for

DETAILS = ('carrier', 'name', 'plan_number', 'client_name', 'notes')
BUNDLING = 'bundling'  # whether the quoted rates already include the bundling discount (F78; slice 35)
PATCHABLE = {*DETAILS, BUNDLING, 'values', 'expect'}
STALE = '{names} changed since you last saw {it}, so nothing was saved. Reload to see the new {value}.'


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


def _text(name, value, label, limit=200, required=True):
    value = (value or '').strip() if isinstance(value, str) or value is None else str(value).strip()
    if required and not value:
        raise ValidationError({name: [f'{label} is required.']})
    return value[:limit]


def next_number(deal, line):
    """The number after every plan the line has had, removed ones included, so a restored plan keeps its place."""
    top = Plan.all_objects.filter(deal=deal, line=line).aggregate(top=Max('sort_order'))['top']
    return 0 if top is None else top + 1


def placed(deal, plan):
    """Activity changes of the plans a new renewal passes when it takes the lead of its plan's group."""
    if plan.role != 'renewal':
        return []
    rows, _data = locks.line(deal, plan.line)
    before = {pid: row.sort_order for pid, row in rows.items()}
    lead_renewals(plan.line, rows, [rows[plan.id]])
    moved = [row for pid, row in rows.items() if row.sort_order != before[pid]]
    Plan.objects.bulk_update(moved, ['sort_order'])
    return [
        activity.change(f'plan:{row.id}', {'plan.sort_order': [before[row.id], row.sort_order]})
        for row in moved
        if row.id != plan.id
    ]


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
    check_role(role)
    carrier, name = _text('carrier', carrier, 'Carrier'), _text('name', name, 'Plan name')
    deal = locks.deal(deal.id)
    rows, _data = locks.line(deal, line)
    renews, replaces = links_for(rows, role, renews_id, replaces_ids)
    cleaned = clean_values(line, values or {})
    plan = Plan(
        deal=deal,
        line=line,
        role=role,
        carrier=carrier,
        name=name,
        plan_number=_text('plan_number', plan_number, 'Plan number', 100, required=False),
        renews_id=renews,
        sort_order=next_number(deal, line),
        source_document=document,
    )
    diff = apply_values(
        plan.values,
        plan.sources,
        cleaned,
        lambda key: source(source_origin, user, doc=getattr(document, 'id', None), cell=(cells or {}).get(key)),
    )
    plan.save()
    plan.replaces.set(replaces)
    plan.replaces_ids = sorted(replaces)
    placed_changes = placed(deal, plan)
    summary = f'Added {carrier} {name} ({role})'
    changes = [activity.change(f'plan:{plan.id}', diff), *placed_changes]
    activity.record(deal, user, 'quotes', 'created', summary, changes=changes)
    signals.changed(deal.id, [line])
    return plan


def _stale(plan, expect):
    """The keys whose stored value is no longer what the person saw."""
    if not isinstance(expect, dict):
        raise ValidationError({'expect': ['Expect must be an object of field keys.']})
    return [key for key, seen in expect.items() if (plan.values.get(key) or '') != (seen or '')]


def _refuse_stale(keys):
    labels = [fields.BY_KEY[key]['label'] if key in fields.BY_KEY else key for key in keys]
    names = labels[0] if len(labels) == 1 else ', '.join(labels[:-1]) + ' and ' + labels[-1]
    one = len(labels) == 1
    text = STALE.format(names=names, it='it' if one else 'them', value='value' if one else 'values')
    raise activity.Refused(text, keys)


@transaction.atomic
def update_plan(user, plan_id, data, source_origin='typed', document=None, cells=None):
    """Returns (plan, [changed value keys]); `plan.activity_id` is the Activity row a Revert would undo, or None.
    Keys outside the PATCH list (role, links, stars, the sale) are ignored (F71)."""
    plan = locked(Plan, plan_id)
    data = {key: value for key, value in data.items() if key in PATCHABLE}
    if 'expect' in data:
        stale = _stale(plan, data['expect'])
        if stale:
            _refuse_stale(stale)
    keys = [f'plan.{key}' for key in (*DETAILS, BUNDLING)]
    before = columns.snapshot(plan, keys)
    for key, label in (('carrier', 'Carrier'), ('name', 'Plan name')):
        if key in data:
            setattr(plan, key, _text(key, data[key], label))
    if 'plan_number' in data:
        plan.plan_number = _text('plan_number', data['plan_number'], 'Plan number', 100, required=False)
    if 'client_name' in data:
        plan.client_name = _text('client_name', data['client_name'], 'Name on client documents', required=False)
    if 'notes' in data:
        plan.notes = str(data['notes'] or '')
    if BUNDLING in data:
        if data[BUNDLING] not in dict(Plan.BUNDLING):
            raise ValidationError({BUNDLING: ['Bundling is blank, "unbundled" or "included".']})
        plan.bundling = data[BUNDLING]
    changed = {}
    if 'values' in data:
        cleaned = clean_values(plan.line, data['values'])
        changed = apply_values(
            plan.values,
            plan.sources,
            cleaned,
            lambda key: source(source_origin, user, doc=getattr(document, 'id', None), cell=(cells or {}).get(key)),
        )
    diff = {**changed, **columns.diff(before, columns.snapshot(plan, keys))}
    plan.activity_id = None
    if diff:  # an unchanged write saves nothing and records nothing (§3.7)
        plan.save()
        if source_origin == 'import':  # one import's edits merge with each other, never with typed ones
            summary, coalesce, noun = 'Imported', f'quotes:import:{getattr(document, "id", "")}', 'plan value'
        elif changed:
            summary, coalesce, noun = 'Edited', 'quotes:values', 'plan value'
        else:
            summary, coalesce, noun = 'Edited', 'quotes:plans', 'plan detail'
        row = activity.record(
            plan.deal,
            user,
            'quotes',
            'updated',
            summary,
            len(diff),
            coalesce,
            noun,
            changes=[activity.change(f'plan:{plan.id}', diff)],
        )
        plan.activity_id = row.id
        signals.changed(plan.deal_id, [plan.line])
    return plan, list(changed)
