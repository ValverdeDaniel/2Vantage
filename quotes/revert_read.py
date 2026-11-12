"""↶ Undo this run (plan.md §10.5, O.3.2; D73): putting back what a used quote read wrote.

- `revert(row, user)` is `deals.activity.reverters['quote_read']`: Revert of the landing's own row (the Change history's
  ↶ Revert, and Undo through `undo`). Runs inside `deals.activity.revert`'s transaction, after the Deal lock; locks the
  row's plans (removed ones too) and every live plan on their lines, by id.
  - A plan the read made (its entry sets `plan.read_ref` from nothing) comes off, softly, as Remove does (F60), unless
    someone has worked on it since: starred, recommended, sold or packaged it, linked another plan to it, typed into
    it, or changed it in any way the log shows. Such a plan stays, and Undo names it.
  - A value the read wrote on a plan the deal had goes back to what it was, with the source it had (a read value goes
    back as read, with its file, from the job's record), checked against the stored "after": a value changed since,
    a plan sold since or removed since refuses the Undo with a sentence naming them (409), and "Undo anyway" (`force`)
    leaves those as they are and puts back the rest. The plans a new renewal passed go back to their places when no one
    has moved them since.
- `undo(user, deal, job, force)` is the job's ↶ Undo this run: every row of the landing (the counts, the plans and
  values, the lines added), newest first, in one transaction, so all of it goes back or none of it does. With
  `force`, a row of another owner that refuses is left as it is and said.
"""

from contextvars import ContextVar

from django.db import transaction
from django.db.models import Q

from ai.models import Job
from deals import activity, clock
from deals.models import Activity
from deals.values import apply as apply_values
from deals.values import source

from . import columns, fields
from .models import Package, Plan
from .selectors.state import replaced_ids
from .services import locks
from .services.batch import Batch
from .services.read_apply import AREA
from .services.read_plans import ORDER, READ_REF, label_of
from .services.removal import take_off

FORCE = ContextVar('quote_read_undo_force', default=False)  # "Undo anyway", for this transaction only
KEYS = (*columns.LINKS, 'plan.removed_at')
NOT_WORK = ('reverted', 'marked', *activity.ACCESS)  # a later row that is no one's work on the plan

REMOVED = 'A plan this read changed has been removed since, so the run cannot be undone.'
SOLD = '{names} {verb} marked sold since, so the run cannot be undone. Un-sell {it} first, or undo anyway.'


def _plan_id(target):
    kind, _, ref = target.partition(':')
    return int(ref) if kind == 'plan' and ref.isdigit() else None


def _made(entry):
    pair = entry['k'].get(READ_REF)
    return pair is not None and pair[0] is None


def _locked(deal_id, plan_ids):
    """{id: plan}: the row's plans and every live plan on their lines, locked by id, with links and packages."""
    line_keys = set(Plan.all_objects.filter(id__in=plan_ids).values_list('line', flat=True))
    live = Q(deal_id=deal_id, line__in=line_keys, removed_at__isnull=True)
    rows = list(Plan.all_objects.select_for_update().filter(Q(id__in=plan_ids) | live).order_by('id'))
    links = replaced_ids(from_plan_id__in=[plan.id for plan in rows])
    for plan in rows:
        plan.replaces_ids = sorted(links.get(plan.id, []))
    return {plan.id: plan for plan in rows}


def _record_of(row):
    """The job's `landed` record for this row: the source entries the landed values replaced, the landing's rows."""
    result = Job.objects.filter(activity_id=row.id).values_list('result', flat=True).first() or {}
    return result.get('landed') or {}


def _touched_since(row, plan_ids, own_rows):
    """The plans a later row of someone's work names (a rename, a move, a role, a star …)."""
    if not plan_ids:
        return set()
    touching = Q()
    for plan_id in plan_ids:
        touching |= Q(changes__contains=[{'t': f'plan:{plan_id}'}])
    later = (
        Activity.objects.filter(deal_id=row.deal_id, pk__gt=row.pk, reverted_at__isnull=True)
        .exclude(pk__in=own_rows)
        .exclude(action__in=NOT_WORK)
        .filter(touching)
        .values_list('changes', flat=True)
    )
    return {_plan_id(entry['t']) for changes in later for entry in changes} & set(plan_ids)


def _worked_on(plan, keys, everything, made, packaged, touched):
    if plan.starred or plan.recommended or plan.sold or plan.id in packaged or plan.id in touched:
        return True
    if any(
        other.removed_at is None
        and other.id not in made
        and (other.renews_id == plan.id or plan.id in other.replaces_ids)
        for other in everything.values()
    ):
        return True
    landed = {key: pair[1] for key, pair in keys.items() if key not in (READ_REF, ORDER)}
    return dict(plan.values) != landed  # typed into since


def _put_back(plan, keys, user, stored, force, changed):
    """Put back one plan's values and place, in memory; returns the diff written. Keys changed since go to `changed`
    (and are left as they are)."""
    values, diff = {}, {}
    for key, (before, after) in keys.items():
        if key == ORDER:
            if plan.sort_order == after:
                diff[key], plan.sort_order = [after, before], before
            continue
        if str(plan.values.get(key) or '') != str(after or ''):
            changed.append((plan, key))
            continue
        values[key] = before if before not in (None, '') else ''

    def make(key):
        entry = stored.get(key)
        return dict(entry) if isinstance(entry, dict) else source('typed', user)

    if force or not changed:
        diff.update(apply_values(plan.values, plan.sources, values, make))
    return diff


def revert(row, user):
    force = FORCE.get()
    record = _record_of(row)
    stored = record.get('sources') or {}
    plan_ids = {_plan_id(entry['t']) for entry in row.changes} - {None}
    everything = _locked(row.deal_id, plan_ids)
    made = {_plan_id(entry['t']) for entry in row.changes if _made(entry)}
    written, changed, saving = [], [], []
    for entry in row.changes:
        plan = everything.get(_plan_id(entry['t']))
        if _plan_id(entry['t']) in made:
            continue
        if plan is None or plan.removed_at is not None:
            if force:
                continue
            raise activity.Refused(REMOVED)
        if plan.sold and set(entry['k']) - {ORDER}:
            if force:
                continue
            raise activity.Refused(SOLD.format(names=label_of(plan), verb='was', it='it'))
        diff = _put_back(plan, entry['k'], user, stored.get(entry['t']) or {}, force, changed)
        if diff:
            saving.append(plan)
            written.append(activity.change(entry['t'], diff))
    if changed and not force:
        many = len({plan.id for plan, _key in changed}) > 1
        labels = [
            fields.BY_KEY.get(key, {}).get('label', key) + (f' on {label_of(plan)}' if many else '')
            for plan, key in changed
        ]
        raise activity.changed_since(labels, [key for _plan, key in changed])
    for plan in saving:
        plan.save(update_fields=['values', 'sources', 'sort_order', 'updated_at'])
    packaged = set(Package.plans.through.objects.filter(plan_id__in=made).values_list('plan_id', flat=True))
    touched = _touched_since(row, made, record.get('activity_ids') or [row.id])
    removing = [
        everything[plan_id]
        for entry in row.changes
        if (plan_id := _plan_id(entry['t'])) in made
        and plan_id in everything
        and everything[plan_id].removed_at is None
        and not _worked_on(everything[plan_id], entry['k'], everything, made, packaged, touched)
    ]
    if removing:
        live = {pid: plan for pid, plan in everything.items() if plan.removed_at is None}
        batch = Batch(live.values(), KEYS)
        take_off(live, removing, clock.now())
        _written, changes = batch.write()
        written += changes
    return written


@transaction.atomic
def undo(user, deal, job, force=False):
    """Revert every row of the job's landing, newest first. Returns {reverted, kept, skipped, at, by}."""
    locks.deal(deal.id)
    landed = (job.result or {}).get('landed') or {}
    ids = sorted(landed.get('activity_ids') or [], reverse=True)
    rows = {row.id: row for row in Activity.objects.filter(pk__in=ids, deal_id=deal.id)}
    reverted, skipped = [], []
    token = FORCE.set(bool(force))
    try:
        for row_id in ids:
            row = rows.get(row_id)
            if row is None or row.reverted_at is not None:
                continue
            try:
                with transaction.atomic():
                    reverted.append(activity.revert(row_id, user).id)
            except activity.Refused as exc:
                if not force or row.area == AREA:
                    raise
                skipped.append(exc.sentence)
    finally:
        FORCE.reset(token)
    stayed = Plan.objects.filter(deal_id=deal.id, id__in=landed.get('created') or []).order_by('sort_order', 'id')
    return {
        'reverted': reverted,
        'kept': [label_of(plan) for plan in stayed],
        'skipped': skipped,
        'at': clock.now().isoformat(),
        'by': getattr(user, 'id', None),
    }
