"""The deal's notes (plan.md §6.2, §7.3; A37, M73–M77, M.5 B12): add, edit, pin and delete, and their reverter.

Only the author or an admin edits or deletes a note. A delete is soft (`deleted_at`) and its Activity row, action
`removed`, reverts: that is the Undo. A note's words never reach Activity (they may name people, §3.8): an edit of the
body records the key alone, so that row cannot be reverted; pins, kinds and deletes keep before and after.
"""

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from .. import activity, clock
from ..models import Deal, Note

AREA = 'notes'
KINDS = dict(Note.KINDS)
NOT_YOURS = "Only the note's author or an admin can change it."
LABELS = {'body': 'The note', 'kind': 'Kind', 'pinned': 'Pinned', 'deleted': 'Deleted'}
# What adding each kind is called in the feed (a call, an email or a meeting is logged; M71).
ADDED = {
    'note': 'Added a note',
    'call': 'Logged a call',
    'email': 'Logged an email',
    'meeting': 'Logged a meeting',
    'internal': 'Added an internal note',
}


def target(note):
    return f'note:{note.id}'


def clean_body(raw):
    body = str(raw if raw is not None else '').strip()
    if not body:
        raise ValidationError({'body': ['A note needs some text.']})
    if len(body) > Note.MAX_BODY:
        raise ValidationError({'body': [f'Keep a note under {Note.MAX_BODY:,} characters.']})
    return body


def clean_kind(raw):
    if raw not in KINDS:
        raise ValidationError({'kind': [f'A note is one of: {", ".join(KINDS.values())}.']})
    return raw


def can_edit(user, note):
    return bool(getattr(user, 'is_staff', False) or (note.author_id and note.author_id == getattr(user, 'id', None)))


def _locked_note(user, note_id):
    """The live note, locked; 403 when `user` may not change it. Raises Note.DoesNotExist (deleted or unknown)."""
    note = Note.objects.select_for_update().get(pk=note_id)
    if not can_edit(user, note):
        raise PermissionDenied(NOT_YOURS)
    return note


@transaction.atomic
def add_note(user, deal_id, *, body, kind='note', pinned=False):
    """A new note on the deal (raises Deal.DoesNotExist). Its words are not recorded in Activity."""
    deal = Deal.objects.get(pk=deal_id)
    now = clock.now()
    note = Note.objects.create(
        deal=deal,
        body=clean_body(body),
        kind=clean_kind(kind),
        pinned=bool(pinned),
        author=user if getattr(user, 'is_authenticated', False) else None,
        created_at=now,
        updated_at=now,
    )
    activity.record(deal, user, AREA, 'created', ADDED[note.kind], changes=[activity.change(target(note), ['body'])])
    return note


@transaction.atomic
def update_note(user, note_id, **changes):
    """Body, kind and pinned (any subset, already cleaned). Returns (note, {key: [before, after]} without the body's
    words); an unchanged note writes nothing. Raises Note.DoesNotExist and PermissionDenied."""
    note = _locked_note(user, note_id)
    changed = {key: [getattr(note, key), changes[key]] for key in ('body', 'kind', 'pinned') if key in changes}
    changed = {key: pair for key, pair in changed.items() if pair[0] != pair[1]}
    if not changed:
        return note, {}
    for key, (_before, after) in changed.items():
        setattr(note, key, after)
    note.updated_at = clock.now()
    note.save(update_fields=[*changed, 'updated_at'])
    if set(changed) == {'pinned'}:
        summary = 'Pinned a note' if note.pinned else 'Unpinned a note'
    else:
        summary = 'Edited a note'
    keys_only = 'body' in changed
    activity.record(
        note.deal, user, AREA, 'updated', summary, changes=[activity.change(target(note), changed)], keys_only=keys_only
    )
    return note, {key: pair for key, pair in changed.items() if key != 'body'}


@transaction.atomic
def delete_note(user, note_id):
    """A soft delete (M77). Returns the Activity row, whose Revert brings the note back as it was, pin and all."""
    note = _locked_note(user, note_id)
    note.deleted_at = clock.now()
    note.save(update_fields=['deleted_at'])
    summary = 'Deleted a pinned note' if note.pinned else 'Deleted a note'
    change = activity.change(target(note), {'deleted': [False, True]})
    return activity.record(note.deal, user, AREA, 'removed', summary, changes=[change])


def revert(row, user):
    """`reverters['notes']`: undo a delete (or a pin or kind change), refused after a later write to the same key."""
    later = activity.later_keys(row)
    if later:
        raise activity.changed_since([LABELS.get(key, key) for _t, key in sorted(later)], [key for _t, key in later])
    written = []
    for entry in sorted(row.changes, key=lambda entry: entry['t']):
        note = Note.all_objects.select_for_update().filter(pk=int(entry['t'].removeprefix('note:'))).first()
        if note is None:
            raise activity.Refused('This note no longer exists, so the change cannot be reverted.')
        now = {'kind': note.kind, 'pinned': note.pinned, 'deleted': note.deleted_at is not None}
        stale = [key for key, (_before, after) in entry['k'].items() if now.get(key) != after]
        if stale:
            raise activity.changed_since([LABELS.get(key, key) for key in stale], stale)
        for key, (before, _after) in entry['k'].items():
            if key == 'deleted':
                note.deleted_at = clock.now() if before else None
            else:
                setattr(note, key, before)
        note.save(update_fields=['deleted_at' if key == 'deleted' else key for key in entry['k']])
        written.append(activity.change(entry['t'], {key: [a, b] for key, (b, a) in entry['k'].items()}))
    return written
