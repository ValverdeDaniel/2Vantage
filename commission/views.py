"""Commission API for the deal and the client (plan.md §7.10; H3–H24, H25–H37, H106, H108). Thin: parse → service →
answer with what the screen redraws. Any deal user reads the tab, edits the rates and previews a split (H102); saving
a split is the all tier's or the owner's (OQ70), which the service checks; booking and the CAA disclosure are the all
tier's. Producers & partners and Settings are in `people_views`, the Book and By person in `record_views`.
"""

from decimal import Decimal, InvalidOperation

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access import commission_tier
from deals import activity
from deals.models import Client, Deal

from . import disclosure, disclosure_pdf, parties, rules, selectors, services
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


ALL_ONLY = 'Only someone with all commission access can do this.'


def _all_tier(request):
    if commission_tier(request.user) != 'all':
        raise PermissionDenied(ALL_ONLY)


class DealBookView(APIView):
    """POST deals/{id}/commission/book/ → {booked: [record ids], changed: [targets], activity_id, …payload}: Book now,
    Update and Rebook (H25, H36, H120); the all tier; 409 on a lost deal (H124)."""

    def post(self, request, pk):
        deal_or_404(pk)
        _all_tier(request)
        written = services.rebook(request.user, pk)
        payload = selectors.deal_payload(deal_or_404(pk), request.user)
        activity_id = written.activity.id if written.activity else None
        changed = [entry['t'] for entry in written.changes]
        booked = [record.id for record in written.records]
        return Response({'booked': booked, 'changed': changed, 'activity_id': activity_id, **payload})


def _slug(text):
    return ''.join(ch if ch.isalnum() else '-' for ch in str(text).lower()).strip('-')[:40] or 'client'


class DealDisclosureView(APIView):
    """GET deals/{id}/commission/disclosure.pdf → the CAA comp disclosure (H108; all tier), built from the deal's booked
    medical, dental and vision records; 409 when none is booked. The download is logged (§3.8)."""

    def get(self, request, pk):
        deal = deal_or_404(pk)
        _all_tier(request)
        found = disclosure.data(deal)
        if not found['has_records']:
            raise activity.Refused(disclosure.NOTHING_BOOKED)
        content = disclosure_pdf.build(found)
        activity.log_access(deal, request.user, 'downloaded', 'the comp disclosure', None, area='commission')
        year = deal.effective_date.year if deal.effective_date else 'year'
        response = HttpResponse(content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="comp-disclosure-{_slug(deal.client.name)}-{year}.pdf"'
        return response
