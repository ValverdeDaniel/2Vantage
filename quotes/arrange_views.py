"""Advisor API: roles, links, the order and slot picks (plan.md §7.8; F43–F48, F52, F53; OQ13).

Each answers only what changed (the changed plans, or the line's new order as plan ids) and the Activity row a Revert
would undo; a refused move answers 409 with its sentence; a bad id answers 400."""

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from . import parse, selectors, services


def _changed(plans, row, **extra):
    return Response({**extra, 'plans': selectors.payloads(plans), 'activity_id': getattr(row, 'id', None)})


class RoleView(APIView):
    def post(self, request, pk):
        """{plan_ids, role, renews_id?, replaces_ids?}: Mark current, Remove current, or a renewal or alternate with the
        links its role needs. A plan made current loses its star, its recommendation and its links (F53)."""
        deal = get_object_or_404(Deal, pk=pk)
        data = request.data
        changed, row = services.set_role(
            request.user,
            deal,
            parse.plan_ids(data.get('plan_ids')),
            services.roles.check_role(data.get('role')),
            parse.optional_id(data.get('renews_id'), 'renews_id'),
            parse.plan_ids(data.get('replaces_ids') or [], 'replaces_ids'),
        )
        return _changed(changed, row)


class LinksView(APIView):
    def post(self, request, pk):
        """{plan_id, replaces_ids} for an alternate (several: a consolidation; none: an added plan), or
        {plan_id, renews_id} for a renewal (F52)."""
        deal = get_object_or_404(Deal, pk=pk)
        data = request.data
        replaces = data.get('replaces_ids')
        changed, row = services.set_links(
            request.user,
            deal,
            parse.plan_id(data.get('plan_id')),
            None if replaces is None else parse.plan_ids(replaces, 'replaces_ids'),
            parse.optional_id(data.get('renews_id'), 'renews_id'),
        )
        return _changed(changed, row)


def _move(move):
    if not isinstance(move, dict):
        raise ValidationError({'move': ['Say which plan to move, and which way.']})
    try:
        step = int(move.get('step'))
    except (TypeError, ValueError) as exc:
        raise ValidationError({'move': ['Say which plan to move, and which way.']}) from exc
    among = move.get('among')
    return 'move', parse.plan_id(move.get('plan_id'), 'move'), step, None if among is None else parse.plan_ids(among)


def _how(data):
    if 'move' in data:
        return _move(data['move'])
    if 'swap' in data:
        pair = parse.plan_ids(data['swap'], 'swap')
        if len(pair) != 2:
            raise ValidationError({'swap': ['Name the two plans to swap.']})
        return 'swap', *pair
    if data.get('reset'):
        return ('reset',)
    raise ValidationError({'non_field_errors': ['Send move, swap or reset.']})


class OrderView(APIView):
    def post(self, request, pk):
        """{line, move: {plan_id, step, among?}} | {line, swap: [a, b]} | {line, reset: true} → {line, order}."""
        deal = get_object_or_404(Deal, pk=pk)
        line = parse.line(request)
        new_order, row = services.arrange(request.user, deal, line, _how(request.data))
        return Response({'line': line, 'order': new_order, 'activity_id': getattr(row, 'id', None)})


class SlotView(APIView):
    def post(self, request, pk):
        """{line, plan_id, at} puts the plan in plan `at`'s spot; {line, plan_id, beside?} adds it beside a current
        plan (F45, F46)."""
        deal = get_object_or_404(Deal, pk=pk)
        data, line = request.data, parse.line(request)
        changed, new_order, row = services.put_in_slot(
            request.user,
            deal,
            line,
            parse.plan_id(data.get('plan_id')),
            at=parse.optional_id(data.get('at'), 'at'),
            beside=parse.optional_id(data.get('beside'), 'beside'),
        )
        return _changed(changed, row, line=line, order=new_order)


class PairView(APIView):
    def post(self, request, pk):
        """{plan_ids: [first, second]}: print the second as one column with the first (D-219, J15); {plan_ids: [id],
        split: true}: take the pair holding it apart. A refusal answers 409 with its sentence; a pair made again
        writes nothing (no plans, no row)."""
        deal = get_object_or_404(Deal, pk=pk)
        ids = parse.plan_ids(request.data.get('plan_ids'))
        if request.data.get('split') is True:
            if len(ids) != 1:
                raise ValidationError({'plan_ids': ['Give the one plan whose pair to split.']})
            return _changed(*services.split_pair(request.user, deal, ids[0]))
        if len(ids) != 2:
            raise ValidationError({'plan_ids': ['Give the two plans to print as one column.']})
        return _changed(*services.pair_plans(request.user, deal, ids[0], ids[1]))
