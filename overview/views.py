"""The Overview over HTTP (plan.md §7.16; M.6 "One endpoint"). Thin: parse → read → respond. Every signed-in user sees
every deal (OQ3). The tab's writes use their owners' endpoints (notes, contacts, lost and reopen, intake, archive, the
client status door), never this app (O.2)."""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal
from deals.views import MAX_ID

from . import payload


class DealOverviewView(APIView):
    """GET deals/{id}/overview/ → the Overview's payload (`payload.overview`); 404 for an unknown or oversized id."""

    def get(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        deal = get_object_or_404(Deal.objects.select_related('client', 'client__owner', 'owner'), pk=pk)
        return Response(payload.overview(deal, request.user))
