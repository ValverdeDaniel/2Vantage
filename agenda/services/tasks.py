"""The one writer of `Task` (I27–I34, I40; I.6 `services/tasks.py`): add, edit, tick and reopen, move, and a soft
delete. Each runs in one transaction, locks the Deal and then the task, records Activity (never the title or the
note) and returns only what changed; an unchanged write records nothing.

- `add_task(user, deal_id, title, due, note='', assigned_to=None, done=False)`: `done=True` is Review's "Log a call",
  a task done at once, so it lands in Done (I40). A lost or sold deal still takes one (I34).
- `update_task(user, task_id, **changes)`: any of title, due, note, assigned_to, done, and `move_note` beside a new
  date: Later on a task moves its date and keeps the optional note as a deal Note "Task moved to <day>: <note>", in
  the same transaction (I32). Ticking stamps who and when; reopening clears both (I31). Anyone may (I110).
- `delete_task(user, task_id)`: a soft delete for the creator or an admin (OQ93); its Activity row's Revert brings the
  task back.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from deals import clock
from deals.services import add_note

from .. import rules
from ..models import Task
from .common import lock_deal, record, task_target

NOT_YOURS = 'Only the person who added this task or an admin can delete it.'
VALUES = ('due', 'done', 'assigned_to')  # before and after in Activity; title and note are recorded as keys only
TEXT = ('title', 'note')


def clean_title(raw):
    title = str(raw if raw is not None else '').strip()
    if not title:
        raise ValidationError({'title': ['A task needs a title.']})
    if len(title) > rules.TITLE_MAX:
        raise ValidationError({'title': [f'Keep the title under {rules.TITLE_MAX} characters.']})
    return title


def clean_due(raw):
    day = rules.parse_day(raw) if raw not in (None, '') else None
    if day is None:
        raise ValidationError({'due': ['Pick the day it is due (YYYY-MM-DD).']})
    return day


def clean_note(raw, field='note'):
    note = str(raw if raw is not None else '').strip()
    if len(note) > rules.TASK_NOTE_MAX:
        raise ValidationError({field: [f'Keep the note under {rules.TASK_NOTE_MAX:,} characters.']})
    return note


def clean_assignee(raw):
    """None for the deal's owner (no one named), else an active user's id."""
    if raw in (None, '', 0, '0'):
        return None
    try:
        user_id = int(raw)
    except (TypeError, ValueError):
        raise ValidationError({'assigned_to': ['Name the person by their id.']}) from None
    if user_id <= 0 or not get_user_model().objects.filter(pk=user_id, is_active=True).exists():
        raise ValidationError({'assigned_to': ['That person cannot be given a task.']})
    return user_id


def clean_done(raw):
    if not isinstance(raw, bool):
        raise ValidationError({'done': ['done must be true or false.']})
    return raw


def _who(user):
    return user if getattr(user, 'is_authenticated', False) else None


def _state(task):
    return {
        'due': task.due.isoformat(),
        'done': task.done,
        'assigned_to': task.assigned_to_id,
        'deleted': task.deleted_at is not None,
        'title': task.title,
        'note': task.note,
    }


def _changes(task_id, before, after):
    diff = {key: [before[key], after[key]] for key in VALUES if key in after and before[key] != after[key]}
    texts = [key for key in TEXT if key in after and before[key] != after[key]]
    out = [{'t': task_target(task_id), 'k': diff}] if diff else []
    return out + ([{'t': task_target(task_id), 'k': texts}] if texts else [])


def _summary(diff_keys, after):
    if diff_keys == {'done'}:
        return ('Ticked', 'agenda:tick', 'task') if after['done'] else ('Reopened a task', '', '')
    if diff_keys == {'due'}:
        return (f'Moved a task to {rules.short_day(after["due"])}', '', '')
    if diff_keys == {'assigned_to'}:
        return ('Gave a task to someone else', '', '')
    return ('Edited a task', '', '')


@transaction.atomic
def add_task(user, deal_id, *, title, due, note='', assigned_to=None, done=False):
    title, due, note = clean_title(title), clean_due(due), clean_note(note)
    assigned_to, done = clean_assignee(assigned_to), clean_done(done)
    deal = lock_deal(deal_id)
    now = clock.now()
    task = Task.objects.create(
        deal=deal,
        title=title,
        due=due,
        note=note,
        assigned_to_id=assigned_to,
        done_at=now if done else None,
        done_by=_who(user) if done else None,
        created_by=_who(user),
        created_at=now,
        updated_at=now,
    )
    summary = 'Added a task, already done' if done else 'Added a task'
    record(deal, user, 'created', summary, [{'t': task_target(task.id), 'k': ['title']}])
    return task


def _locked(task_id):
    deal_id = Task.objects.values_list('deal_id', flat=True).get(pk=task_id)  # DoesNotExist: deleted or unknown
    deal = lock_deal(deal_id)
    return deal, Task.objects.select_for_update().get(pk=task_id)


def _clean(changes):
    cleaners = {'title': clean_title, 'due': clean_due, 'note': clean_note, 'assigned_to': clean_assignee,
                'done': clean_done}  # fmt: skip
    return {key: cleaners[key](value) for key, value in changes.items() if key in cleaners}


@transaction.atomic
def update_task(user, task_id, **changes):
    """Returns (task, {key: [before, after]} of the values that changed, without the title's or note's words)."""
    move_note = clean_note(changes.pop('move_note', ''), 'move_note')
    wanted = _clean(changes)
    deal, task = _locked(task_id)
    before = _state(task)
    after = {**{key: before[key] for key in wanted}, **wanted}
    if 'due' in after:
        after['due'] = after['due'].isoformat()
    changes_list = _changes(task.id, before, after)
    if not changes_list:
        return task, {}
    for key in ('title', 'note'):
        if key in wanted:
            setattr(task, key, wanted[key])
    if 'due' in wanted:
        task.due = wanted['due']
    if 'assigned_to' in wanted:
        task.assigned_to_id = wanted['assigned_to']
    if 'done' in wanted and wanted['done'] != before['done']:
        task.done_at, task.done_by = (clock.now(), _who(user)) if wanted['done'] else (None, None)
    task.updated_at = clock.now()
    task.save()
    diff = changes_list[0]['k'] if isinstance(changes_list[0]['k'], dict) else {}
    summary, coalesce, noun = _summary(set(diff), after)
    record(deal, user, 'updated', summary, changes_list, coalesce_key=coalesce, noun=noun)
    if 'due' in diff and move_note:
        add_note(user, deal.id, body=f'Task moved to {rules.short_day(task.due)}: {move_note}')
    return task, diff


def move_task(user, task_id, due, note=''):
    """Later on a task (I32): its date moves; the optional note is kept as a deal Note."""
    return update_task(user, task_id, due=due, move_note=note)


def can_delete(user, task):
    return bool(getattr(user, 'is_staff', False) or (task.created_by_id and task.created_by_id == user.id))


@transaction.atomic
def delete_task(user, task_id):
    """A soft delete (I33, OQ93). Returns the Activity row, whose Revert is the Undo."""
    deal, task = _locked(task_id)
    if not can_delete(user, task):
        raise PermissionDenied(NOT_YOURS)
    task.deleted_at, task.deleted_by = clock.now(), _who(user)
    task.save(update_fields=['deleted_at', 'deleted_by'])
    change = {'t': task_target(task.id), 'k': {'deleted': [False, True]}}
    return record(deal, user, 'removed', 'Deleted a task', [change])
