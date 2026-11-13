"""Review & requests API, staff side (plan.md §7.13; L.6 endpoints). Thin: parse → service → answer with what the
screen redraws. Ids come from the path as integers; past bigint, or not on that deal, they answer 404 (B4).

- GET  deals/{id}/review/board/[?scope=intake|census] → the Board (selectors/board.py), or one section's own (L45).
- GET  deals/{id}/review/requests/ → {requests: [row]}: every request and link ever made (People & links, L38).
- POST deals/{id}/review/requests/[?dry_run=1] {people, asks, message?, security?, expires_on?, blank?}
  → 201 {request: row, links: [{link_id, name, email, path, pin, security, expires_at}], activity_id}; the dry run
  → 200 {floor: {level, because}, security, people, asks: [words], numbers} (the builder's live numbers, slice
  57). 400 {field: [sentence]}; 409 {detail}.
- POST deals/{id}/review/requests/{rid}/close/ {reason} → {request: row, changed, activity_id}.
- PATCH links/{lid}/ {action, copied?} → {link: recipient, request: row, changed, activity_id, pin?} (pin only from
  `new_pin`, this once). Slice 57's actions take a value: `expiry` {day}, `blank` {blank}, `address` {email}, `nudge`
  {day | null}, `nudge_done` (`services.link_settings`). 400 for an unknown action; 409 {detail} for a refusal.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals import clock
from deals.models import Deal

from . import services, words
from .models import ClientLink, ClientRequest
from .rules import ask_words
from .selectors import board as board_selector
from .selectors import drafted
from .selectors import requests as request_rows
from .services import link_settings

MAX_ID = 2**63 - 1  # a bigger id is not a row: 404, never a database error


def _deal(pk):
    if pk > MAX_ID:
        raise Http404
    return get_object_or_404(Deal.objects.select_related('client'), pk=pk)


def _body(request):
    if not isinstance(request.data, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    return request.data


def _activity_id(row):
    return row.id if row else None


SCOPES = ('intake', 'census')


class BoardView(APIView):
    def get(self, request, pk):
        scope = request.query_params.get('scope') or None
        if scope is not None and scope not in SCOPES:
            raise ValidationError({'scope': [f'Name the section as one of: {", ".join(SCOPES)}.']})
        return Response(board_selector.board(_deal(pk), scope=scope))


def _made(link, path, pin):
    return {
        'link_id': link.id,
        'name': link.name,
        'email': link.email,
        'path': path,
        'pin': pin,
        'security': link.security,
        'expires_at': link.expires_at.isoformat(),
    }


class RequestsView(APIView):
    def get(self, request, pk):
        deal = _deal(pk)
        return Response({'requests': request_rows.rows([deal.id], clock.now()).get(deal.id, [])})

    def post(self, request, pk):
        deal = _deal(pk)
        data = _body(request)
        if request.query_params.get('dry_run') in ('1', 'true'):
            planned = services.create(request.user, deal.id, data, dry_run=True)
            return Response(
                {
                    'floor': planned.floor,
                    'security': planned.security,
                    'people': len(planned.people),
                    'asks': ask_words.words(planned.asks),
                    'numbers': drafted.numbers(deal, planned.asks, blank=planned.blank),
                }
            )
        created = services.create(request.user, deal.id, data)
        answer = {
            'request': request_rows.one(created.request.id, clock.now()),
            'links': [_made(*made) for made in created.links],
            'activity_id': _activity_id(created.activity),
        }
        return Response(answer, status=status.HTTP_201_CREATED)


class CloseView(APIView):
    def post(self, request, pk, rid):
        deal = _deal(pk)
        if rid > MAX_ID or not ClientRequest.objects.filter(pk=rid, deal=deal).exists():
            raise Http404
        closed = services.close(request.user, rid, _body(request).get('reason'))
        return Response(
            {
                'request': request_rows.one(rid, clock.now()),
                'changed': closed.changed,
                'activity_id': _activity_id(closed.activity),
            }
        )


class LinkView(APIView):
    def patch(self, request, lid):
        if lid > MAX_ID or not ClientLink.objects.filter(pk=lid).exists():
            raise Http404
        data = _body(request)
        name = data.get('action')
        action = services.ACTIONS.get(name) if isinstance(name, str) else None
        setting = link_settings.ACTIONS.get(name) if isinstance(name, str) else None
        if action is None and setting is None:
            every = [*services.ACTIONS, *link_settings.ACTIONS]
            raise ValidationError({'action': [words.UNKNOWN_ACTION.format(actions=', '.join(every))]})
        if setting is not None:
            acted = setting(request.user, lid, data)
        elif action is services.mark_sent:
            acted = action(request.user, lid, copied=data.get('copied') is True)
        else:
            acted = action(request.user, lid)
        row = request_rows.one(acted.request.id, clock.now())
        answer = {
            'link': next(person for person in row['recipients'] if person['link_id'] == lid),
            'request': row,
            'changed': acted.changed,
            'activity_id': _activity_id(acted.activity),
        }
        if acted.pin:
            answer['pin'] = acted.pin
        return Response(answer)
