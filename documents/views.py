"""Documents API, version 1 (plan.md §7.4)."""

import json

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.downloads import file_response
from deals.models import Deal
from deals.selectors import person

from . import services
from .models import Document


def document_payload(document):
    return {
        'id': document.id,
        'original_name': document.original_name,
        'label': document.label,
        'kind': document.kind,
        'role': document.role,
        'carrier': document.carrier,
        'lines': document.lines,
        'size': document.size,
        'page_count': document.page_count,
        'source': document.source,
        'review_state': document.review_state,
        'uploaded_by': person(document.uploaded_by),
        'uploaded_at': document.uploaded_at,
        'issued': hasattr(document, 'proposal_issue'),
    }


def _form_meta(request):
    meta = {key: request.data.get(key) for key in ('kind', 'role', 'carrier', 'label') if key in request.data}
    if 'lines' in request.data:
        raw = request.data.get('lines')
        try:
            meta['lines'] = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError as exc:
            raise ValidationError({'lines': ['Lines must be a JSON array.']}) from exc
    return meta


class DocumentsView(APIView):
    def get(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        return Response([document_payload(d) for d in deal.documents.select_related('uploaded_by')])

    def post(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        upload = request.FILES.get('file')
        if not upload:
            raise ValidationError({'file': ['Choose a file.']})
        document = services.upload(request.user, deal, upload, _form_meta(request))
        return Response(document_payload(document), status=status.HTTP_201_CREATED)


class DocumentView(APIView):
    def patch(self, request, document_id):
        get_object_or_404(Document, pk=document_id)
        return Response(document_payload(services.update(request.user, document_id, request.data)))

    def delete(self, request, document_id):
        get_object_or_404(Document, pk=document_id)
        services.delete(request.user, document_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DownloadView(APIView):
    def get(self, request, document_id):
        document = get_object_or_404(Document, pk=document_id)
        services.record_download(request.user, document)
        inline = request.query_params.get('inline') == '1'
        return file_response(document.file.open('rb'), document.original_name, inline=inline)
