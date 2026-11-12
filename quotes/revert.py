"""Revert for quotes' Activity rows (plan.md §3.7, O.3.2; F.6 "Revert works per key"): plan values, typed enrollment,
a plan's own details, and the multi-row rules: stars and Clear shortlist, recommendations, roles and links, the order
and slot picks, removals (Restore, F60), moves to another line (F59) and merges (F142).

Registered as `deals.activity.reverters['quotes']` in QuotesConfig.ready(). Runs inside `deals.activity.revert`'s
transaction, after the Deal lock: it locks the change's plans (removed ones too) and every live plan on the lines they
are on or go back to, by id; refuses with a sentence (a sold plan, a plan removed since, a later write to the same key,
a package deleted since, or a line the change would now break); puts each key's "before" back in memory; checks the
lines' rules, then saves. Values go back through `values.apply`; a value that goes back to what the reader read gets
its read source back (`None` in `values.apply`), so ↗ still opens the file.
"""

from django.db.models import Q

from deals import activity, lines
from deals.values import apply as apply_values
from deals.values import source

from . import columns, fields, presented
from .models import Package, Plan
from .selectors.state import line_data, replaced_ids
from .services.batch import write_replaces

ENROLLMENT = 'enrollment.'
DETAIL_WORDS = {
    'plan_number': 'Plan number',
    'replaces_ids': 'Replaces',
    'renews_id': 'Renews',
    'sort_order': 'Order',
    'removed_at': 'Removal',
    'package_ids': 'Packages',
    'source_document': 'File',
}
MANY = (columns.REPLACES, columns.PACKAGES)

REMOVED = 'A plan this change was made on has been removed, so the change cannot be reverted.'
LINKS = "A role or link change cannot be reverted here. Change the plan's role or links back instead."
BROKEN = 'This change cannot be reverted: {why}'
PACKAGE_GONE = 'A package one of these plans was in has been deleted, so this change cannot be reverted.'


def _plan_id(target):
    kind, _, plan_id = target.partition(':')
    return int(plan_id) if kind == 'plan' and plan_id.isdigit() else None


def _label(key):
    if key in fields.BY_KEY:
        return fields.BY_KEY[key]['label']
    if key.startswith(ENROLLMENT):
        return f'{key.removeprefix(ENROLLMENT)} enrollment'
    if key == 'enrollment_on':
        return 'Typed enrollment'
    column = key.removeprefix('plan.')
    return DETAIL_WORDS.get(column, column.replace('_', ' ').capitalize())


def _current(plan, key):
    if key.startswith(ENROLLMENT):
        return plan.enrollment.get(key.removeprefix(ENROLLMENT))
    if key == 'enrollment_on':
        return plan.enrollment_on
    if key in MANY or key in columns.COLUMNS:
        return columns.read(plan, key, plan.replaces_ids)
    return plan.values.get(key)


def _value_back(plan, key, before):
    if before is None:
        return ''  # the write added the value: clear it
    if plan.sources.get(key, {}).get('read_value') == before:
        return None  # back to what was read, with its source
    return before


def _put_back(plan, keys, user):
    diff, values, enrollment = {}, {}, dict(plan.enrollment)
    for key, (before, _after) in keys.items():
        if key.startswith(ENROLLMENT):
            tier = key.removeprefix(ENROLLMENT)
            diff[key] = [plan.enrollment.get(tier), before]
            if before is None:
                enrollment.pop(tier, None)
            else:
                enrollment[tier] = before
        elif key == 'enrollment_on':
            diff[key] = [plan.enrollment_on, before]
            plan.enrollment_on = before
        elif key == columns.REPLACES:
            diff[key] = [sorted(plan.replaces_ids), sorted(before or [])]
            plan.replaces_ids = sorted(before or [])
        elif key == columns.PACKAGES:
            diff[key] = [sorted(plan.package_ids), sorted(before or [])]
            plan.package_ids = sorted(before or [])
        elif key in columns.COLUMNS:
            diff[key] = [columns.read(plan, key), before]
            columns.write(plan, key, before)
        else:
            values[key] = _value_back(plan, key, before)
    plan.enrollment = enrollment
    diff.update(apply_values(plan.values, plan.sources, values, source('typed', user)))
    return {key: pair for key, pair in diff.items() if pair[0] != pair[1]}


def _broken(line_key, rows, held_before):
    """Why the line's live plans, as the revert would leave them, break §5.4's rules; None when they hold."""
    renewed = {}
    for plan in rows.values():
        if plan.role == 'current' and (plan.starred or plan.renews_id or plan.replaces_ids):
            return f'{plan.carrier} {plan.name} is a current plan now, and a current plan takes no star or link.'
        if plan.role == 'renewal':
            current = rows.get(plan.renews_id)
            if current is None or current.role != 'current':
                return f'{plan.carrier} {plan.name} would renew a plan that is no longer current.'
            if plan.renews_id in renewed:
                return f'{current.carrier} {current.name} already has a renewal.'
            renewed[plan.renews_id] = plan.id
        if any(rows.get(pid) is None or rows[pid].role != 'current' for pid in plan.replaces_ids):
            return f'{plan.carrier} {plan.name} would replace a plan that is no longer current.'
    data = line_data(line_key, list(rows.values()))
    if presented.has_stars(data) and len(presented.held(data)) > max(presented.MAX_COLUMNS, held_before):
        return f'the {lines.label(line_key)} proposal would hold more than {presented.MAX_COLUMNS} plans.'
    return None


def _locked(row, plan_ids):
    """{plan id: plan}: the change's own plans, removed ones included, and every live plan on the lines they are on or
    go back to, locked by id in one statement, each with `replaces_ids` and `package_ids`."""
    back = {pair[0] for entry in row.changes for key, pair in entry['k'].items() if key == 'plan.line'}
    line_keys = set(Plan.all_objects.filter(id__in=plan_ids).values_list('line', flat=True)) | back
    live = Q(deal_id=row.deal_id, line__in=line_keys, removed_at__isnull=True)
    rows = list(Plan.all_objects.select_for_update().filter(Q(id__in=plan_ids) | live).order_by('id'))
    links = replaced_ids(from_plan_id__in=[plan.id for plan in rows])
    packages = {}
    for plan_id, package_id in Package.plans.through.objects.filter(plan_id__in=plan_ids).values_list(
        'plan_id', 'package_id'
    ):
        packages.setdefault(plan_id, []).append(package_id)
    for plan in rows:
        plan.replaces_ids = sorted(links.get(plan.id, []))
        plan.package_ids = sorted(packages.get(plan.id, []))
    return {plan.id: plan for plan in rows}


def _restores(entry):
    removal = entry['k'].get('plan.removed_at')
    return removal is not None and removal[0] is None


def _refuse_later(row, plans, keys):
    later = activity.later_keys(row) | {
        (entry['t'], key)
        for entry in row.changes
        for key, (_before, after) in entry['k'].items()
        if _current(plans[_plan_id(entry['t'])], key) != after
    }
    if later:
        many = len({t for t, _ in keys}) > 1
        labels = [
            _label(key) + (f' on {plans[_plan_id(t)].carrier} {plans[_plan_id(t)].name}' if many else '')
            for t, key in keys
            if (t, key) in later
        ]
        raise activity.changed_since(labels, [key for t, key in keys if (t, key) in later])


def _live_on(everything, line_key):
    return {p.id: p for p in everything.values() if p.line == line_key and p.removed_at is None}


def _check_packages(deal_id, plans, written):
    for target, diff in written:
        if columns.PACKAGES in diff:
            plan = plans[_plan_id(target)]
            found = Package.objects.filter(id__in=plan.package_ids, deal_id=deal_id, line=plan.line).count()
            if found != len(plan.package_ids):
                raise activity.Refused(PACKAGE_GONE)


def _renews_last(item):
    renews = item[1].get('plan.renews_id')
    return renews is not None and renews[1] is not None


def revert(row, user):
    ids = {_plan_id(entry['t']) for entry in row.changes}
    if None in ids:
        raise activity.Refused(activity.NO_REVERTER)
    everything = _locked(row, ids)
    restoring = {_plan_id(entry['t']) for entry in row.changes if _restores(entry)}
    if not ids <= set(everything) or any(everything[pid].removed_at and pid not in restoring for pid in ids):
        raise activity.Refused(REMOVED)
    plans = {plan_id: everything[plan_id] for plan_id in ids}
    sold = [plan for plan in plans.values() if plan.sold]
    if sold:
        names = ' and '.join(f'{plan.carrier} {plan.name}' for plan in sold)
        one = len(sold) == 1
        raise activity.Refused(
            f'{names} {"is" if one else "are"} marked sold, so this change cannot be reverted. '
            f'Un-sell {"it" if one else "them"} first.'
        )
    keys = [(entry['t'], key) for entry in row.changes for key in entry['k']]
    if any(key.startswith('plan.') and key not in columns.COLUMNS and key not in MANY for _, key in keys):
        raise activity.Refused(LINKS)
    _refuse_later(row, plans, keys)
    line_keys = {plan.line for plan in everything.values()}
    held = {key: len(presented.held(line_data(key, list(_live_on(everything, key).values())))) for key in line_keys}
    written = [(entry['t'], _put_back(plans[_plan_id(entry['t'])], entry['k'], user)) for entry in row.changes]
    for line_key in sorted(line_keys | {plan.line for plan in plans.values()}):
        why = _broken(line_key, _live_on(everything, line_key), held.get(line_key, 0))
        if why:
            raise activity.Refused(BROKEN.format(why=why))
    _check_packages(row.deal_id, plans, written)
    # A plan that stops renewing is saved first, so one renewal per current plan holds after every statement.
    for target, diff in sorted(written, key=_renews_last):
        plan = plans[_plan_id(target)]
        if diff:
            plan.save()
            if columns.REPLACES in diff:
                write_replaces(plan)
            if columns.PACKAGES in diff:
                plan.packages.set(plan.package_ids)
    return [activity.change(target, diff) for target, diff in written]
