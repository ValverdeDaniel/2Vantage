"""Advisor API: stars, the shortlist, the recommendation and the sale (plan.md §7.8; F50, F51, F55, F123).

Each answers only the plans that changed and the Activity row a Revert would undo; a refusal answers 409 with its
sentence."""

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal
from deals.selectors import deal_header

from . import parse, selectors, services
from .models import Plan


def _changed(plans, row):
    return Response({'plans': selectors.payloads(plans), 'activity_id': getattr(row, 'id', None)})


class StarView(APIView):
    def post(self, request, pk):
        """{plan_ids, starred}: the 16-column cap, the reason, the auto-link and the lock."""
        deal = get_object_or_404(Deal, pk=pk)
        ids = parse.plan_ids(request.data.get('plan_ids', []))
        return _changed(*services.star(request.user, deal, ids, bool(request.data.get('starred'))))


class ClearShortlistView(APIView):
    def post(self, request, pk):
        """{line}: every star on that line comes off."""
        deal = get_object_or_404(Deal, pk=pk)
        return _changed(*services.clear_shortlist(request.user, deal, parse.line(request)))


class RecommendView(APIView):
    def post(self, request, plan_id):
        get_object_or_404(Plan, pk=plan_id)
        plan = services.set_recommended(request.user, plan_id, bool(request.data.get('recommended')))
        return Response({**selectors.plan_payload(plan), 'activity_id': plan.activity_id})


class SoldView(APIView):
    def post(self, request, plan_id):
        """{sold} → {plan, deal}: the deal's header carries its new stage and its client's status."""
        get_object_or_404(Plan, pk=plan_id)
        plan, deal = services.set_sold(request.user, plan_id, bool(request.data.get('sold')))
        return Response({'plan': selectors.plan_payload(plan), 'deal': deal_header(deal)})
