"""Proposal API (plan.md §7.12): the builder (GET, and PATCH by path), its card marks, and "What the client will see",
the page split (slice 14)."""

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal
from quotes import board_presets, parse

from . import builder, page_cells, pages_read, services


class ProposalView(APIView):
    def get(self, request, pk):
        return Response(builder.payload(get_object_or_404(Deal, pk=pk)))

    def patch(self, request, pk):
        """{path: value} → {changed: {path: value}, cleared: [mark paths], activity_id}."""
        deal = get_object_or_404(Deal, pk=pk)
        written = services.set_config(request.user, deal, request.data)
        return Response(
            {
                'changed': written.changed,
                'cleared': written.cleared,
                'activity_id': written.activity.id if written.activity else None,
            }
        )


class MarksView(APIView):
    def post(self, request, pk):
        """{card, line?, done} → {card, line, stamp: {by, at} | null, activity_id}."""
        deal = get_object_or_404(Deal, pk=pk)
        card, line = str(request.data.get('card') or ''), str(request.data.get('line') or '')
        keys, _states, _off, _found = builder.proposal_lines(deal)
        stamp, row = services.set_mark(request.user, deal, card, line, request.data.get('done'), keys)
        return Response({'card': card, 'line': line or None, 'stamp': stamp, 'activity_id': row.id if row else None})


class PagesView(APIView):
    def get(self, request, pk):
        """?line= (required) and ?preset= (the Advisor's Columns tab, or the builder's Key rows; Primary by default)."""
        deal = get_object_or_404(Deal, pk=pk)
        line = parse.line(request)
        preset = request.query_params.get('preset') or board_presets.DEFAULT_PRESET
        if preset not in page_cells.PRESETS:
            raise ValidationError({'preset': ['Give a column preset: ' + ', '.join(page_cells.PRESETS) + '.']})
        return Response(pages_read.payload(deal, line, preset))
