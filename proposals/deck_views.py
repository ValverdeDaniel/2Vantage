"""`GET deals/{id}/proposal/files/pdf/` and `…/files/pptx/`: the client PDF and the client PowerPoint, drafts
(plan.md §7.12, §9.6, §9.7; J24, J122, J141; J.6.6).

Built on each request from the deal as it stands (`story.build.deck`, then `paint.pdf.draw`): one layout pass, the
same frames the PowerPoint will replay. A draft writes nothing but its `downloaded` row (§3.8, rule 3), which names
the kind of file, never a person; Draft prints on every page until the proposal is issued (OQ35; Issue, slice 32).
"""

import io

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from deals import activity
from deals.downloads import file_response
from deals.models import Deal

from .paint import pdf, pptx
from .services import AREA
from .story import build


class ClientPdfView(APIView):
    def get(self, request, pk):
        deal = get_object_or_404(Deal.objects.select_related('client', 'owner'), pk=pk)
        found = build.deck(deal)
        data = pdf.draw(found['pages'], found['title'], found['sources'])
        activity.log_access(deal, request.user, 'downloaded', 'the client PDF (draft)', None, area=AREA)
        return file_response(io.BytesIO(data), build.file_name(deal))


class ClientPptxView(APIView):
    """The same deck as the PDF, replayed as slides (`paint.pptx.draw`, slice 31); the old "⬇ PowerPoint"."""

    def get(self, request, pk):
        deal = get_object_or_404(Deal.objects.select_related('client', 'owner'), pk=pk)
        found = build.deck(deal)
        data = pptx.draw(found['pages'], found['title'], found['sources'])
        activity.log_access(deal, request.user, 'downloaded', 'the client PowerPoint (draft)', None, area=AREA)
        return file_response(io.BytesIO(data), build.file_name(deal, 'pptx'))
