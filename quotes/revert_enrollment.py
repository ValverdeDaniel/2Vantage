"""Revert of a typed-enrollment save (plan.md §3.7, §5.5; F85, F88, F91): `deals.activity.reverters['enrollment']`.

Runs inside `deals.activity.revert`'s transaction, after the Deal lock. It locks the row's plans by id, then the
line's LineEnrollment; refuses with a sentence when a plan has been removed or sold since, or when a later write
changed one of its keys (a move to another line clears a plan's counts); then puts each key's "before" back: a plan's
counts and census plan names, the line figure, its switch, `typed_at` and `census_seen` (so undoing Keep lets the
census take over again).
"""

from datetime import datetime

from deals import activity

from .models import LineEnrollment, Plan
from .services.enrollment import AREA

REMOVED = 'A plan this change was made on has been removed, so the change cannot be reverted.'
WORDS = {
    'census_names': 'Census plan names',
    'on': 'Typed counts switch',
    'typed_at': 'When the counts were typed',
    'census_seen': 'The census imports the counts were typed after',
}


def _label(key):
    if key.startswith(('enrollment.', 'figure.')):
        return f'{key.partition(".")[2]} enrollment'
    return WORDS.get(key, key)


def _put_back_plan(plan, keys):
    diff, figures = {}, dict(plan.enrollment or {})
    for key, (before, _after) in keys.items():
        if key == 'census_names':
            diff[key] = [list(plan.census_names or []), before or []]
            plan.census_names = before or []
            continue
        tier = key.partition('.')[2]
        diff[key] = [figures.get(tier), before]
        if before is None:
            figures.pop(tier, None)
        else:
            figures[tier] = before
    plan.enrollment = figures
    return {key: pair for key, pair in diff.items() if pair[0] != pair[1]}


def _put_back_line(row, keys):
    diff, figures = {}, dict(row.enrollment or {})
    for key, (before, _after) in keys.items():
        if key == 'on':
            diff[key] = [row.on, before]
            row.on = before
        elif key == 'typed_at':
            diff[key] = [row.typed_at.isoformat() if row.typed_at else None, before]
            row.typed_at = datetime.fromisoformat(before) if before else None
        elif key == 'census_seen':
            diff[key] = [row.census_seen, before]
            row.census_seen = before
        else:
            tier = key.partition('.')[2]
            diff[key] = [figures.get(tier), before]
            if before is None:
                figures.pop(tier, None)
            else:
                figures[tier] = before
    row.enrollment = figures
    return {key: pair for key, pair in diff.items() if pair[0] != pair[1]}


def revert(entry, user):
    plan_ids = sorted(int(change['t'].partition(':')[2]) for change in entry.changes if change['t'].startswith('plan:'))
    line_keys = [change['t'].partition(':')[2] for change in entry.changes if change['t'].startswith(f'{AREA}:')]
    plans = {plan.id: plan for plan in Plan.all_objects.select_for_update().filter(id__in=plan_ids).order_by('id')}
    if set(plans) != set(plan_ids) or any(plan.removed_at for plan in plans.values()):
        raise activity.Refused(REMOVED)
    sold = [plan for plan in plans.values() if plan.sold]
    if sold:
        names = ' and '.join(f'{plan.carrier} {plan.name}' for plan in sold)
        raise activity.Refused(f'{names} {"is" if len(sold) == 1 else "are"} marked sold, so this cannot be reverted.')
    later = activity.later_keys(entry)
    if later:
        raise activity.changed_since([_label(key) for _, key in sorted(later)], [key for _, key in sorted(later)])
    rows = {
        row.line: row
        for row in LineEnrollment.objects.select_for_update().filter(deal_id=entry.deal_id, line__in=line_keys)
    }
    written = []
    for change in entry.changes:
        kind, _, ref = change['t'].partition(':')
        if kind == 'plan':
            plan = plans[int(ref)]
            diff = _put_back_plan(plan, change['k'])
            if diff:
                plan.save(update_fields=['enrollment', 'census_names', 'updated_at'])
        else:
            row = rows.get(ref) or LineEnrollment(deal_id=entry.deal_id, line=ref)
            diff = _put_back_line(row, change['k'])
            if diff:
                row.save()
        written.append(activity.change(change['t'], diff))
    return written
