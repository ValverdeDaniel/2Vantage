"""`GET deals/{id}/proposal/preview/?file=workbook&tab=` and `?file=deck`: the Export viewer's payloads (plan.md §7.12,
§8.14; J107–J111, J114, J116–J118; J.6.5, J.6.6).

Built on each request from the deal as it stands, from the downloads' own builders; `Cache-Control: private,
no-store`; writes nothing at all (Q.3 #2): a preview is not a download, so not even a `downloaded` row. A proposal
with nothing to present answers 409 in the download's own words (J107: "refusals in the downloads' words").

`PREVIEWS` maps `file` to its builder: the client spreadsheet (`workbook`, one tab a request; slice 28) and the deck
(`deck`: one build behind the PowerPoint, PDF and Paper views, the PDF's bytes with its page log; slice 30).
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from .viewer import deck, workbook
from .workbook.build import NothingToPresent

PREVIEWS = {
    workbook.FILE: lambda deal, params: workbook.preview(deal, (params.get('tab') or '').strip() or None),
    deck.FILE: lambda deal, params: deck.preview(deal),
}


def _no_store(response):
    response['Cache-Control'] = 'private, no-store'
    return response


class ProposalPreviewView(APIView):
    def get(self, request, pk):
        deal = get_object_or_404(Deal.objects.select_related('client', 'owner'), pk=pk)
        wanted = (request.query_params.get('file') or '').strip()
        build = PREVIEWS.get(wanted)
        if build is None:
            known = ', '.join(sorted(PREVIEWS))
            return _no_store(Response({'detail': f'No preview of "{wanted}": ask for {known}.'}, status=400))
        try:
            body = build(deal, request.query_params)
        except NothingToPresent as refusal:
            return _no_store(Response({'detail': str(refusal)}, status=status.HTTP_409_CONFLICT))
        return _no_store(Response(body))
