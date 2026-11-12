"""Questionnaire API (plan.md §7.9; G.6 endpoints). Thin: parse → service or selector → respond.

Every write answers the form's payload as it now stands (or the deal's forms, for the choice), so the tab re-reads
nothing after a save; `activity_id` names the Activity row for Undo. Refusals answer 409 with a sentence; a bad body
400; an unknown deal, form, block or row 404. The spec is the only cached answer (`private, max-age`, §7.14).
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from . import services
from .selectors import payload, sources
from .services.common import form_or_404
from .spec_payload import spec

MAX_ID = 2**63 - 1
SPEC_CACHE = 'private, max-age=3600'


def _deal(pk):
    if pk > MAX_ID:
        raise Http404
    return get_object_or_404(Deal.objects.select_related('client'), pk=pk)


def _body(request):
    if not isinstance(request.data, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    return request.data


def _flag(data, name):
    value = data.get(name, False)
    if not isinstance(value, bool):
        raise ValidationError({name: [f'Send {name} as true or false.']})
    return value


def _answer(deal_id, form_key, row_activity=None, **extra):
    deal = _deal(deal_id)
    return {**payload.form_payload(deal, form_key), 'activity_id': row_activity.id if row_activity else None, **extra}


class SpecView(APIView):
    """GET meta/questionnaires/{form}/ — the form's spec, cached per version."""

    def get(self, request, form):
        form_or_404(form)
        response = Response(spec(form))
        response['Cache-Control'] = SPEC_CACHE
        return response


class DealFormsView(APIView):
    """GET deals/{id}/questionnaires/ — the deal's forms (chips), both items resolved, the band."""

    def get(self, request, pk):
        return Response(payload.deal_forms(_deal(pk)))


class ChoiceView(APIView):
    """PATCH deals/{id}/questionnaires/choice/ {item, choice} — the item's form choice; 409 for a swap away from a
    signed form."""

    def patch(self, request, pk):
        _deal(pk)
        data = _body(request)
        ticked = services.choose_form(request.user, pk, data.get('item'), data.get('choice'))
        answer = payload.deal_forms(_deal(pk))
        return Response({**answer, 'activity_id': ticked.activity.id if ticked.activity else None})


class FormView(APIView):
    """GET deals/{id}/questionnaires/{form}/ — one form as it stands; never writes."""

    def get(self, request, pk, form):
        form_or_404(form)
        return Response(payload.form_payload(_deal(pk), form))


class AnswersView(APIView):
    """PATCH …/{form}/answers/ {answers: {slot: value}, relay?} → the form, `changed` slots and `dropped` answers."""

    def patch(self, request, pk, form):
        _deal(pk)
        form_or_404(form)
        data = _body(request)
        answered = services.set_answers(request.user, pk, form, data.get('answers'), relay=_flag(data, 'relay'))
        changed = sorted({key.removeprefix('cleared:') for key in answered.changed})
        return Response(_answer(pk, form, answered.activity, changed=changed, dropped=answered.dropped))


class RowsView(APIView):
    """POST …/{form}/rows/{block}/ — add a row (201, with its id); 400 past the block's maximum."""

    def post(self, request, pk, form, block):
        _deal(pk)
        form_or_404(form)
        changed = services.add_row(request.user, pk, form, block)
        return Response(_answer(pk, form, changed.activity, row_id=changed.row_id), status=status.HTTP_201_CREATED)


class RowView(APIView):
    """DELETE …/{form}/rows/{block}/{row_id}/ — remove a row; 404 for an unknown row, 400 below the minimum."""

    def delete(self, request, pk, form, block, row_id):
        _deal(pk)
        form_or_404(form)
        if row_id > MAX_ID:
            raise Http404
        changed = services.remove_row(request.user, pk, form, block, row_id)
        return Response(_answer(pk, form, changed.activity))


class SignView(APIView):
    """POST …/{form}/sign/ {who, name, authorized, sign_anyway} — 400 without the officer's authorization; 409 for
    blanks (with `incomplete`), a lost deal or a signature on file."""

    def post(self, request, pk, form):
        _deal(pk)
        form_or_404(form)
        data = _body(request)
        signed = services.sign(
            request.user, pk, form, data.get('who'), data.get('name'),
            authorized=_flag(data, 'authorized'), sign_anyway=_flag(data, 'sign_anyway'),
        )  # fmt: skip
        return Response(_answer(pk, form, signed.activity))


class ReopenView(APIView):
    """POST …/{form}/reopen/ {reason} — reopen a signed form (G54, OQ55)."""

    def post(self, request, pk, form):
        _deal(pk)
        form_or_404(form)
        reopened = services.reopen(request.user, pk, form, _body(request).get('reason'))
        return Response(_answer(pk, form, reopened.activity))


class SourcesView(APIView):
    """GET …/{form}/sources/ — the answers with their sources and marks (E103)."""

    def get(self, request, pk, form):
        form_or_404(form)
        return Response(sources.source_rows(_deal(pk), form))


class MarksView(APIView):
    """POST …/{form}/marks/ {action, refs?} — approve, ignore, needs checking or clear (E103)."""

    def post(self, request, pk, form):
        _deal(pk)
        form_or_404(form)
        data = _body(request)
        marked = services.mark_answers(request.user, pk, form, data.get('action'), refs=data.get('refs'))
        return Response(_answer(pk, form, marked.activity, marked=marked.slots))
