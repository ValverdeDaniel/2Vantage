"""The chat API (plan.md §7.5; D7, D19, D25, D77, D100, D104; slice 24).

GET `deals/{id}/ai/chats/` → {chats, open, window} · PATCH `ai/chats/{id}/` {title} → the chat · GET
`ai/chats/{id}/messages/?before=` → {chat, messages, more} · POST `deals/{id}/ai/messages/` {text, chat_id?,
document_ids?, tab?, board?, viewer?, model?, budget_override?} → 201 {chat_id, message, job, queue_position} ·
PATCH `deals/{id}/ai/` {locked?, budget_usd?} → the state (only admins change the budget, OQ34). Any signed-in person
may chat on any deal (OQ3). Ids from the path or the body are read as ints: a bad one answers 400 or 404, never 500.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import chat_selectors, selectors
from .models import Chat, Job
from .services import chats, deal_ai
from .views import MAX_ID, _deal, _ids, _job, _model


def _chat(chat_id):
    if chat_id > MAX_ID:
        raise Http404
    return get_object_or_404(Chat, pk=chat_id)


def _optional_id(raw, name):
    if raw in (None, ''):
        return None
    if isinstance(raw, bool):
        raise ValidationError({name: ['Give an id.']})
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: ['Give an id.']}) from exc
    if not 0 < value <= MAX_ID:
        raise ValidationError({name: ['Give an id.']})
    return value


class ChatsView(APIView):
    def get(self, request, pk):
        return Response(chat_selectors.chats(_deal(pk), request.user))


class ChatView(APIView):
    def patch(self, request, chat_id):
        chat, _changed = chats.rename_chat(request.user, _chat(chat_id).id, request.data.get('title'))
        return Response({'id': chat.id, 'title': chat_selectors.title(chat), 'named': bool(chat.title)})


class MessagesView(APIView):
    def get(self, request, chat_id):
        before = _optional_id(request.query_params.get('before'), 'before')
        return Response(chat_selectors.messages(_chat(chat_id), before))


class SendView(APIView):
    def post(self, request, pk):
        deal = _deal(pk)
        data = request.data
        tab = data.get('tab') or ''
        if not isinstance(tab, str):
            raise ValidationError({'tab': ['Name a tab.']})
        raw_ids = data.get('document_ids')
        chat, message, job = chats.send_message(
            request.user,
            deal,
            text=data.get('text') if isinstance(data.get('text'), str) else '',
            chat_id=_optional_id(data.get('chat_id'), 'chat_id'),
            document_ids=_ids(raw_ids) if raw_ids not in (None, []) else [],
            tab=tab,
            board=data.get('board'),
            viewer=data.get('viewer'),
            model=_model(data),
            budget_override=data.get('budget_override') is True,
        )
        job = _job(job.id)
        place = None
        if job.status == 'queued':
            place = Job.objects.filter(deal=deal, lane=job.lane, status='queued', id__lte=job.id).count()
        body = {
            'chat_id': chat.id,
            'message': chat_selectors.message(message),
            'job': selectors.job_light(job, place),
            'queue_position': place,
        }
        return Response(body, status=status.HTTP_201_CREATED)


def patch_settings(request, deal):
    """PATCH deals/{id}/ai/: the lock and the budget, then the state."""
    data = request.data if isinstance(request.data, dict) else {}
    unknown = set(data) - {'locked', 'budget_usd'}
    if unknown:
        raise ValidationError({key: ['Only locked and budget_usd can be changed here.'] for key in unknown})
    rows = []
    if 'locked' in data:
        rows.append(deal_ai.set_lock(request.user, deal, data['locked']))
    if 'budget_usd' in data:
        rows.append(deal_ai.set_budget(request.user, deal, data['budget_usd']))
    written = [row.id for row in rows if row is not None]
    return Response({**selectors.deal_state(deal, request.user), 'activity_ids': written})
