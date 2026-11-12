"""Saved board setups (plan.md §6.7, §7.8; F28, OQ7; the old AdvisorFilterSet views and advisor_filters.clean_write):
＋ Save current, Update, Delete, and the Revert of an Update.

A setup belongs to a person, not to a deal, so its Activity rows are firm rows: no deal, `subject` "saved_view:<id>",
area `saved_views`, with before and after of each column it changed. Every write cleans the whole body (the config
through `board.clean_config` for its view), locks the row it changes, writes nothing when nothing changed, and answers
the row. Another person's private setup does not exist for anyone else (404); a shared one is changed only by its
owner or an admin (403 with the sentence). A create or a delete is not reverted (Activity's NOT_REVERTIBLE): a deleted
setup is saved again with ＋ Save current.
"""

from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from deals import activity, lines

from .. import board
from ..models import SavedView
from ..selectors.saved_views import editable_by

AREA = 'saved_views'
COLUMNS = ('name', 'description', 'view', 'line', 'shared', 'config')
NAME_LIMIT = 80
DESCRIPTION_LIMIT = 200
NOT_FOUND = 'No saved setup with that id.'
THEIRS = 'This setup belongs to someone else — copy it with “Save current” instead.'
GONE = 'This setup has been deleted since, so this change cannot be reverted.'
VIEW_NAMES = dict(SavedView.VIEWS)
WORDS = {'name': 'Name', 'description': 'Description', 'view': 'View', 'line': 'Line', 'shared': 'Sharing',
         'config': 'Setup'}  # fmt: skip


def target(view_id):
    return f'saved_view:{view_id}'


def _text(data, key, limit, errors, required=False):
    raw = data.get(key)
    text = raw.strip() if isinstance(raw, str) else ''
    if raw is not None and not isinstance(raw, str):
        errors[key] = f'{WORDS[key]} takes text.'
    elif required and not text:
        errors[key] = 'Give this setup a name.'
    elif len(text) > limit:
        errors[key] = f'{WORDS[key]} takes at most {limit} characters.'
    return text


def clean_write(data, instance=None):
    """The columns a create (every column) or an update (the ones it names) writes, cleaned; 400 naming each refusal."""
    if not isinstance(data, dict):
        raise ValidationError({'detail': 'Send the setup as {name, description, view, line, shared, config}.'})
    errors, out = {}, {}
    if 'name' in data or instance is None:
        out['name'] = _text(data, 'name', NAME_LIMIT, errors, required=True)
    if 'description' in data:
        out['description'] = _text(data, 'description', DESCRIPTION_LIMIT, errors)
    view = data.get('view', instance.view if instance else SavedView.QUOTES)
    if view not in VIEW_NAMES or view not in board.CLEANERS:
        errors['view'] = f'There are no saved setups for "{view}" yet.'
    else:
        out['view'] = view
    if 'line' in data or instance is None:
        line = data.get('line') or ''
        if line and line not in lines.BY_KEY:
            errors['line'] = f'"{line}" is not a line of coverage.'
        out['line'] = line
    if 'shared' in data:
        if not isinstance(data['shared'], bool):
            errors['shared'] = 'Sharing is on or off (true or false).'
        out['shared'] = data['shared'] is True
    if 'view' in out and ('config' in data or instance is None or instance.view != view):
        raw = data.get('config', instance.config if instance else {})
        try:
            out['config'] = board.clean_config(raw, view)
        except board.ConfigError as exc:
            errors['config'] = exc.errors
    if errors:
        raise ValidationError(errors)
    return out


def _name_taken(owner_id, view, name, exclude=None):
    return SavedView.objects.filter(owner_id=owner_id, view=view, name=name).exclude(pk=exclude).exists()


def _check_name(owner_id, fields, exclude=None):
    if _name_taken(owner_id, fields['view'], fields['name'], exclude):
        raise ValidationError({'name': f'You already have a setup called “{fields["name"]}”.'})


def _locked(user, view_id):
    """The setup, locked, when `user` may see it; 404 otherwise (another person's private setup included)."""
    row = SavedView.objects.select_for_update().filter(Q(shared=True) | Q(owner=user), pk=view_id).first()
    if row is None:
        raise NotFound(NOT_FOUND)
    return row


def create(user, data):
    """＋ Save current: a new setup of `user`'s, private unless shared."""
    fields = clean_write(data)
    with transaction.atomic():
        _check_name(user.id, fields)
        row = SavedView.objects.create(owner=user, **fields)
        diff = {key: [None, getattr(row, key)] for key in COLUMNS}
        activity.record(
            None,
            user,
            AREA,
            'created',
            f'Saved the board setup “{row.name}”',
            changes=[activity.change(target(row.id), diff)],
            subject=target(row.id),
        )
    return row


def update(user, view_id, data):
    """Update: the columns the body names. → (row, Activity row or None when nothing changed)."""
    with transaction.atomic():
        row = _locked(user, view_id)
        if not editable_by(row, user):
            raise PermissionDenied(THEIRS)
        fields = clean_write(data, row)
        diff = {key: [getattr(row, key), value] for key, value in fields.items() if getattr(row, key) != value}
        if not diff:
            return row, None
        if 'name' in diff or 'view' in diff:
            _check_name(row.owner_id, {'name': row.name, 'view': row.view, **fields}, exclude=row.id)
        for key, (_, value) in diff.items():
            setattr(row, key, value)
        row.save(update_fields=[*diff, 'updated_at'])
        entry = activity.record(
            None,
            user,
            AREA,
            'changed',
            f'Updated the board setup “{row.name}”',
            changes=[activity.change(target(row.id), diff)],
            subject=target(row.id),
        )
    return row, entry


def delete(user, view_id):
    with transaction.atomic():
        row = _locked(user, view_id)
        if not editable_by(row, user):
            raise PermissionDenied(THEIRS)
        diff = {key: [getattr(row, key), None] for key in COLUMNS}
        activity.record(
            None,
            user,
            AREA,
            'deleted',
            f'Deleted the board setup “{row.name}”',
            changes=[activity.change(target(row.id), diff)],
            subject=target(row.id),
        )
        row.delete()


def revert(entry, user):
    """`deals.activity.reverters['saved_views']`: an Update's earlier values back, refused after a later write."""
    (change,) = entry.changes
    view_id = int(change['t'].partition(':')[2])
    row = SavedView.objects.select_for_update().filter(pk=view_id).first()
    if row is None:
        raise activity.Refused(GONE)
    later = activity.later_keys(entry)
    if later:
        raise activity.changed_since([WORDS[key] for _, key in sorted(later)], [key for _, key in sorted(later)])
    diff = {key: [getattr(row, key), before] for key, (before, _) in change['k'].items() if getattr(row, key) != before}
    after = {'name': row.name, 'view': row.view, **{key: pair[1] for key, pair in diff.items()}}
    if ('name' in diff or 'view' in diff) and _name_taken(row.owner_id, after['view'], after['name'], row.id):
        raise activity.Refused(f'Another setup is called “{after["name"]}” now, so this change cannot be reverted.')
    for key, (_, value) in diff.items():
        setattr(row, key, value)
    if diff:
        row.save(update_fields=[*diff, 'updated_at'])
    return [activity.change(target(row.id), diff)]
