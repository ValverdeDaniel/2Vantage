"""Intake API (plan.md §7.6): the intake payload and the answers PATCH, one answer's source (slice 65), the coverage
rows and the intent door. Thin: parse → service or selector → respond. The gate's doors — the checklist, the BOR and
Mark as marketed (slice 40) — are `market_views.py`."""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from . import form, providers, selectors, services
from .models import CurrentCoverage, Intake

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


def _answered(deal_id, answered):
    """The answers PATCH's reply (§7.6): the answers and sources that changed (null: cleared), then the form's state
    as it now stands, so the form re-reads nothing after a save."""
    deal = Deal.objects.get(pk=deal_id)
    intake = Intake.objects.filter(deal_id=deal_id).first()
    shown = selectors.answers_of(deal, intake)
    rows = list(CurrentCoverage.objects.filter(deal_id=deal_id).order_by('sort_order', 'id'))
    state = selectors.form_state(deal, intake, rows, providers.quote_lines(deal_id))
    return {
        'answers': {key: shown.get(key) for key in answered.changed},
        'sources': answered.sources,
        **state,
        'effective_date': deal.effective_date,
        'activity_id': answered.activity.id if answered.activity else None,
    }


class IntakeView(APIView):
    """GET deals/{id}/intake/ — the intake payload; a deal with no Intake row reads as empty.
    PATCH {answers: {key: raw}, expect?: {key: value seen}, relay?: bool} — the form's answers, all or nothing (B4)."""

    def get(self, request, pk):
        return Response(selectors.intake_payload(_deal(pk)))

    def patch(self, request, pk):
        _deal(pk)
        data = _body(request)
        relay = data.get('relay', False)
        if not isinstance(relay, bool):
            raise ValidationError({'relay': ['Send true or false.']})
        answered = services.update_answers(
            request.user, pk, data.get('answers'), expect=data.get('expect'), origin='relay' if relay else 'typed'
        )
        return Response(_answered(pk, answered))


class SourceView(APIView):
    """GET deals/{id}/intake/source/?key= → {key, label, value, hint, what, source}: where one answer was read, so ↗
    and the Documents station's intake view open it in its file (E18, E44; slice 65). Read only."""

    def get(self, request, pk):
        deal = _deal(pk)
        key = request.query_params.get('key') or ''
        if key not in form.ANSWER_KEYS:
            raise ValidationError({'key': ['Give a question of the intake form.']})
        return Response(selectors.value_source(deal, key))


class MarksView(APIView):
    """POST deals/{id}/intake/marks/ {action: approve|ignore|check|clear, refs?: ["intake:<key>"]} (B10, B11; E.6):
    refs name exactly those answers; none takes the shown answers' open warnings (for clear, their marks). Answers
    {action, changed, activity_id, sources: {key: entry}, status, flags}."""

    def post(self, request, pk):
        _deal(pk)
        data = _body(request)
        marked = services.mark_answers(request.user, pk, data.get('action'), refs=data.get('refs'))
        deal = Deal.objects.get(pk=pk)
        intake = Intake.objects.filter(deal_id=pk).first()
        rows = list(CurrentCoverage.objects.filter(deal_id=pk).order_by('sort_order', 'id'))
        state = selectors.form_state(deal, intake, rows, providers.quote_lines(pk))
        return Response(
            {
                'action': marked.action,
                'changed': len(marked.keys),
                'activity_id': marked.row.id if marked.row else None,
                'sources': marked.sources,
                'status': state['status'],
                'review': state['review'],
            }
        )


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
