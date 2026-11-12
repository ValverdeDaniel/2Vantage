"""Advisor API: moving and removing plans (plan.md §7.8; F59–F61): `plans/move-line/`, `plans/delete/`, `plans/clear/`.

Each answers only what changed and the Activity row a Revert would undo (Revert of a removal is its Restore); a
refusal answers 409 with its sentence; a bad id or line answers 400."""

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from . import parse, selectors, services


def _removal(result):
    """{removed: [ids], kept: [{id, name}], note, plans: [the plans left on the board that changed], activity_id}."""
    return Response(
        {
            'removed': [plan.id for plan in result.removed],
            'kept': [{'id': plan.id, 'name': f'{plan.carrier} {plan.name}', 'reason': 'sold'} for plan in result.kept],
            'note': result.note,
            'plans': selectors.payloads(result.changed),
            'activity_id': getattr(result.row, 'id', None),
        }
    )


class DeleteView(APIView):
    def post(self, request, pk):
        """{plan_ids}: removes them softly; sold plans stay and are named (409 when every plan named is sold)."""
        deal = get_object_or_404(Deal, pk=pk)
        return _removal(services.delete_plans(request.user, deal, parse.plan_ids(request.data.get('plan_ids'))))


class ClearView(APIView):
    def post(self, request, pk):
        """{line}: removes every plan on the line except its current and sold plans."""
        deal = get_object_or_404(Deal, pk=pk)
        return _removal(services.clear_line(request.user, deal, parse.line(request)))


class MoveLineView(APIView):
    def post(self, request, pk):
        """{plan_ids, line} → {line, plans: [the moved plans and the plans they left that changed], activity_id}."""
        deal = get_object_or_404(Deal, pk=pk)
        line = parse.line(request)
        changed, row = services.move_line(request.user, deal, parse.plan_ids(request.data.get('plan_ids')), line)
        return Response({'line': line, 'plans': selectors.payloads(changed), 'activity_id': getattr(row, 'id', None)})
