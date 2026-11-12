"""GET deals/{id}/plans/as-quoted/ — the printed tables of the deal's scanned quotes (plan.md §7.8, O.3.5; F42, E42;
slice 21): with no `document`, `{files: [...]}`, one entry per table (the Advisor's chips, Documents' "As in the
file"); with `?document=<id>[&line=<line>]`, that table (`selectors/as_quoted.py`). Read only (Q.3 #2). A bad id or
line answers 400; a file with no table on this deal 404.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals import lines as line_vocab
from deals.models import Deal

from .selectors import as_quoted

MAX_ID = 2**63 - 1


class AsQuotedView(APIView):
    def get(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        deal = get_object_or_404(Deal, pk=pk)
        raw = str(request.query_params.get('document') or '').strip()
        if not raw:
            return Response({'files': as_quoted.files(deal)})
        if not raw.isdigit() or int(raw) > MAX_ID:
            raise ValidationError({'document': ['Give the id of one file.']})
        line = request.query_params.get('line') or ''
        if line and line not in line_vocab.BY_KEY:
            raise ValidationError({'line': ['Give one of the deal’s lines.']})
        found = as_quoted.table(deal, int(raw), line)
        if found is None:
            raise Http404
        return Response(found)
