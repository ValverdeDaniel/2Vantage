"""What a turn remembers of its chat (plan.md §10.6; D79, D25; the old scan_chat MAX_CHAT_TURNS): the chat's last 30
messages, the person's newest one included, as plain words. Context blocks ride only the newest message and are never
stored (D78), so the history repeats nobody's figures and the cached prefix stays the same from turn to turn.
"""

from .models import ChatMessage

WINDOW = 30  # Claude reads this many of a chat's latest messages (the drawer's hint past it, D25)


def window(chat_id, upto_id):
    """The chat's messages up to and including `upto_id`, the last WINDOW of them, oldest first."""
    rows = list(
        ChatMessage.objects.filter(chat_id=chat_id, id__lte=upto_id).select_related('author').order_by('-id')[:WINDOW]
    )
    return list(reversed(rows))


def _speaker(row):
    if row.role != ChatMessage.USER_ROLE:
        return ''
    name = (row.author.get_full_name() or row.author.get_username()) if row.author else ''
    return f'{name}: ' if name else ''


def as_messages(rows):
    """[{role, content}] for the API: alternating roles (a run of one role joined), starting with the person. Each of
    the person's messages says who wrote it, because a deal's chats are shared (D7)."""
    out = []
    for row in rows:
        role = 'user' if row.role == ChatMessage.USER_ROLE else 'assistant'
        text = f'{_speaker(row)}{row.text}'.strip() or '…'
        if out and out[-1]['role'] == role:
            out[-1]['content'] += '\n\n' + text
        else:
            out.append({'role': role, 'content': text})
    while out and out[0]['role'] != 'user':
        out.pop(0)
    return out
