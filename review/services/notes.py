"""Notes, replies and closing a thread (plan.md §5.8, §7.13 `notes/`; L22; old 891f1b3 `review/notes.py` `add_note`,
`reply`, `resolve`, `remove_draft`). Every write locks the Deal first, then the notes it touches.

- `add(user, deal_id, ref, text, audience=)`: a remark on an item. `team` (🔒 Team only): nobody outside sees it, on any
  deal. `client`: it goes now, on the request a send-back on the item would go to (`rules.tray.target`), joining the
  item to it if it does not ask it yet (`deliver`), and shows on their link (a client still typing sees it on their
  next read). Refused 409 when no open link can take it (NO_LINK) or the deal may no longer ask its client.
- `reply(user, deal_id, question_id, text)`: our answer to a client's question, on their link now; it closes the
  question.
- `resolve(user, deal_id, note_id)`: close a question, or an ask or send-back that went out, by hand ("answered another
  way", or no longer needed). Closing what is closed changes nothing.
- `drop(user, deal_id, note_id)`: take one draft out of the tray (`DELETE notes/{id}/`).
Activity rows are key-only: what a note is about, never its words (a note may name a person or a condition, §3.8).
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from deals import activity, clock

from ..models import ASK_KINDS, ReviewNote
from ..rules import tray as tray_rules
from ..selectors import notes as note_rows
from ..selectors import open_requests
from . import deliver as delivering
from .common import AREA, user_id
from .tray import clean_text, items_of, locked_deal, refuse_unless_asking
from .tray import remove as remove_drafts

Noted = namedtuple('Noted', 'note activity')

AUDIENCES = ('team', 'client')
WRITE_FIRST = 'Write the note first.'
NO_LINK = 'No link to the client carries this yet. Ask for it instead (＋ Ask): it waits in the tray until you send it.'
NOT_FOUND = 'That note is not on this deal.'
NOT_A_QUESTION = 'That is not a question from the client.'
CLOSES = 'Only a question, or an ask or send-back that went out, closes.'


def _row(deal, user, action, summary, ref, *, coalesce=''):
    change = activity.change('notes', [ref])
    return activity.record(
        deal, user, AREA, action, summary, 1, coalesce, changes=[change], keys_only=True, revertible=False
    )


def _note(deal, note_id, **filters):
    try:
        return ReviewNote.objects.select_for_update().get(pk=int(note_id), deal=deal, **filters)
    except (ReviewNote.DoesNotExist, TypeError, ValueError):
        raise NotFound(NOT_FOUND) from None


def _client_target(deal, item, now):
    found = open_requests.load(deal.id)
    own = open_requests.own_requests(found).get(item.own_link)
    ask = tray_rules.Item(item.ref, item.section, item.gone, own, None, item.pin)
    target, _why = tray_rules.target(ask, open_requests.candidates(found, now))
    if target is None:
        raise activity.Refused(NO_LINK)
    return target.request_id


@transaction.atomic
def add(user, deal_id, ref, text, *, audience='team'):
    """Noted(note, Activity row)."""
    if audience not in AUDIENCES:
        raise ValidationError({'audience': ["Send 'team' or 'client'."]})
    text = clean_text(text)
    if not text:
        raise ValidationError({'text': [WRITE_FIRST]})
    deal = locked_deal(deal_id)
    item = items_of(deal, [ref])[ref]
    now = clock.now()
    note = ReviewNote(
        deal=deal, surface=item.surface, key=item.key, member_id=item.member_id, audience=audience, kind='note',
        text=text, author_id=user_id(user), at=now,
    )  # fmt: skip
    if audience == 'team':
        note.save()
        return Noted(note, _row(deal, user, 'noted', 'Wrote a team note', ref, coalesce=f'review:note:{deal.id}'))
    refuse_unless_asking(deal)
    request_id = _client_target(deal, item, now)
    note.save()
    try:
        done = delivering.deliver(user, request_id, [note], [item], now, summary='Wrote a note to the client')
    except delivering.NeedsNew as refused:
        raise activity.Refused(refused.why) from None
    return Noted(note, done.activity)


@transaction.atomic
def reply(user, deal_id, question_id, text):
    text = clean_text(text)
    if not text:
        raise ValidationError({'text': [WRITE_FIRST]})
    deal = locked_deal(deal_id)
    refuse_unless_asking(deal)
    question = _note(deal, question_id)
    if question.kind != 'question':
        raise ValidationError({'question_id': [NOT_A_QUESTION]})
    now = clock.now()
    note = ReviewNote.objects.create(
        deal=deal, surface=question.surface, key=question.key, member_id=question.member_id,
        request_id=question.request_id, link_id=question.link_id, parent=question, audience='client', kind='reply',
        text=text, author_id=user_id(user), at=now, sent_at=now,
    )  # fmt: skip
    if question.resolved_at is None:
        question.resolved_at, question.resolved_by_id = now, user_id(user)
        question.save(update_fields=['resolved_at', 'resolved_by'])
    return Noted(note, _row(deal, user, 'replied', 'Replied to the client', note_rows.ref_of(note)))


@transaction.atomic
def resolve(user, deal_id, note_id):
    deal = locked_deal(deal_id)
    note = _note(deal, note_id)
    closes = note.kind == 'question' or (note.kind in ASK_KINDS and note.sent_at is not None)
    if not closes:
        raise activity.Refused(CLOSES)
    if note.resolved_at is not None:
        return Noted(note, None)
    note.resolved_at, note.resolved_by_id = clock.now(), user_id(user)
    note.save(update_fields=['resolved_at', 'resolved_by'])
    return Noted(note, _row(deal, user, 'resolved', 'Closed a thread', note_rows.ref_of(note)))


def drop(user, deal_id, note_id):
    try:
        note_id = int(note_id)
    except (TypeError, ValueError):
        raise NotFound(NOT_FOUND) from None
    removed = remove_drafts(user, deal_id, [note_id])
    if not removed.ids:
        if not ReviewNote.objects.filter(pk=note_id, deal_id=deal_id).exists():
            raise NotFound(NOT_FOUND)
        raise activity.Refused('Only an item still in the tray can be taken out.')
    return removed
