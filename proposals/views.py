"""Proposal API (plan.md §7.9). Release 1, slice M6: configuration and preview."""

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from . import selectors, services


class ProposalView(APIView):
    def get(self, request, pk):
        return Response(selectors.payload(get_object_or_404(Deal, pk=pk)))

    def put(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        services.save_config(request.user, deal, request.data)
        return Response(selectors.payload(deal))
