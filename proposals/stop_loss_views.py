"""`GET deals/{id}/plans/stop-loss/workbook/`: the stop-loss analysis workbook (plan.md §7.8, §9.13; J166, F106).

The proposals app serves it because the sheet writer lives here (`workbook/stop_loss_build.py`) and quotes cannot
import to its right; the analysis and its math stay in quotes. Built on each request from the deal as it stands; a GET
writes nothing (Q.3 #2): the file prints laser amounts by position and no claimant, so there is no `downloaded` row
to keep (§3.8, OQ104), as the client spreadsheet's draft (J97). A deal with no stop-loss plan, or with two or more
in-force contracts, answers 409 with the producer's sentence.
"""

import io

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.downloads import file_response
from deals.models import Deal

from .workbook import stop_loss_build


class StopLossWorkbookView(APIView):
    def get(self, request, pk):
        deal = get_object_or_404(Deal.objects.select_related('client'), pk=pk)
        try:
            data, name = stop_loss_build.workbook(deal)
        except stop_loss_build.Refused as refusal:
            return Response({'detail': str(refusal)}, status=status.HTTP_409_CONFLICT)
        return file_response(io.BytesIO(data), name)
