"""The File panel and Remove (plan.md §3.8, §7.4; E10–E16; O.3.7; OQ23).

- `update`: label, kind, role, carrier, lines. Nothing written when nothing differs, not even Activity (E14); a kind
  the file's type does not fit refuses the whole write (E11).
- `archive` (Remove) keeps the row and its bytes; values keep their link (E15). `restore` puts it back (E16).
- `purge` (admins only, the view checks) deletes the row; its bytes go once that commits (E96).
Protected files (an issued proposal, a signed form) refuse archive, purge and a change of kind (O.3.7).

Activity keeps before and after of kind, role, carrier, lines and `archived`, never a label (it can carry a name);
a rename records the key only, so Revert refuses it with KEYS_ONLY (§3.7, E74).
"""

from django.db import transaction

from deals import activity, clock

from .. import kinds
from ..checks import check_extension
from ..models import Document
from .clean import clean

PROTECTED = 'This file is kept: an issued proposal or a signed form cannot be {what}.'
TRACKED = ('kind', 'role', 'carrier', 'lines')


def target(document):
    return f'document:{document.id}'


def locked(document_id):
    """The document, archived or not, locked for the rest of the transaction."""
    return Document.all_objects.select_for_update().get(pk=document_id)


def _refuse_protected(document, what):
    if document.protected:
        raise activity.Refused(PROTECTED.format(what=what))


@transaction.atomic
def update(user, document_id, data):
    """Returns (document, changed field names)."""
    document = locked(document_id)
    meta = clean(data, document)
    changed = {key: value for key, value in meta.items() if getattr(document, key) != value}
    if not changed:
        return document, []
    if 'kind' in changed:
        _refuse_protected(document, 'given another kind')
        check_extension(changed['kind'], document.original_name)
    before = {key: getattr(document, key) for key in changed}
    for key, value in changed.items():
        setattr(document, key, value)
    document.save(update_fields=list(changed))
    diff = {key: [before[key], changed[key]] for key in TRACKED if key in changed}
    entries = [activity.change(target(document), diff)] if diff else []
    if 'label' in changed:
        entries.append({'t': target(document), 'k': ['label']})  # never the label's text (§3.8)
    activity.record(document.deal, user, 'documents', 'updated', 'Edited a file', changes=entries,
                    document_id=document.id)  # fmt: skip
    return document, list(changed)


def set_archived(document, archived, user):
    """Archive or restore one locked row. Returns the {archived: [before, after]} diff, or {} when nothing moved."""
    if bool(document.archived_at) == archived:
        return {}
    if archived:
        _refuse_protected(document, 'removed')
        document.archived_at, document.archived_by = clock.now(), user if getattr(user, 'id', None) else None
    else:
        document.archived_at, document.archived_by = None, None
    document.save(update_fields=['archived_at', 'archived_by'])
    return {'archived': [not archived, archived]}


def _archive_or_restore(user, document_id, archived):
    document = locked(document_id)
    diff = set_archived(document, archived, user)
    if diff:
        word = 'Removed' if archived else 'Restored'
        summary = f'{word} a {kinds.label(document.kind)} file'
        action = 'archived' if archived else 'restored'
        activity.record(document.deal, user, 'documents', action, summary,
                        changes=[activity.change(target(document), diff)], document_id=document.id)  # fmt: skip
    return document


@transaction.atomic
def archive(user, document_id):
    return _archive_or_restore(user, document_id, True)


@transaction.atomic
def restore(user, document_id):
    return _archive_or_restore(user, document_id, False)


@transaction.atomic
def purge(user, document_id):
    """Delete the row for good (admins only, OQ23). Values keep the id they had; the bytes go after commit."""
    document = locked(document_id)
    _refuse_protected(document, 'deleted')
    deal, kind, document_id = document.deal, document.kind, document.id
    document.delete()
    summary = f'Deleted a {kinds.label(kind)} file for good'
    activity.record(deal, user, 'documents', 'deleted', summary, document_id=document_id)
