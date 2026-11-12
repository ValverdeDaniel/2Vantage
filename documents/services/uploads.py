"""Storing a file as a Document (plan.md §3.8, §6.3; E6–E8, D52; OQ24).

`upload` is the only door for a person's or a client's file: kind required, the kind's accept list, first bytes that
match the extension, 30 MB at most, a PDF's page count read at upload, and the member-data screen stored on the row.
`store_bytes` stores a file the app made (an issued proposal): never screened. The bytes an upload stored are removed
when its own transaction fails; a rollback further out leaves bytes that `sweep_orphan_files` finds (E98).
"""

from contextlib import contextmanager

from django.core.files.base import ContentFile
from django.db import transaction

from deals import activity
from deals.downloads import content_type_for

from .. import kinds, pages, screening
from ..checks import check_upload
from ..models import Document, remove_bytes
from .clean import clean


def _read(upload_file):
    upload_file.seek(0)
    raw = upload_file.read()
    upload_file.seek(0)
    return raw


@contextmanager
def _stored(document, name, raw):
    """Store the bytes; when anything after fails (the row, its Activity), the bytes go before the error rises."""
    document.file.save(name, ContentFile(raw), save=False)
    try:
        yield
    except BaseException:
        remove_bytes(document.file.storage, document.file.name)
        raise


@transaction.atomic
def upload(user, deal, upload_file, data=None, source='staff', log=True, link_id=None, slot=''):
    """A new Document from an uploaded file. Raises 400 (no kind, a type the kind refuses, bytes that are not what
    the name says) or 413 (over the cap); nothing is stored then."""
    meta = clean(data or {}, require_kind=True)
    check_upload(upload_file, meta['kind'])
    raw = _read(upload_file)
    name = upload_file.name
    document = Document(
        deal=deal,
        original_name=name[:255],
        size=len(raw),
        content_type=content_type_for(name),
        page_count=pages.page_count(raw) if kinds.shape_of(name) == kinds.PDF else None,
        screen=screening.screen(name, raw, meta['kind']),
        uploaded_by=user if getattr(user, 'is_authenticated', False) else None,
        source=source,
        link_id=link_id,
        slot=slot or '',
        **meta,
    )
    with _stored(document, name, raw):
        document.save()
        if log:
            # File names and labels can carry a person's name (§3.8): the summary names the kind, the row the file.
            summary = f'Uploaded a {kinds.label(document.kind)} file'
            kind = 'client' if source == 'client' else None
            activity.record(deal, user, 'documents', 'created', summary, document_id=document.id, actor_kind=kind)
    return document


@transaction.atomic
def store_bytes(user, deal, filename, content, kind, label, protected=False):
    """Store a file the app made (an issued proposal) as a document. Never screened (J.6.4)."""
    document = Document(
        deal=deal,
        original_name=filename[:255],
        size=len(content),
        kind=kind,
        label=label,
        content_type=content_type_for(filename),
        page_count=pages.page_count(content) if kinds.shape_of(filename) == kinds.PDF else None,
        protected=protected,
        uploaded_by=user if getattr(user, 'is_authenticated', False) else None,
    )
    with _stored(document, filename, content):
        document.save()
    return document
