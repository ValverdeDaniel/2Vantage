"""The chat payloads (plan.md §7.5; D7, D25, D90; slice 24). Reads only, a fixed number of queries.

- `chats(deal, user)`: the deal's chats, most recently used first, each with its title (or "Chat N"), the tab it
  started on, when and by whom a person last wrote in it, and how many messages it holds; `open` is the chat this
  person last wrote in on the deal (the old D-096 rule: the server picks the chat to open).
- `messages(chat, before)`: one page of a chat's messages, oldest first, each with the turn it belongs to: the
  turn's state, what it proposed (the change set), how it landed and what it cost (D90), and the board it set.
"""

from django.db.models import Count, Max, Q

from deals.selectors import person

from . import history, kinds
from .models import Chat, ChatMessage

PAGE = 50


def title(chat):
    return chat.title or f'Chat {chat.number}'


def chats(deal, user):
    rows = list(
        Chat.objects.filter(deal=deal)
        .select_related('last_used_by')
        .annotate(count=Count('messages'), mine=Max('messages__id', filter=Q(messages__author=user)))
        .order_by('-last_used_at', '-id')
    )
    mine = max((row for row in rows if row.mine), key=lambda row: row.mine, default=None)
    return {
        'chats': [
            {
                'id': row.id,
                'number': row.number,
                'title': title(row),
                'named': bool(row.title),
                'tab': row.tab,
                'created_at': row.created_at,
                'last_used_at': row.last_used_at,
                'last_used_by': person(row.last_used_by),
                'messages': row.count,
            }
            for row in rows
        ],
        'open': mine.id if mine else None,
        'window': history.WINDOW,
    }


def turn(job):
    """A turn as its messages show it: running or ended, what it proposed, how that landed, what it cost."""
    result = job.result or {}
    landed = result.get('landed') or {}
    return {
        'id': job.id,
        'status': job.status,
        'stopping': bool(job.cancel_requested_at) and job.status in kinds.ACTIVE,
        'started_at': job.started_at,
        'step': job.steps[-1] if job.steps else '',
        'land': job.land,  # auto (landed by itself), staged (waits for review), budget (over the deal's budget)
        'wait_reason': job.wait_reason,
        'resolution': job.resolution,
        'over': result.get('over') or '',
        'error': job.error,
        'model': job.model or (job.params or {}).get('model', ''),
        'cost_usd': f'{job.cost_usd:.4f}',
        'summary': result.get('summary', ''),
        'items': result.get('items') or [],
        'findings': result.get('findings') or [],
        'board': result.get('board'),
        'landed': {
            'summary': landed.get('summary', ''),
            'plan_ids': landed.get('plan_ids') or [],
            'areas': landed.get('areas') or [],
            'items': landed.get('items') or [],
            'auto': bool(landed.get('auto')),
            'undone': bool(landed.get('undone')),
        },
        'retry_of': (job.params or {}).get('retry_of'),
    }


def message(row):
    return {
        'id': row.id,
        'role': row.role,
        'text': row.text,
        'author': person(row.author),
        'created_at': row.created_at,
        'job_id': row.job_id,
        'turn': turn(row.job) if row.job_id else None,
    }


def messages(chat, before=None):
    """{messages, more}: up to PAGE messages before `before` (the newest when None), oldest first."""
    rows = ChatMessage.objects.filter(chat=chat).select_related('author', 'job')
    if before is not None:
        rows = rows.filter(id__lt=before)
    page = list(rows.order_by('-id')[: PAGE + 1])
    return {
        'chat': {'id': chat.id, 'number': chat.number, 'title': title(chat), 'named': bool(chat.title)},
        'messages': [message(row) for row in reversed(page[:PAGE])],
        'more': len(page) > PAGE,
    }
