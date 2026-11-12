"""Advisor API: priced versions (plan.md §7.8; F76–F84): `deals/{id}/plans/priced/` and `plans/{id}/priced/` (✎).

Both take `dry_run`: the preview, written nowhere, whose figures the commit then shows (F76). The answer:
`{dry_run, drafts: [{original_id, name, label, derived, starred, changes: {key: value}, premium, change, part_of,
credit, enrollment_used, enrollment_source}], plans: [the versions written], warning, activity_id}`. A malformed
request answers 400 with a sentence; a refusal (a sold plan, the in-force baseline, a bundle already in the rates, a
rate below zero, a dollar credit across several plans, a version's kind) answers 409 with its own.
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from . import parse, selectors, services
from .models import Plan


def _dry_run(request):
    return request.data.get('dry_run') in (True, 'true', '1', 1)


def _answer(result, dry_run, created=False):
    body = {
        'dry_run': dry_run,
        'drafts': result.drafts,
        'plans': [] if dry_run else selectors.payloads(result.plans),
        'warning': result.warning,
        'activity_id': getattr(result.row, 'id', None),
    }
    code = status.HTTP_201_CREATED if created and not dry_run else status.HTTP_200_OK
    return Response(body, status=code)


class PricedView(APIView):
    def post(self, request, pk):
        """{plan_ids, kind, all?, each?, parts?, conditional?, credit?, note?, name?, dry_run?}: a version of each."""
        deal = get_object_or_404(Deal, pk=pk)
        dry_run = _dry_run(request)
        plan_ids = parse.plan_ids(request.data.get('plan_ids'))
        result = services.priced.price(request.user, deal, plan_ids, request.data, dry_run=dry_run)
        return _answer(result, dry_run, created=True)


class RepriceView(APIView):
    def post(self, request, plan_id):
        """{kind, …, dry_run?}: ✎ re-price this version from its original."""
        get_object_or_404(Plan, pk=plan_id)
        dry_run = _dry_run(request)
        return _answer(services.priced.reprice(request.user, plan_id, request.data, dry_run=dry_run), dry_run)
