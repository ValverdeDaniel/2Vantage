"""Census API (plan.md §7.7): the census page and the import door. Thin: parse → service or selector → respond.

The roster's own writes (members, clear), the template, the export, sources and marks arrive with the grid, slice 41.
Opening an import reads the stored census file (its samples), so it is a view of a file with member data and writes
its `viewed` row (§3.8, E99).
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal
from documents.models import Document
from documents.services import record_access

from . import selectors, services
from .models import CensusImport
from .selectors.page import MAX_PAGE_SIZE, PAGE_SIZE, SHOWS

MAX_ID = 2**63 - 1  # a bigger id is not a row: 404, never a database error


def _deal(pk):
    if pk > MAX_ID:
        raise Http404
    return get_object_or_404(Deal, pk=pk)


def _import(import_id):
    if import_id > MAX_ID:
        raise Http404
    return get_object_or_404(CensusImport, pk=import_id)


def _body(request):
    if not isinstance(request.data, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    return request.data


def _whole(raw, name, default, low, high):
    if raw in (None, ''):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: ['Send a whole number.']}) from exc
    if not low <= value <= high:
        raise ValidationError({name: [f'Send a number from {low} to {high}.']})
    return value


def _viewed(request, imp):
    document = Document.all_objects.filter(pk=imp.document_id).first() if imp.document_id else None
    if document is not None:
        record_access(request.user, document, inline=True)


class CensusView(APIView):
    """GET deals/{id}/census/?page=&page_size=&show=all|issues|missing&q= — the census page."""

    def get(self, request, pk):
        deal = _deal(pk)
        query = request.query_params
        show = query.get('show') or 'all'
        if show not in SHOWS:
            raise ValidationError({'show': ['Show all, issues or missing.']})
        page = _whole(query.get('page'), 'page', 1, 1, 100000)
        size = _whole(query.get('page_size'), 'page_size', PAGE_SIZE, 1, MAX_PAGE_SIZE)
        return Response(selectors.census_page(deal, page, size, show, (query.get('q') or '')[:100]))


class ImportsView(APIView):
    """POST deals/{id}/census/imports/ {document_id} → 201 the proposed import (C12–C14)."""

    def post(self, request, pk):
        _deal(pk)
        document_id = _body(request).get('document_id')
        if isinstance(document_id, bool) or not isinstance(document_id, int) or not 0 < document_id <= MAX_ID:
            raise ValidationError({'document_id': ['Choose a census file on this deal.']})
        imp = services.create_import(request.user, pk, document_id)
        _viewed(request, imp)
        return Response(selectors.import_payload(imp), status=status.HTTP_201_CREATED)


class ImportView(APIView):
    """GET census/imports/{id}/ — the import with samples; PATCH {sheet_name, header_row, first_data_row, reformat,
    mapping: [{column, field}]} → the import (C15)."""

    def get(self, request, import_id):
        imp = _import(import_id)
        _viewed(request, imp)
        return Response(selectors.import_payload(imp))

    def patch(self, request, import_id):
        _import(import_id)
        imp, _changed = services.update_import(request.user, import_id, _body(request))
        _viewed(request, imp)
        return Response(selectors.import_payload(imp))


class ApplyView(APIView):
    """POST census/imports/{id}/apply/?dry_run=1 → who is added, changed, removed and kept, writing nothing; without
    dry_run → {stats, summary, import} (C16, C17)."""

    def post(self, request, import_id):
        _import(import_id)
        if request.query_params.get('dry_run') in ('1', 'true'):
            return Response(services.dry_run(import_id))
        applied = services.apply_import(request.user, import_id)
        imp = CensusImport.objects.select_related('document__deal').get(pk=import_id)
        census = selectors.census_page(imp.deal, page_size=1)
        return Response(
            {
                'stats': applied.stats,
                'summary': census['summary'],
                'import': selectors.import_row(imp),
                'activity_id': applied.activity.id,
            }
        )


class DiscardView(APIView):
    """POST census/imports/{id}/discard/ → 204; the roster is untouched."""

    def post(self, request, import_id):
        _import(import_id)
        services.discard_import(request.user, import_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
