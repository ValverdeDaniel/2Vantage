"""The Overview over HTTP (plan.md §7.16; M.6). Thin: parse → read → respond. Every signed-in user sees every deal
(OQ3). The tab's writes use their owners' endpoints (notes, contacts, lost and reopen, intake, documents, the
questionnaire's form choice, review's tray, archive, the client status door), never this app (O.2)."""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal
from deals.selectors import activity_feed, activity_row
from deals.views import MAX_ID, Pages

from . import feed, payload


class DealOverviewView(APIView):
    """GET deals/{id}/overview/ → the Overview's payload (`payload.overview`); 404 for an unknown or oversized id."""

    def get(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        deal = get_object_or_404(Deal.objects.select_related('client', 'client__owner', 'owner'), pk=pk)
        return Response(payload.overview(deal, request.user))


class DealFeedView(APIView):
    """GET deals/{id}/overview/feed/?page= → {count, next, previous, results: [activity row + detail]}: the Timeline
    (M70, M71), 25 rows a page, newest first, no downloads or views; a page past the end is a 404, as DRF pages."""

    def get(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        deal = get_object_or_404(Deal, pk=pk)
        pager = Pages()
        page = pager.paginate_queryset(activity_feed(deal), request, view=self)
        found = feed.details(page)
        return pager.get_paginated_response([{**activity_row(row), 'detail': found.get(row.id, '')} for row in page])
