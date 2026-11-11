"""Every write to documents (plan.md §3.8, §6.3, §7.4)."""

import os

from django.conf import settings
from django.db import transaction
from django.db.models import ProtectedError
from rest_framework.exceptions import APIException, ValidationError

from deals import activity, lines
from deals.downloads import content_type_for
from deals.values import locked

from . import kinds
from .models import Document


def _clean_meta(data, current=None):
    meta = {}
    if 'kind' in data:
        kind = data['kind'] or 'other'
        if kind not in kinds.KIND_KEYS:
            raise ValidationError({'kind': ['Unknown document kind.']})
        meta['kind'] = kind
    kind = meta.get('kind', getattr(current, 'kind', 'other'))
    if 'role' in data:
        role = data['role'] or ''
        if role and role not in kinds.ROLE_KEYS:
            raise ValidationError({'role': ['Unknown document role.']})
        meta['role'] = role if kind in kinds.ROLE_KINDS else ''
    elif current is not None and kind not in kinds.ROLE_KINDS:
        meta['role'] = ''
    if 'lines' in data:
        chosen = data['lines'] or []
        if not isinstance(chosen, list) or any(line not in lines.BY_KEY for line in chosen):
            raise ValidationError({'lines': ['Lines must be line keys.']})
        meta['lines'] = chosen
    for key, limit in (('carrier', 200), ('label', 200)):
        if key in data:
            meta[key] = (data[key] or '').strip()[:limit]
    return meta


class FileTooLarge(APIException):
    status_code = 413
    default_detail = 'Files can be up to 50 MB.'


def check_upload(upload):
    extension = os.path.splitext(upload.name)[1].lower()
    if extension not in kinds.ALLOWED_EXTENSIONS:
        raise ValidationError({'file': ["That file type isn't accepted."]})
    if upload.size > settings.FILE_UPLOAD_MAX_BYTES:
        raise FileTooLarge()


@transaction.atomic
def upload(user, deal, upload_file, data=None, source='staff', log=True):
    check_upload(upload_file)
    meta = _clean_meta(data or {})
    document = Document(
        deal=deal,
        original_name=upload_file.name[:255],
        size=upload_file.size,
        content_type=content_type_for(upload_file.name),
        uploaded_by=user,
        source=source,
        **meta,
    )
    document.file.save(upload_file.name, upload_file, save=False)
    document.save()
    if log:
        # File names and labels can carry a person's name (§3.8), so the summary names only the kind.
        activity.record(deal, user, 'documents', 'created', f'Uploaded a {document.kind} document')
    return document


@transaction.atomic
def store_bytes(user, deal, filename, content, kind, label):
    """Store a file the app made (an issued proposal) as a document."""
    from django.core.files.base import ContentFile

    document = Document(
        deal=deal,
        original_name=filename[:255],
        size=len(content),
        kind=kind,
        label=label,
        content_type=content_type_for(filename),
        uploaded_by=user,
    )
    document.file.save(filename, ContentFile(content), save=False)
    document.save()
    return document


@transaction.atomic
def update(user, document_id, data):
    document = locked(Document, document_id)
    for key, value in _clean_meta(data, document).items():
        setattr(document, key, value)
    document.save()
    activity.record(document.deal, user, 'documents', 'updated', 'Edited', 1, 'documents:meta', 'document detail')
    return document


@transaction.atomic
def delete(user, document_id):
    document = locked(Document, document_id)
    deal = document.deal
    try:
        document.delete()
    except ProtectedError as exc:
        raise ValidationError({'detail': 'An issued proposal cannot be deleted.'}) from exc
    activity.record(deal, user, 'documents', 'deleted', 'Deleted a document')


def record_download(user, document):
    if document.kind in kinds.PHI_KINDS:
        activity.record(document.deal, user, 'documents', 'downloaded', f'Downloaded a {document.kind} document')
