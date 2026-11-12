"""Documents API (plan.md §7.4; E.6): the list and upload, the File panel, Remove and Restore, the admin purge and the
file itself. Sheets are sheet_views.py."""

import json

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.downloads import file_response
from deals.models import Deal

from . import selectors, services
from .models import Document

MAX_ID = 2**63 - 1  # a bigger id is not a row: 404, never a database error
FORM_FIELDS = ('kind', 'role', 'carrier', 'label')


def document_or_404(document_id):
    """Any document, removed or not: a removed file still opens, and still restores (E15)."""
    if document_id > MAX_ID:
        raise Http404
    return get_object_or_404(Document.all_objects.select_related('deal__client'), pk=document_id)


def _form_meta(request):
    meta = {key: request.data.get(key) for key in FORM_FIELDS if key in request.data}
    if 'lines' in request.data:
        raw = request.data.get('lines')
        try:
            meta['lines'] = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError as exc:
            raise ValidationError({'lines': ['Lines must be a JSON array.']}) from exc
    return meta


class DocumentsView(APIView):
    """GET the deal's files (`?archived=1`: the removed ones); POST one file (multipart, `kind` required)."""

    def get(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        deal = get_object_or_404(Deal, pk=pk)
        archived = request.query_params.get('archived') == '1'
        return Response(selectors.deal_documents(deal, archived=archived))

    def post(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        deal = get_object_or_404(Deal, pk=pk)
        files = request.FILES.getlist('file')
        if not files:
            raise ValidationError({'file': ['Choose a file.']})
        if len(files) > 1:
            raise ValidationError({'file': ['Send one file per request.']})
        document = services.upload(request.user, deal, files[0], _form_meta(request))
        return Response(selectors.document_payload(document), status=status.HTTP_201_CREATED)


class DocumentView(APIView):
    """PATCH the File panel's fields; DELETE purges (admins only, OQ23)."""

    def patch(self, request, document_id):
        document_or_404(document_id)
        if not isinstance(request.data, dict):
            raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
        document, _changed = services.update(request.user, document_id, request.data)
        return Response(selectors.document_payload(document))

    def delete(self, request, document_id):
        document_or_404(document_id)
        if not request.user.is_staff:
            return Response({'detail': 'Only an admin can delete a file for good.'}, status=status.HTTP_403_FORBIDDEN)
        services.purge(request.user, document_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ArchiveView(APIView):
    """POST: Remove (archive) a file; its values keep their link (E15)."""

    def post(self, request, document_id):
        document_or_404(document_id)
        return Response(selectors.document_payload(services.archive(request.user, document_id)))


class RestoreView(APIView):
    """POST: put a removed file back (E16)."""

    def post(self, request, document_id):
        document_or_404(document_id)
        return Response(selectors.document_payload(services.restore(request.user, document_id)))


class DownloadView(APIView):
    """GET the bytes: an attachment, or `?inline=1` for the viewer under a sandbox CSP (E17). A file with member data
    writes its `downloaded` or `viewed` row (E99) and downloads under the client's name and its kind."""

    def get(self, request, document_id):
        document = document_or_404(document_id)
        inline = request.query_params.get('inline') == '1'
        try:
            handle = document.file.open('rb')
        except (FileNotFoundError, OSError, ValueError) as exc:
            raise Http404('This file is missing from storage.') from exc
        services.record_access(request.user, document, inline)
        return file_response(handle, services.download_name(document), inline=inline)
