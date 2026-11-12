"""Chats: sending a message and naming a chat (plan.md §7.5, §10.6; D7, D19, D77, D82; slice 24).

- `send_message` stores the person's words in a chat (a new one on its first message, numbered under the deal's
  DealAi row, so an unsent "＋ New chat" leaves nothing) and starts the turn that answers it, in the chat lane: a
  question never waits behind a read. With a turn still running on the deal, the new one queues behind it. It carries
  what the person's tab shows (`page`: the tab, the Advisor's board, the open file) and at most three attached files.
  Refused without Claude (409, D26); Opus 5.5 and Run anyway only for admins and direct people (409, D9, D24).
- `rename_chat` names a chat for everyone on the deal ('' gives back "Chat N").
Chats and messages are the AI's own working record, as jobs are, not deal data: they record no Activity. What a turn
changes on the deal is recorded by the owners that land it.
"""

import json

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import clock
from deals.activity import Refused
from deals.models import Deal
from documents.models import Document

from .. import client, kinds, pricing, reading, turn_files
from ..models import Chat, ChatMessage, DealAi
from .jobs import NO_OPUS, NO_OVERRIDE, start

MAX_TEXT = 8000
MAX_TITLE = 80
MAX_PAGE = 20_000  # characters of the tab's state (the board's config and shown plans)
TABS = ('overview', 'agenda', 'review', 'intake', 'census', 'questionnaire', 'rfp', 'commission', 'advisor',
        'proposal', 'documents')  # fmt: skip

SAY_SOMETHING = 'Write a message for Claude.'
TOO_LONG = f'Keep a message under {MAX_TEXT:,} characters.'
NOT_THIS_DEAL = 'That chat is not on this deal.'
FILES = f'Attach at most {turn_files.MAX_ATTACHED} files to one message.'
FILES_NOT_HERE = 'Those files are not on this deal.'
MEMBER_FILES = 'Files that list members are not read in a chat.'
BAD_TAB = 'Name one of the deal’s tabs.'
BAD_PAGE = 'The page state is too large or not an object.'
TITLE_LONG = f'Keep a chat’s name under {MAX_TITLE} characters.'


def _page(tab, board, viewer):
    if tab and tab not in TABS:
        raise ValidationError({'tab': [BAD_TAB]})
    page = {'tab': tab or ''}
    for key, value in (('board', board), ('viewer', viewer)):
        if value in (None, ''):
            continue
        if not isinstance(value, dict) or len(json.dumps(value)) > MAX_PAGE:
            raise ValidationError({key: [BAD_PAGE]})
        page[key] = value
    return page


def _documents(deal, ids):
    ids = list(dict.fromkeys(ids or []))
    if len(ids) > turn_files.MAX_ATTACHED:
        raise ValidationError({'document_ids': [FILES]})
    found = {doc.id: doc for doc in Document.objects.filter(deal=deal, pk__in=ids)}
    if set(found) != set(ids):
        raise ValidationError({'document_ids': [FILES_NOT_HERE]})
    if any(not turn_files.readable(doc) for doc in found.values()):
        raise ValidationError({'document_ids': [MEMBER_FILES]})
    return ids


def _chat(deal, chat_id, user, tab):
    if chat_id is not None:
        chat = Chat.objects.select_for_update().filter(pk=chat_id, deal=deal).first()
        if chat is None:
            raise ValidationError({'chat_id': [NOT_THIS_DEAL]})
        return chat
    settings_row, _ = DealAi.objects.select_for_update().get_or_create(deal=deal)
    number = settings_row.next_chat
    settings_row.next_chat = number + 1
    settings_row.save(update_fields=['next_chat'])
    return Chat.objects.create(deal=deal, number=number, tab=tab or '', created_by=user)


def send_message(
    user,
    deal,
    *,
    text,
    chat_id=None,
    document_ids=(),
    tab='',
    board=None,
    viewer=None,
    model='',
    budget_override=False,
):
    """(chat, message, job): the person's words stored and the turn that answers them started (or queued)."""
    if not client.available():
        raise Refused(client.NoKey.sentence)
    words = str(text or '').strip()
    if not words:
        raise ValidationError({'text': [SAY_SOMETHING]})
    if len(words) > MAX_TEXT:
        raise ValidationError({'text': [TOO_LONG]})
    if model and (model not in pricing.READ_MODELS or (model == pricing.OPUS and not reading.may_use_opus(user))):
        raise Refused(NO_OPUS)
    if budget_override and not reading.may_use_opus(user):
        raise Refused(NO_OVERRIDE)
    page = _page(tab, board, viewer)
    ids = _documents(deal, document_ids)
    now = clock.now()
    with transaction.atomic():
        Deal.objects.select_for_update().only('id').get(pk=deal.id)  # chats are numbered under the deal's lock
        chat = _chat(deal, chat_id, user, page['tab'])
        message = ChatMessage.objects.create(chat=chat, role=ChatMessage.USER_ROLE, text=words, author=user)
        chat.last_used_at, chat.last_used_by = now, user
        chat.save(update_fields=['last_used_at', 'last_used_by'])
    params = {'message_id': message.id, 'page': page}
    if model:
        params['model'] = model
    if budget_override:
        params['budget_override'] = True
    job, _created = start(user, deal, kinds.TURN, documents=ids, params=params, chat=chat)
    ChatMessage.objects.filter(pk=message.pk).update(job=job)
    message.job_id = job.id
    return chat, message, job


def rename_chat(user, chat_id, title):
    """(chat, changed)."""
    name = ' '.join(str(title or '').split())
    if len(name) > MAX_TITLE:
        raise ValidationError({'title': [TITLE_LONG]})
    with transaction.atomic():
        chat = Chat.objects.select_for_update().get(pk=chat_id)
        if chat.title == name:
            return chat, False
        chat.title = name
        chat.save(update_fields=['title'])
    return chat, True
