"""RFP API (plan.md §7.11; K.6 endpoints): the page payload and the request's settings, the cards' marks and the sends.
Thin: parse → service → answer with what the screen redraws. The files are in `file_views`, the lens in `lens_views`
(slice 45), the check and the pills in `check_views` (slice 46).
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from . import page, services
from .context import Request

MAX_ID = 2**63 - 1  # a bigger id is not a row: 404, never a database error


def _deal(pk):
    if pk > MAX_ID:
        raise Http404
    return get_object_or_404(Deal.objects.select_related('client', 'owner'), pk=pk)


def _body(request):
    if not isinstance(request.data, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    return request.data


class RfpView(APIView):
    """GET deals/{id}/rfp/ → the page payload (rfp/page.py).
    PATCH {route?, carriers?: {add, remove}, funding?: {add, remove} | null, other_carriers?, form?, due_date?, notes?,
    include?: {file key: true | false | null} | 'reset'} → {changed: {key: value}, cleared: [card], activity_id,
    request, carriers, packet, drafts, done, checks_stamp}; 400 {field: [sentence]}."""

    def get(self, request, pk):
        return Response(page.page(_deal(pk)))

    def patch(self, request, pk):
        _deal(pk)
        written = services.update(request.user, pk, _body(request))
        deal = Deal.objects.select_related('client', 'owner').get(pk=pk)
        return Response(
            {
                'changed': written.changed,
                'cleared': written.cleared,
                'activity_id': written.activity.id if written.activity else None,
                **page.request_parts(Request(deal)),
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


class SentView(APIView):
    """POST deals/{id}/rfp/drafts/{key}/sent/ {sent: bool} → {drafts, done, stage, activity_id} (K64–K68, K120): the
    first send moves the deal to Quoting and pins the route; 404 no such draft; 409 a lost deal or a past year."""

    def post(self, request, pk, key):
        _deal(pk)
        sent = services.mark_sent(request.user, pk, key, _body(request).get('sent'))
        deal = Deal.objects.select_related('client', 'owner').get(pk=pk)
        parts = page.request_parts(Request(deal))
        activity_id = sent.activity.id if sent.activity else None
        answer = {'drafts': parts['drafts'], 'done': parts['done'], 'stage': sent.stage, 'activity_id': activity_id}
        return Response(answer)
