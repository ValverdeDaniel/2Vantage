"""GET plans/{id}/source/?key= — one value's full source for ↗ (plan.md §7.8; E18). Read only (Q.3 #2)."""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import fields
from .models import Plan
from .selectors.source import value_source


class PlanSourceView(APIView):
    def get(self, request, plan_id):
        if plan_id > 2**63 - 1:
            raise Http404
        plan = get_object_or_404(Plan, pk=plan_id)
        key = request.query_params.get('key') or ''
        if key not in fields.keys_for(plan.line):
            raise ValidationError({'key': ['Give a field of this plan.']})
        return Response(value_source(plan, key))
