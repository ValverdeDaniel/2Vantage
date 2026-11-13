"""A client's questions and last look, through their link (plan.md §7.14 `questions/`, `seen/`; L101, L103; old 891f1b3
`notes.client_question`, `check_questions`, `mark_seen(link=)`). The portal's views call these once the guard has let
the link through (rule 11: a staff session never gets here, it answers 403).

- `ask(link_id, questions)`: `questions` is [{ref, text}], at most 20, each about something this page asks now
  (`follow_ups.titles`: an intake question or part, a person's asked value, a file); anything else refuses the whole
  post (400) before a write. Each becomes a question note on the link and its request, sent now, which staff see in
  their queues and threads until one of them replies or closes it. One key-only Activity row for the client ("Client
  asked 2 questions"), never the words (a question may name a person or a condition, §3.8).
- `seen(link_id)`: the page's last look at its follow-ups, now (it posts after showing something new).
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import clock

from ..models import ClientLink, ReviewNote
from ..portal import follow_ups
from ..portal.asked import asked
from ..rules import refs as ref_rules
from . import common, seen, stamps

LIMIT = 20
TEXT_LIMIT = 1000
LIST = f'Send up to {LIMIT} questions at a time, each as {{ref, text}}.'
TEXT = f'Each question needs some words, under {TEXT_LIMIT} characters.'
OFF_PAGE = 'A question must be about something on this page.'


def _clean(questions, allowed):
    if not isinstance(questions, list) or not questions or len(questions) > LIMIT:
        raise ValidationError({'questions': [LIST]})
    out = []
    for entry in questions:
        if not isinstance(entry, dict):
            raise ValidationError({'questions': [LIST]})
        text = str(entry.get('text') or '').strip()
        if not text or len(text) > TEXT_LIMIT:
            raise ValidationError({'questions': [TEXT]})
        ref = entry.get('ref')
        if not isinstance(ref, str) or ref not in allowed:
            raise ValidationError({'questions': [OFF_PAGE]})
        out.append((ref, text))
    return out


@transaction.atomic
def ask(link_id, questions):
    """The question notes made, oldest first."""
    link = ClientLink.objects.select_related('request__deal').get(pk=link_id)
    request, deal = link.request, link.request.deal
    found = asked(link, request, deal, link_ids=list(request.links.values_list('id', flat=True)))
    cleaned = _clean(questions, follow_ups.titles(found))
    deal, request, link = common.locked_open(link_id)
    now = clock.now()
    made = []
    for ref, text in cleaned:
        surface, key, member_id = ref_rules.note_of(ref)
        made.append(
            ReviewNote(
                deal=deal, surface=surface, key=key, member_id=member_id, request=request, link=link,
                audience='client', kind='question', text=text, at=now, sent_at=now,
            )
        )  # fmt: skip
    made = ReviewNote.objects.bulk_create(made)
    refs = sorted({ref for ref, _text in cleaned})
    count = len(made)
    summary = f'Client asked {count} question{"" if count == 1 else "s"}'
    stamps.client_row(deal, link, 'client_asked', summary, refs, count=count)
    return made


def seen_now(link_id):
    link = ClientLink.objects.select_related('request').get(pk=link_id)
    return seen.mark(link.request.deal_id, link=link)
