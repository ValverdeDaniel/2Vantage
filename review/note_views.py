"""Review & requests API for notes, the tray and the request page (plan.md §7.13; L22, L33, L49–L53; B12). Thin: parse →
service → answer with what the screen redraws. Ids from the path are integers (past bigint, or on another deal: 404).

- POST deals/{id}/review/notes/ {kind: note, ref, text, audience: team | client} | {kind: reply, question_id, text}
  → 201 {note, activity_id}; {kind: ask | sendback, ref | refs, text?, request_id?} → 201 {tray, activity_id}.
- PATCH deals/{id}/review/notes/{nid}/ {action: resolve} → {note, activity_id}; DELETE (a draft) → {tray}.
- GET  deals/{id}/review/tray/ → the tray (selectors/tray.py). POST {refs, kind?, text?, request_id?, skip_out?} or
  {census: {columns, scope: blank | missing}} → 201 {tray, added, activity_id}.
- POST deals/{id}/review/tray/remove/ {ids} → {removed, tray}.
- POST deals/{id}/review/tray/send/ {ids?, request_id?, new?: {people, security?, expires_on?, message?, blank?}}
  → {sent, targets, waiting, whys, dropped, request?, links?, tray}; `links` (a new link's, with its PIN this once).
- POST deals/{id}/review/seen/ {at?} → {seen_at}: this person's last look (L33).
- GET  deals/{id}/review/request/?pane=intake | census | documents[&request=<id>] → the request page
  (selectors/request_page.py); with `request`, the Ask card's `target` (slice 57).
400 {field: [sentence]}; 409 {detail} (a deal that may no longer ask its client, nothing to send, no link for a note).
"""

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals import clock

from .selectors import notes as note_rows
from .selectors import request_page
from .selectors import requests as request_rows
from .selectors import tray as tray_selector
from .services import notes, seen, send, tray
from .views import MAX_ID, _activity_id, _body, _deal, _made

PANES = ('intake', 'census', 'documents')


def _tray(deal):
    return tray_selector.tray(deal)


def _ask(request, deal, data):
    refs = data.get('refs') if 'refs' in data else [data.get('ref')]
    asked = tray.ask(
        request.user, deal.id, refs, kind=data.get('kind') or 'ask', text=data.get('text') or '',
        request_id=data.get('request_id'), skip_out=data.get('skip_out') is True,
    )  # fmt: skip
    answer = {'tray': _tray(deal), 'added': len(asked.drafts), 'activity_id': _activity_id(asked.activity)}
    return Response(answer, status=status.HTTP_201_CREATED)


class NotesView(APIView):
    def post(self, request, pk):
        deal = _deal(pk)
        data = _body(request)
        kind = data.get('kind') or 'note'
        if kind in ('ask', 'sendback'):
            return _ask(request, deal, data)
        if kind == 'reply':
            done = notes.reply(request.user, deal.id, data.get('question_id'), data.get('text'))
        elif kind == 'note':
            done = notes.add(
                request.user, deal.id, data.get('ref'), data.get('text'), audience=data.get('audience') or 'team'
            )
        else:
            raise ValidationError({'kind': ['Send kind as note, reply, ask or sendback.']})
        answer = {'note': note_rows.payload(done.note), 'activity_id': _activity_id(done.activity)}
        return Response(answer, status=status.HTTP_201_CREATED)


class NoteView(APIView):
    def patch(self, request, pk, nid):
        deal = _deal(pk)
        if nid > MAX_ID:
            raise Http404
        if _body(request).get('action') != 'resolve':
            raise ValidationError({'action': ['Send action: resolve.']})
        done = notes.resolve(request.user, deal.id, nid)
        return Response({'note': note_rows.payload(done.note), 'activity_id': _activity_id(done.activity)})

    def delete(self, request, pk, nid):
        deal = _deal(pk)
        if nid > MAX_ID:
            raise Http404
        notes.drop(request.user, deal.id, nid)
        return Response({'tray': _tray(deal)})


class TrayView(APIView):
    def get(self, request, pk):
        return Response(_tray(_deal(pk)))

    def post(self, request, pk):
        deal = _deal(pk)
        data = _body(request)
        census = data.get('census')
        if census is None:
            return _ask(request, deal, data)
        if not isinstance(census, dict):
            raise ValidationError({'census': ['Send the census columns as {columns, scope}.']})
        asked = tray.ask_census(
            request.user, deal.id, census.get('columns'), scope=census.get('scope') or 'blank', text=data.get('text')
        )
        answer = {'tray': _tray(deal), 'added': len(asked.drafts), 'activity_id': _activity_id(asked.activity)}
        return Response(answer, status=status.HTTP_201_CREATED)


class TrayRemoveView(APIView):
    def post(self, request, pk):
        deal = _deal(pk)
        removed = tray.remove(request.user, deal.id, _body(request).get('ids'))
        return Response({'removed': removed.ids, 'tray': _tray(deal)})


class TraySendView(APIView):
    def post(self, request, pk):
        deal = _deal(pk)
        data = _body(request)
        done = send.send(
            request.user, deal.id, ids=data.get('ids'), request_id=data.get('request_id'), new=data.get('new')
        )
        answer = {
            'sent': done.sent,
            'targets': done.targets,
            'waiting': done.waiting,
            'whys': {str(note_id): why for note_id, why in done.whys.items()},
            'dropped': done.dropped,
            'tray': _tray(deal),
        }
        if done.created is not None:
            answer['request'] = request_rows.one(done.created.request.id, clock.now())
            answer['links'] = [_made(*made) for made in done.created.links]
        return Response(answer)


class SeenView(APIView):
    def post(self, request, pk):
        deal = _deal(pk)
        return Response({'seen_at': seen.mark(deal.id, user=request.user, at=_body(request).get('at')).isoformat()})


class RequestPageView(APIView):
    def get(self, request, pk):
        deal = _deal(pk)
        pane = request.query_params.get('pane') or 'intake'
        if pane not in PANES:
            raise ValidationError({'pane': [f'Name the tab as one of: {", ".join(PANES)}.']})
        raw = request.query_params.get('request') or ''
        if raw and (not raw.isdigit() or len(raw) > 18):
            raise ValidationError({'request': ['Send the request as a number.']})
        return Response(request_page.page(deal, pane, request.user, request_id=int(raw) if raw else None))
