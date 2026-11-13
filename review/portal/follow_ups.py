"""The follow-ups part of a link's page (plan.md §7.14, §8.20; L81, L101, L106; old 891f1b3
`notes.follow_ups_for_link`). Allowlisted: one card per item this link asks that we wrote to the client about, or
they asked about, with its thread.

- `titles(found)`: {ref: words} for everything the page asks (what a question may be about, and a card's title):
  each intake question and part, each person's asked value ("Date of birth — Avery Synthetic"; the page that shows
  people needs the PIN), each file, their census file, and (slice 58) each question of a form on screen ("Florida
  Blue 51+ · Plan 2 · Current plan name") and the form itself.
- `cards(link, request, deal, found)`: [{ref, title, needs_answer, answered, question_open, new, replied, thread}],
  the ones that need an answer first, then the newest. A thread entry is {who: you | colleague | agency, kind, text,
  plain, at}: never a team note, never a draft, never a staff name, never a value. An ask that went with no words of
  its own is just the form asking more, so it makes no card; a send-back says "Please check this and update it.".
  `needs_answer` while a send-back or ask on it is open and they have not answered since; `answered` once they sent
  something newer; `question_open` while a question of theirs (or, on an ordinary link, a colleague's) waits;
  `new` when a note or reply of ours went out after their last look (`Seen`, or never looked), `replied` when that is a
  reply. A blank link (L66) sees only its own questions.
- `stamp(link, request)`: what moves when a card would (a note sent or closed), for `form_stamp` (L103).
`routed(link, request)` is which notes a link's page reads: its request's, and its own.
"""

from django.db.models import Count, Max, Q

from census import fields as census_fields
from census.client_view import title as person_title
from documents.models import Document
from intake import form
from questionnaire import forms as questionnaire_forms
from questionnaire.engine import walk

from ..models import ASK_KINDS, ReviewNote, Seen
from ..rules import tray as tray_rules
from ..selectors import notes as note_rows
from . import files_part

ASK_DEFAULT = 'Please check this and update it.'
BLOCKS = {
    'contacts': 'Your contacts',
    'coverage': 'Coverage in force',
    'lines': 'Lines to quote',
    'bor': 'Broker of Record',
    'files': 'Compliance files',
}
CENSUS_FILE = 'Your census file'


def titles(found):
    out = {f'intake:{key}': form.BY_KEY[key]['label'] for key in found.intake_keys}
    out.update({f'intake:block:{block}': BLOCKS[block] for block in found.blocks})
    for member in found.people:
        for column in found.columns.get(member.id, []):
            out[f'census:{member.id}:{column}'] = f'{census_fields.label(column)} — {person_title(member)}'
    out.update({f'doc:{slot}': files_part.label(slot) for slot in found.documents})
    if found.census_file:
        out['census:file'] = CENSUS_FILE
    for ask in found.forms:
        out.update(_form_titles(ask))
    return out


def _form_titles(ask):
    from ..selectors.queue_questionnaire import label

    name = questionnaire_forms.label(ask.form)
    out = {f'qform:{ask.form}': questionnaire_forms.FORMS[ask.form]['title']}
    if ask.view is None:
        return out
    rows = ask.view.stored.rows
    numbers = {(block, entry['id']): at + 1 for block, listed in rows.items() for at, entry in enumerate(listed)}
    for entry in walk.order(ask.view.form, ask.view.view):
        out[f'q:{ask.form}:{entry["slot"]}'] = f'{name} · {label(ask.view.form, entry["slot"], numbers)[0]}'
    return out


def routed(link, request):
    return Q(request_id=request.id) | Q(link_id=link.id)


def _answered(found, link_ids):
    """{ref: when the client last answered it}: an answer on the owner's row, or a file through this request."""
    out = {}
    client = (found.intake.client if found.intake else None) or {}
    for slot, entry in client.items():
        if isinstance(entry, dict) and entry.get('at'):
            out[f'intake:{slot}'] = tray_rules.moment(entry['at'])
    for member in found.people:
        for column, entry in (member.client or {}).items():
            if isinstance(entry, dict) and entry.get('at'):
                out[f'census:{member.id}:{column}'] = tray_rules.moment(entry['at'])
    for ask in found.forms:
        row = ask.view.row if ask.view is not None else None
        for slot, entry in ((row.client if row else None) or {}).items():
            if isinstance(entry, dict) and entry.get('at'):
                out[f'q:{ask.form}:{slot}'] = tray_rules.moment(entry['at'])
    for slot, at in Document.objects.filter(link_id__in=link_ids, source='client').values_list('slot', 'uploaded_at'):
        ref = 'census:file' if slot == files_part.CENSUS_SLOT else slot if slot.startswith('qform:') else f'doc:{slot}'
        out[ref] = max(at, out.get(ref) or at)
    return out


def _who(note, link):
    if note.kind != 'question':
        return 'agency'
    return 'you' if note.link_id == link.id else 'colleague'


def _card(ref, title):
    return {'ref': ref, 'title': title, 'needs_answer': False, 'answered': False, 'question_open': False,
            'new': False, 'replied': False, 'thread': []}  # fmt: skip


def cards(link, request, deal, found, *, link_ids=()):
    named = titles(found)
    notes = ReviewNote.objects.filter(deal_id=deal.id, audience='client', sent_at__isnull=False)
    notes = notes.filter(routed(link, request)).order_by('sent_at', 'id')
    if link.blank:
        notes = notes.exclude(Q(kind='question') & ~Q(link_id=link.id))
    seen = Seen.objects.filter(deal_id=deal.id, link=link).values_list('seen_at', flat=True).first()
    answered = _answered(found, list(link_ids) or [link.id])
    out, asks = {}, {}
    for note in notes:
        ref = note_rows.ref_of(note)
        if ref not in named or (note.kind == 'ask' and not note.text.strip()):
            continue
        card = out.setdefault(ref, _card(ref, named[ref]))
        if note.kind == 'question' and note.resolved_at is None:
            card['question_open'] = True
        if note.kind in ('note', 'reply') and (seen is None or note.sent_at > seen):
            card['new'] = True
            card['replied'] = card['replied'] or note.kind == 'reply'
        if note.kind in ASK_KINDS and note.resolved_at is None:
            asks[ref] = max(note.sent_at, asks.get(ref) or note.sent_at)
        plain = not note.text.strip()
        text = ASK_DEFAULT if plain and note.kind in ASK_KINDS else note.text
        card['thread'].append({'who': _who(note, link), 'kind': note.kind, 'text': text, 'plain': plain,
                               'at': note.sent_at.isoformat()})  # fmt: skip
    for ref, sent in asks.items():
        later = answered.get(ref)
        out[ref]['answered'] = bool(later and later > sent)
        out[ref]['needs_answer'] = not out[ref]['answered']
    return sorted(out.values(), key=lambda card: (not card['needs_answer'], -_newest(card)))


def _newest(card):
    return max((tray_rules.moment(entry['at']).timestamp() for entry in card['thread']), default=0)


def stamp(link, request):
    found = ReviewNote.objects.filter(audience='client', sent_at__isnull=False).filter(routed(link, request))
    agg = found.aggregate(sent=Max('sent_at'), closed=Max('resolved_at'), n=Count('id'))
    return '|'.join(str(agg[key] or '') for key in ('sent', 'closed', 'n'))
