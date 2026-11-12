"""Proposal API (plan.md §7.12): the configuration and preview (Release 1, slice M6; slice 25 replaces them) and
"What the client will see", the page split (slice 14)."""

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal
from quotes import board_presets, parse

from . import pages_read, selectors, services


class ProposalView(APIView):
    def get(self, request, pk):
        return Response(selectors.payload(get_object_or_404(Deal, pk=pk)))

    def put(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        services.save_config(request.user, deal, request.data)
        return Response(selectors.payload(deal))


class PagesView(APIView):
    def get(self, request, pk):
        """?line= (required) and ?preset= (the Advisor's Columns tab picking the rows; Primary by default)."""
        deal = get_object_or_404(Deal, pk=pk)
        line = parse.line(request)
        preset = request.query_params.get('preset') or board_presets.DEFAULT_PRESET
        if preset not in dict(board_presets.PRESETS):
            raise ValidationError({'preset': ['Give a column preset: ' + ', '.join(dict(board_presets.PRESETS)) + '.']})
        return Response(pages_read.payload(deal, line, preset))
