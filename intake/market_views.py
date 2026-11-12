"""The go-to-market gate's doors (plan.md §7.6; B26, B27, B29, B33, B34): the checklist's controls, the BOR
e-signature and Mark as marketed. Thin: parse → service → answer with what the screen redraws (the gate's blocks, read
fresh) and the Activity id for Undo.
"""

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from . import selectors, services
from .services.checklist import UNSET
from .views import _body, _deal


def _gate(pk):
    return selectors.gate_of(Deal.objects.get(pk=pk))


def _flag(data, key):
    value = data.get(key, False)
    if not isinstance(value, bool):
        raise ValidationError({key: ['Send true or false.']})
    return value


class ChecklistView(APIView):
    """PATCH deals/{id}/intake/checklist/ {item, checked?, note?, requirement? ('' | required | waived),
    client_note?} — one item's tick and/or requirement (B26, B27; the Census tab's COBRA tick, C25) → {item: {key,
    label, checked, by, by_name, at, requirement}, checklist, ready, activity_id}."""

    def patch(self, request, pk):
        _deal(pk)
        data = _body(request)
        ticked = services.set_checklist_item(
            request.user,
            pk,
            data.get('item'),
            checked=data['checked'] if 'checked' in data else UNSET,
            note=data.get('note'),
            requirement=data['requirement'] if 'requirement' in data else UNSET,
            client_note=data.get('client_note', ''),
        )
        gate = _gate(pk)
        return Response(
            {
                'item': selectors.checklist_item(pk, ticked.item),
                'checklist': gate['checklist'],
                'ready': gate['ready'],
                'activity_id': ticked.activity.id if ticked.activity else None,
            }
        )


class BorView(APIView):
    """POST deals/{id}/intake/sign/ {name} — sign the BOR (B29) → {bor, ready, activity_id}; 409 on a lost deal.
    DELETE — clear the signature → 204."""

    def post(self, request, pk):
        _deal(pk)
        signed = services.sign_bor(request.user, pk, _body(request).get('name'))
        gate = _gate(pk)
        return Response(
            {'bor': gate['bor'], 'ready': gate['ready'], 'activity_id': signed.activity.id if signed.activity else None}
        )

    def delete(self, request, pk):
        _deal(pk)
        services.clear_bor(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MarketedView(APIView):
    """POST deals/{id}/intake/marketed/ {override?} — Mark as marketed, or Market anyway (B34) → {marketed, ready,
    skipped: [{kind, key, label}], activity_id}; 409 {detail, keys, gaps} while not ready and not overridden; 409 on a
    lost deal. DELETE — take "Sent to market" off → {marketed: null, ready, activity_id}."""

    def post(self, request, pk):
        _deal(pk)
        done = services.mark_marketed(request.user, pk, override=_flag(_body(request), 'override'))
        gate = _gate(pk)
        return Response(
            {
                'marketed': gate['marketed'],
                'ready': gate['ready'],
                'skipped': done.skipped,
                'activity_id': done.activity.id if done.activity else None,
            }
        )

    def delete(self, request, pk):
        _deal(pk)
        done = services.unmark_marketed(request.user, pk)
        gate = _gate(pk)
        return Response(
            {
                'marketed': gate['marketed'],
                'ready': gate['ready'],
                'activity_id': done.activity.id if done.activity else None,
            }
        )
