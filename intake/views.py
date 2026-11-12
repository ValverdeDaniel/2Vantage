"""Intake API (plan.md §7.6): the intake payload, the coverage rows and the intent door. Thin: parse → service or
selector → respond. The form's PATCH arrives in slice 39; the checklist, BOR and Mark as marketed in slice 40."""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from . import selectors, services
from .models import CurrentCoverage

MAX_ID = 2**63 - 1  # a bigger id is not a row: 404, never a database error
INTENT_KEYS = ('line', 'lines', 'has_today', 'this_year', 'shop', 'remove')


def _deal(pk):
    if pk > MAX_ID:
        raise Http404
    return get_object_or_404(Deal, pk=pk)


def _coverage_row(coverage_id):
    if coverage_id > MAX_ID:
        raise Http404
    return get_object_or_404(CurrentCoverage, pk=coverage_id)


def _body(request):
    if not isinstance(request.data, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    return request.data


def _intent_answer(deal_id, activity_row):
    """What the intent doors answer: the card and the rows as they now stand, the lines to quote, the Activity id."""
    deal = Deal.objects.get(pk=deal_id)
    payload = selectors.intake_payload(deal)
    return Response(
        {
            'intent': payload['intent'],
            'coverage': payload['coverage'],
            'requested_lines': deal.requested_lines,
            'activity_id': activity_row.id if activity_row else None,
        }
    )


class IntakeView(APIView):
    """GET deals/{id}/intake/ — the intake payload; a deal with no Intake row reads as empty."""

    def get(self, request, pk):
        return Response(selectors.intake_payload(_deal(pk)))


class IntentView(APIView):
    """POST deals/{id}/intake/intent/ {line | lines, has_today?, this_year?, shop?, remove?} (B16–B19, B32)."""

    def post(self, request, pk):
        _deal(pk)
        data = _body(request)
        controls = {key: data[key] for key in INTENT_KEYS if key in data and key != 'remove'}
        if 'line' not in data and 'lines' not in data:
            raise ValidationError({'line': ['Name the line of coverage.']})
        remove = data.get('remove', False)
        if not isinstance(remove, bool):
            raise ValidationError({'remove': ['Send true or false.']})
        changed = services.set_intent(request.user, pk, remove=remove, **controls)
        return _intent_answer(pk, changed.activity)


class ConfirmIntentView(APIView):
    """POST deals/{id}/intake/intent/confirm/ — Confirm coverage & intent, or Confirm again (B20)."""

    def post(self, request, pk):
        _deal(pk)
        return _intent_answer(pk, services.confirm_intent(request.user, pk))


class ReopenIntentView(APIView):
    """POST deals/{id}/intake/intent/reopen/ — Reopen (B20)."""

    def post(self, request, pk):
        _deal(pk)
        return _intent_answer(pk, services.reopen_intent(request.user, pk))


class CoverageListView(APIView):
    """GET deals/{id}/coverage/ — the rows; POST one row (B14, B19) → 201 the row."""

    def get(self, request, pk):
        deal = _deal(pk)
        return Response(selectors.intake_payload(deal)['coverage'])

    def post(self, request, pk):
        _deal(pk)
        written = services.create_coverage(request.user, pk, _body(request))
        return Response(selectors.one_coverage_row(written.row), status=status.HTTP_201_CREATED)


class CoverageView(APIView):
    """PATCH coverage/{id}/ → the row (400 for carrier or funding once the line has current plans); DELETE → 204."""

    def patch(self, request, coverage_id):
        _coverage_row(coverage_id)
        written = services.update_coverage(request.user, coverage_id, _body(request))
        return Response(selectors.one_coverage_row(written.row))

    def delete(self, request, coverage_id):
        _coverage_row(coverage_id)
        services.delete_coverage(request.user, coverage_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
