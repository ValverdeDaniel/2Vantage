"""Review notes as the staff screens read them (plan.md §6.12; L22, L49–L53; old 891f1b3 `review/notes.py`
`note_payload`, `threads_for_case`, `_drafts`, `going_back_q`), each in one query however many notes:

- `payload(note)`: one note as a thread shows it: {id, ref, kind, audience, text, by, who, at, sent_at, resolved_at,
  from_client, link_id, request_id}. `who` names its author: our person, or for a client's question the person whose
  link asked ('' when the link names nobody: the screen says "The client"). Staff only: a team note rides it.
- `threads(deal_id, refs=None)`: {ref: [note]} oldest first, every note on the deal (or on `refs`).
- `drafts(deal_id, ids=None)`: the asks and send-backs waiting in the tray, oldest first.
- `sent_asks(deal_ids)`: {deal_id: [note]}, the asks and send-backs that went out and nobody closed.
- `going(deal_ids, opens)`: {deal_id: (refs drafted, {ref: newest sent on a request that opens})}, one query: what
  `rules.tray.going_back` reads. `opens` is {request_id: bool}.
"""

from collections import defaultdict

from ..models import ASK_KINDS, ReviewNote
from ..rules import refs as ref_rules


def _iso(moment):
    return moment.isoformat() if moment else None


def _person(user):
    return (user.get_full_name() or user.username) if user else ''


def ref_of(note):
    return ref_rules.ref_of_note(note.surface, note.key, note.member_id)


def payload(note):
    ours = _person(note.author)
    asked = note.kind == 'question'
    return {
        'id': note.id,
        'ref': ref_of(note),
        'kind': note.kind,
        'audience': note.audience,
        'text': note.text,
        'by': ours,
        'who': (note.link.name if note.link_id else '') if asked else ours,
        'at': _iso(note.at),
        'sent_at': _iso(note.sent_at),
        'resolved_at': _iso(note.resolved_at),
        'from_client': asked,
        'link_id': note.link_id if note.sent_at else None,
        'request_id': note.request_id if note.sent_at else None,
    }


def threads(deal_id, refs=None):
    rows = ReviewNote.objects.filter(deal_id=deal_id).select_related('author', 'link').order_by('at', 'id')
    wanted = set(refs) if refs is not None else None
    out = defaultdict(list)
    for note in rows:
        ref = ref_of(note)
        if wanted is None or ref in wanted:
            out[ref].append(payload(note))
    return dict(out)


def drafts(deal_id, ids=None):
    rows = ReviewNote.objects.filter(
        deal_id=deal_id, kind__in=ASK_KINDS, sent_at__isnull=True, resolved_at__isnull=True
    ).select_related('author')
    if ids is not None:
        rows = rows.filter(pk__in=list(ids))
    return list(rows.order_by('at', 'id'))


def sent_asks(deal_ids):
    rows = ReviewNote.objects.filter(
        deal_id__in=list(deal_ids), kind__in=ASK_KINDS, sent_at__isnull=False, resolved_at__isnull=True
    ).order_by('sent_at', 'id')
    out = defaultdict(list)
    for note in rows:
        out[note.deal_id].append(note)
    return out


def going(deal_ids, opens):
    rows = ReviewNote.objects.filter(deal_id__in=list(deal_ids), kind__in=ASK_KINDS, resolved_at__isnull=True).only(
        'deal_id', 'surface', 'key', 'member_id', 'sent_at', 'request_id'
    )
    out = defaultdict(lambda: (set(), {}))
    for note in rows:
        drafted, sent = out[note.deal_id]
        ref = ref_of(note)
        if note.sent_at is None:
            drafted.add(ref)
        elif opens.get(note.request_id) and (ref not in sent or note.sent_at > sent[ref]):
            sent[ref] = note.sent_at
    return out
