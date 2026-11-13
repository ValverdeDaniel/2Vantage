"""`reverters['agenda']` (plan.md §3.7; I22, I33; Q.3 #1): puts a mark's or a task's earlier values back, through the
same rows the services write, under the Deal's lock (`deals.activity.revert` takes it first). Refused after a later
write to the same key, and when the row no longer stands as this entry left it.

- `mark:<step_key>` {kind, until, sig}: the earlier mark comes back (a hold, or a Done anyway with its signature), or
  the mark goes when there was none.
- `task:<id>` {due, done, assigned_to, deleted}: the earlier date, tick, person, or a deleted task restored.
"""

from deals import activity, clock

from .models import StepMark, Task

LABELS = {
    'kind': 'The mark',
    'until': 'The day it comes back',
    'sig': 'The step',
    'due': 'The date',
    'done': 'The tick',
    'assigned_to': 'Who it is for',
    'deleted': 'Deleted',
}


def _mark_state(deal_id, step_key):
    mark = StepMark.objects.select_for_update().filter(deal_id=deal_id, step_key=step_key).first()
    if mark is None:
        return None, {'kind': None, 'until': None, 'sig': ''}
    return mark, {'kind': mark.kind, 'until': mark.until.isoformat() if mark.until else None, 'sig': mark.sig}


def _put_mark(row, user, step_key, keys):
    mark, now = _mark_state(row.deal_id, step_key)
    stale = [key for key, (_before, after) in keys.items() if now.get(key) != after]
    if stale:
        raise activity.changed_since([LABELS.get(key, key) for key in stale], stale)
    wanted = {**now, **{key: before for key, (before, _after) in keys.items()}}
    if wanted['kind'] is None:
        if mark is not None:
            mark.delete()
    else:
        StepMark.objects.update_or_create(
            deal_id=row.deal_id,
            step_key=step_key,
            defaults={
                'kind': wanted['kind'],
                'until': wanted['until'],
                'sig': wanted['sig'] or '',
                'by': user if getattr(user, 'is_authenticated', False) else None,
                'at': clock.now(),
            },
        )


def _task_state(task):
    return {
        'due': task.due.isoformat(),
        'done': task.done_at is not None,
        'assigned_to': task.assigned_to_id,
        'deleted': task.deleted_at is not None,
    }


def _put_task(user, task_id, keys):
    task = Task.all_objects.select_for_update().filter(pk=task_id).first()
    if task is None:
        raise activity.Refused('This task no longer exists, so the change cannot be reverted.')
    now = _task_state(task)
    stale = [key for key, (_before, after) in keys.items() if now.get(key) != after]
    if stale:
        raise activity.changed_since([LABELS.get(key, key) for key in stale], stale)
    for key, (before, _after) in keys.items():
        if key == 'due':
            task.due = before
        elif key == 'done':
            task.done_at, task.done_by = (clock.now(), user) if before else (None, None)
        elif key == 'assigned_to':
            task.assigned_to_id = before
        elif key == 'deleted':
            task.deleted_at = clock.now() if before else None
            task.deleted_by = (user if before else None) if getattr(user, 'is_authenticated', False) else None
    task.updated_at = clock.now()
    task.save()


def revert(row, user):
    later = activity.later_keys(row)
    if later:
        raise activity.changed_since([LABELS.get(key, key) for _t, key in sorted(later)], [key for _t, key in later])
    written = []
    for entry in sorted(row.changes, key=lambda entry: entry['t']):
        kind, _, rest = entry['t'].partition(':')
        if kind == 'mark':
            _put_mark(row, user, rest, entry['k'])
        elif kind == 'task':
            _put_task(user, int(rest), entry['k'])
        else:
            raise activity.Refused(activity.NO_REVERTER)
        written.append(activity.change(entry['t'], {key: [a, b] for key, (b, a) in entry['k'].items()}))
    return written
