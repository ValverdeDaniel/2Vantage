"""`GET deals/{id}/proposal/files/xlsx/`: the client spreadsheet, a draft (plan.md §7.12, §9.4; J24, J97, J104).

Built on each request from the deal as it stands (`workbook.build`). A draft download writes nothing (J97, Q.3 #2): the
file carries no member data, so there is no `downloaded` row to keep (§3.8). Its name is `<Client> - <year> Benefits
Proposal-DRAFT.xlsx` (J104) until Issue (slice 32) stores the issued copy. A proposal with nothing to present answers
409 with the producer's sentence.
"""

import io

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.downloads import file_response
from deals.models import Deal

from .workbook import build


class ClientWorkbookView(APIView):
    def get(self, request, pk):
        deal = get_object_or_404(Deal.objects.select_related('client', 'owner'), pk=pk)
        try:
            data, name = build.workbook(deal)
        except build.NothingToPresent as refusal:
            return Response({'detail': str(refusal)}, status=status.HTTP_409_CONFLICT)
        return file_response(io.BytesIO(data), name)
