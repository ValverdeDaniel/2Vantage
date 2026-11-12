"""Commission API for the deal and the client (plan.md §7.10; H3–H24, H106). Thin: parse → service → answer with what
the screen redraws. Any deal user reads the tab, edits the rates and previews a split (H102); saving a split is the
all tier's or the owner's (OQ70), which the service checks. Producers & partners and Settings are in `people_views`.
"""

from decimal import Decimal, InvalidOperation

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Client, Deal

from . import parties, rules, selectors, services
from .models import Settings

MAX_ID = 2**63 - 1  # a bigger id is not a row: 404, never a database error
BAD_NUMBER = 'Send a number, or null.'


def deal_or_404(pk):
    if pk > MAX_ID:
        raise Http404
    return get_object_or_404(Deal.objects.select_related('client'), pk=pk)


def client_or_404(pk):
    if pk > MAX_ID:
        raise Http404
    return get_object_or_404(Client, pk=pk)


def body(request):
    if not isinstance(request.data, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    return request.data


def _number(data, key, kind, errors):
    raw = data.get(key)
    if raw in (None, ''):
        return None
    try:
        if isinstance(raw, bool):
            raise ValueError
        value = Decimal(str(raw)) if kind is Decimal else int(str(raw))
    except (InvalidOperation, ValueError):
        errors[key] = [BAD_NUMBER]
        return None
    if value < 0 or (kind is Decimal and not value.is_finite()):
        errors[key] = [BAD_NUMBER]
        return None
    return value


def preview_answer(data, revenue_total=None, employees=None, year=1, from_body=True):
    """{'preview': …} for the rows in `data`, on the basis the GET returned (H18: the body carries it, so the line
    states are not worked out again on every keystroke). 400 with the save's own errors."""
    errors = {}
    if from_body:
        revenue_total = _number(data, 'revenue', Decimal, errors)
        employees = _number(data, 'employees', int, errors)
        year = _number(data, 'year', int, errors) or None
    people = parties.lookup(parties.people())
    rows, problems = rules.validate_rows(data.get('rows'), people)
    errors.update({key: [sentence] for key, sentence in problems.items()})
    if errors:
        raise ValidationError(errors)
    return {'preview': selectors.preview(rows, people, Settings.get(), revenue_total, employees, year)}


class DealCommissionView(APIView):
    """GET deals/{id}/commission/ → the tab's payload (selectors.deal_payload).
    PATCH {rates?: {line: Comp | '' }, year_number?: int | null} → {changed: {key: [before, after]}, activity_id,
    …payload}; 400 {'rates.<line>' | 'year_number': [sentence]}."""

    def get(self, request, pk):
        return Response(selectors.deal_payload(deal_or_404(pk), request.user))

    def patch(self, request, pk):
        deal_or_404(pk)
        written = services.update(request.user, pk, body(request))
        payload = selectors.deal_payload(deal_or_404(pk), request.user)
        activity_id = written.activity.id if written.activity else None
        return Response({'changed': written.changed, 'activity_id': activity_id, **payload})


class DealSplitView(APIView):
    """PUT deals/{id}/commission/split/ {scope: deal | client, rows: [Row]} → {saved, activity_id, owner, …payload};
    400 {'rows.<i>.<field>' | 'rows.primary' | 'rows.split_total' | 'scope': [sentence]}; 403 for anyone but the all
    tier and the deal's owner (OQ70)."""

    def put(self, request, pk):
        deal_or_404(pk)
        data = body(request)
        saved = services.save_split(request.user, deal_id=pk, scope=data.get('scope') or 'deal', rows=data.get('rows'))
        payload = selectors.deal_payload(deal_or_404(pk), request.user)
        activity_id = saved.activity.id if saved.activity else None
        return Response({'saved': bool(saved.changed), 'activity_id': activity_id, 'owner': saved.owner, **payload})


class DealSplitPreviewView(APIView):
    """POST deals/{id}/commission/split/preview/ {rows, revenue, employees, year} (the basis the GET returned) →
    {preview: {year, first_year, year_label, producer_pct, house_pct, pct_source, revenue, employees, shares: [{key,
    name, role, share (millionths), pct, amount}]}}; 400 as the save. Writes nothing."""

    def post(self, request, pk):
        deal_or_404(pk)
        return Response(preview_answer(body(request)))


class ClientSplitView(APIView):
    """GET clients/{id}/commission/split/ → the client's split (selectors.client_payload; H106).
    PUT {rows} → {saved, activity_id, owner, …payload}; 403 for anyone but the all tier and the client's owner."""

    def get(self, request, pk):
        return Response(selectors.client_payload(client_or_404(pk), request.user))

    def put(self, request, pk):
        client_or_404(pk)
        saved = services.save_split(request.user, client_id=pk, rows=body(request).get('rows'))
        payload = selectors.client_payload(client_or_404(pk), request.user)
        activity_id = saved.activity.id if saved.activity else None
        return Response({'saved': bool(saved.changed), 'activity_id': activity_id, 'owner': saved.owner, **payload})


class ClientSplitPreviewView(APIView):
    """POST clients/{id}/commission/split/preview/ {rows} → {preview} in percentages (no revenue at the client level;
    the first year until slice 49's records count)."""

    def post(self, request, pk):
        client_or_404(pk)
        return Response(preview_answer(body(request), from_body=False))
