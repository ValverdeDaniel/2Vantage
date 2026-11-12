"""`GET deals/{id}/plans/stop-loss/`: the stop-loss analysis (plan.md §7.8, §8.14; F98–F107). Thin: parse → selector.

`?without=<plan id>:<laser position>,…` is the laser what-if (F104): a parameter of the read, never stored and never
in Activity. Lasers are named by position, so the address carries no claimant (rule 10). A malformed pair answers
400; a plan or position the line does not have is ignored. The five-tab workbook is the proposals app's
(`plans/stop-loss/workbook/`, §9.13): quotes cannot import the workbook writer.
"""

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from .selectors import stop_loss

MAX_PAIRS = 200


def without(raw):
    """'12:1,12:3,15:2' → {12: {1, 3}, 15: {2}}."""
    out = {}
    pairs = [part for part in str(raw or '').split(',') if part.strip()]
    if len(pairs) > MAX_PAIRS:
        raise ValidationError({'without': [f'At most {MAX_PAIRS} lasers can be left out at once.']})
    for part in pairs:
        plan, _, position = part.strip().partition(':')
        try:
            plan_id, n = int(plan), int(position)
        except ValueError as exc:
            raise ValidationError({'without': ['Give the lasers left out as <plan id>:<position>, …']}) from exc
        if n < 1:
            raise ValidationError({'without': ['A laser position starts at 1.']})
        out.setdefault(plan_id, set()).add(n)
    return out


class StopLossView(APIView):
    def get(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        return Response(stop_loss.analysis(deal, without(request.query_params.get('without'))))
