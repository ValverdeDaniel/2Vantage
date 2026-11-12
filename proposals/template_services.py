"""Saved parts of a proposal, write side (plan.md §6.11, §7.12; J68, OQ7; old Vantage 891f1b3
`proposal_templates.clean_write` and the template views): ＋ Save as template, Update, Delete, and the Revert of an
Update. Applying one is the builder's own PATCH of the deal (`services.set_config`), never a write here.

A template belongs to a person, not to a deal, so its Activity rows are firm rows: no deal, `subject`
"proposal_template:<id>", area `proposal_templates`, with before and after of each column it changed. Every write
cleans the whole body (the config through `template_store.clean_config` for its kind), locks the row it changes,
writes nothing when nothing changed, and answers the row. Another person's private template does not exist for anyone
else (404); a shared one is changed only by its owner or an admin (403 with the sentence). Create and delete are not
reverted (Activity's NOT_REVERTIBLE).
"""

from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from deals import activity, lines

from . import template_store
from .models import ProposalTemplate

AREA = 'proposal_templates'
COLUMNS = ('name', 'description', 'kind', 'line', 'shared', 'config')
NAME_LIMIT = 80
DESCRIPTION_LIMIT = 200
KINDS = dict(ProposalTemplate.KINDS)
NOT_FOUND = 'No saved template with that id.'
THEIRS = 'This template belongs to someone else — “Save as template” to make your own copy.'
GONE = 'This template has been deleted since, so this change cannot be reverted.'
WORDS = {'name': 'Name', 'description': 'Description', 'kind': 'Kind', 'line': 'Line', 'shared': 'Sharing',
         'config': 'Template'}  # fmt: skip


def target(template_id):
    return f'proposal_template:{template_id}'


def _text(data, key, limit, errors, required=False):
    raw = data.get(key)
    text = raw.strip() if isinstance(raw, str) else ''
    if raw is not None and not isinstance(raw, str):
        errors[key] = f'{WORDS[key]} takes text.'
    elif required and not text:
        errors[key] = 'Give this template a name.'
    elif len(text) > limit:
        errors[key] = f'{WORDS[key]} takes at most {limit} characters.'
    return text


def clean_write(data, instance=None):
    """The columns a create (every column) or an update (the ones it names) writes, cleaned; 400 naming each refusal.
    The config is cleaned again whenever the kind or the line changes, so no other kind's paths stay behind."""
    if not isinstance(data, dict):
        raise ValidationError({'detail': 'Send the template as {name, description, kind, line, shared, config}.'})
    errors, out = {}, {}
    if 'name' in data or instance is None:
        out['name'] = _text(data, 'name', NAME_LIMIT, errors, required=True)
    if 'description' in data:
        out['description'] = _text(data, 'description', DESCRIPTION_LIMIT, errors)
    kind = data.get('kind', instance.kind if instance else None)
    if kind not in KINDS:
        errors['kind'] = f'Templates are of these kinds: {", ".join(KINDS)}.'
    else:
        out['kind'] = kind
    line = data.get('line', instance.line if instance else '') or ''
    if line and line not in lines.BY_KEY:
        errors['line'] = f'"{line}" is not a line of coverage.'
    else:
        out['line'] = line
    if 'shared' in data:
        if not isinstance(data['shared'], bool):
            errors['shared'] = 'Sharing is on or off (true or false).'
        out['shared'] = data['shared'] is True
    moved = instance is not None and (instance.kind != out.get('kind') or instance.line != out.get('line'))
    if 'kind' in out and 'line' in out and ('config' in data or instance is None or moved):
        raw = data.get('config', instance.config if instance else {})
        out['config'] = template_store.clean_config(out['kind'], raw, out['line'])
    if errors:
        raise ValidationError(errors)
    return out


def _name_taken(owner_id, kind, name, exclude=None):
    return ProposalTemplate.objects.filter(owner_id=owner_id, kind=kind, name=name).exclude(pk=exclude).exists()


def _check_name(owner_id, fields, exclude=None):
    if _name_taken(owner_id, fields['kind'], fields['name'], exclude):
        raise ValidationError({'name': f'You already have a template called “{fields["name"]}”.'})


def _locked(user, template_id):
    """The template, locked, when `user` may see it; 404 otherwise (another person's private one included)."""
    row = ProposalTemplate.objects.select_for_update().filter(Q(shared=True) | Q(owner=user), pk=template_id).first()
    if row is None:
        raise NotFound(NOT_FOUND)
    return row


def _record(user, action, summary, row, diff):
    return activity.record(
        None,
        user,
        AREA,
        action,
        summary,
        changes=[activity.change(target(row.id), diff)],
        subject=target(row.id),
    )


def create(user, data):
    """＋ Save as template: a new template of `user`'s, private unless shared."""
    fields = clean_write(data)
    with transaction.atomic():
        _check_name(user.id, fields)
        row = ProposalTemplate.objects.create(owner=user, **fields)
        diff = {key: [None, getattr(row, key)] for key in COLUMNS}
        _record(user, 'created', f'Saved the template “{row.name}”', row, diff)
    return row


def update(user, template_id, data):
    """Update: the columns the body names. → (row, Activity row or None when nothing changed)."""
    with transaction.atomic():
        row = _locked(user, template_id)
        if not template_store.editable_by(row, user):
            raise PermissionDenied(THEIRS)
        fields = clean_write(data, row)
        diff = {key: [getattr(row, key), value] for key, value in fields.items() if getattr(row, key) != value}
        if not diff:
            return row, None
        if 'name' in diff or 'kind' in diff:
            _check_name(row.owner_id, {'name': row.name, 'kind': row.kind, **fields}, exclude=row.id)
        for key, (_, value) in diff.items():
            setattr(row, key, value)
        row.save(update_fields=[*diff, 'updated_at'])
        entry = _record(user, 'changed', f'Updated the template “{row.name}”', row, diff)
    return row, entry


def delete(user, template_id):
    with transaction.atomic():
        row = _locked(user, template_id)
        if not template_store.editable_by(row, user):
            raise PermissionDenied(THEIRS)
        diff = {key: [getattr(row, key), None] for key in COLUMNS}
        _record(user, 'deleted', f'Deleted the template “{row.name}”', row, diff)
        row.delete()


def revert(entry, user):  # noqa: ARG001 (the reverters' signature)
    """`deals.activity.reverters['proposal_templates']`: an Update's earlier values back, refused after a later
    write."""
    (change,) = entry.changes
    template_id = int(change['t'].partition(':')[2])
    row = ProposalTemplate.objects.select_for_update().filter(pk=template_id).first()
    if row is None:
        raise activity.Refused(GONE)
    later = activity.later_keys(entry)
    if later:
        raise activity.changed_since([WORDS[key] for _, key in sorted(later)], [key for _, key in sorted(later)])
    diff = {key: [getattr(row, key), before] for key, (before, _) in change['k'].items() if getattr(row, key) != before}
    after = {'name': row.name, 'kind': row.kind, **{key: pair[1] for key, pair in diff.items()}}
    if ('name' in diff or 'kind' in diff) and _name_taken(row.owner_id, after['kind'], after['name'], row.id):
        raise activity.Refused(f'Another template is called “{after["name"]}” now, so this change cannot be reverted.')
    for key, (_, value) in diff.items():
        setattr(row, key, value)
    if diff:
        row.save(update_fields=[*diff, 'updated_at'])
    return [activity.change(target(row.id), diff)]
