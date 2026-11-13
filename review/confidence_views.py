"""The Overview's data confidence (plan.md §7.13, §8.6; M83–M93; M.6 endpoints; slice 64). Thin: parse → selector or
service → answer.

- GET  deals/{id}/confidence/ → `selectors.confidence.confidence` (cells, the confirmed bar, documents, the ignored
  and needs-checking rows, 50 each plus `more`, the last re-check). Writes nothing.
- POST deals/{id}/review/marks/ {action, document_id} | {action, refs} → {action, changed: {owner: n}, count,
  activity_id}: marks across every owner in one transaction (`services.marks`); Undo is POST activity/{id}/revert/.
  400 for a bad action, both or neither target, or refs that are not values; 404 for a file of another deal, or ids
  past bigint.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from .selectors import confidence as reading
from .services import marks

MAX_ID = 2**63 - 1


def _deal(pk):
    if pk > MAX_ID:
        raise Http404
    return get_object_or_404(Deal.objects.select_related('client'), pk=pk)


class ConfidenceView(APIView):
    def get(self, request, pk):
        return Response(reading.confidence(_deal(pk)))


class MarksView(APIView):
    def post(self, request, pk):
        if not isinstance(request.data, dict):
            raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
        deal = _deal(pk)
        done = marks.mark(
            request.user,
            deal.id,
            request.data.get('action'),
            document_id=request.data.get('document_id'),
            refs=request.data.get('refs'),
        )
        return Response(
            {
                'action': done.action,
                'changed': done.changed,
                'count': sum(done.changed.values()),
                'activity_id': done.row.id if done.row else None,
            }
        )
