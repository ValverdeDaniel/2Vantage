"""RFP API (plan.md §7.11; K.6 endpoints): the page payload and the request's settings, and the cards' marks. Thin:
parse → service → answer with what the screen redraws. The census files are in `file_views`, the lens in `lens_views`
(slice 45); the packet zip, checks and sends join with slice 46.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from . import page, services
from .models import RfpRequest

MAX_ID = 2**63 - 1  # a bigger id is not a row: 404, never a database error


def _deal(pk):
    if pk > MAX_ID:
        raise Http404
    return get_object_or_404(Deal.objects.select_related('client'), pk=pk)


def _body(request):
    if not isinstance(request.data, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    return request.data


class RfpView(APIView):
    """GET deals/{id}/rfp/ → the page payload (rfp/page.py).
    PATCH {route?, carriers?: {add, remove}, funding?: {add, remove} | null, other_carriers?, due_date?, notes?,
    include?: {file key: true | false | null} | 'reset'} → {changed: {key: value}, cleared: [card], activity_id,
    request, carriers, packet, done}; 400 {field: [sentence]}."""

    def get(self, request, pk):
        return Response(page.page(_deal(pk)))

    def patch(self, request, pk):
        _deal(pk)
        written = services.update(request.user, pk, _body(request))
        deal = Deal.objects.select_related('client').get(pk=pk)
        row = RfpRequest.objects.filter(deal_id=pk).first()
        band = page.band_block_for(deal)
        return Response(
            {
                'changed': written.changed,
                'cleared': written.cleared,
                'activity_id': written.activity.id if written.activity else None,
                **page.request_parts(deal, row, band['key']),
            }
        )


class DoneView(APIView):
    """POST deals/{id}/rfp/done/ {card, done} → {done: {card: {by, by_id, at}}, activity_id} (K9)."""

    def post(self, request, pk):
        _deal(pk)
        data = _body(request)
        marked = services.set_done(request.user, pk, data.get('card'), data.get('done'))
        activity_id = marked.activity.id if marked.activity else None
        return Response({'done': page.marks(marked.done), 'activity_id': activity_id})
