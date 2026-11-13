"""The request page (plan.md §7.13 `GET review/request/?pane=`, §8.8; L24, L26–L29, L33, L37; B12; old 891f1b3
`review/request_page.py`): where a person works with one client — who has a link, what each tab could ask and where
each item stands, what is in the tray and where it goes, each item's thread, and what is new since their last look.

`page(deal, pane, user)` → {pane, asks_closed, panes [{key, label, waiting, in_cart}], people [person], counts
{all, question, in_cart, answered, asked, on_file, missing}, items [item], columns [column] (census), census_file
(census), threads {ref: [note]}, seen_at, new [ref]}:
- a tab (`pane`: intake, census, documents) is read alone (L28 Ch. 14a); the tabs' own numbers come from the deal's
  counts: client answers and questions waiting (`waiting`), drafts in the tray (`in_cart`);
- `people`: the who bar (L26): each link on a request still open that a person can still use (not past its ceiling),
  {link_id, request_id, name, security, sent, opens, days_left, expired, revoked, path};
- an item and a column as `request_rail` builds them; `threads` the notes on the tab's items (L22);
- `new`: the items with a client question or answer since this person's last look (`Seen`, L33; never looked: all).
Staff only. A fixed number of queries per tab; writes nothing.
"""

from collections import Counter

from deals import clock, rules
from intake.models import Intake

from .. import tokens
from ..models import ReviewNote, Seen
from ..rules import policy
from ..rules import rail as rail_rules
from . import entries as entry_rows
from . import notes as note_rows
from . import open_requests, request_rail
from .tray import out_with_client

PANES = (('intake', 'Intake'), ('census', 'Census'), ('documents', 'Documents'))


def _iso(moment):
    return moment.isoformat() if moment else None


def _people(found, now):
    out = []
    for request, links in found.values():
        if request.closed_at is not None:
            continue
        for link in links:
            if not policy.can_renew(link, now):
                continue
            out.append(
                {
                    'link_id': link.id,
                    'request_id': request.id,
                    'name': link.name,
                    'security': link.security,
                    'sent': link.sent_at is not None,
                    'opens': link.open_count,
                    'days_left': policy.days_left(link.expires_at, now),
                    'expired': link.expires_at <= now,
                    'revoked': link.revoked_at is not None,
                    'submitted_at': _iso(link.submitted_at),
                    'path': tokens.path_of(link.seed),
                }
            )
    return out


def _facts(deal, found, now):
    notes = list(ReviewNote.objects.filter(deal_id=deal.id).only('surface', 'key', 'member_id', 'kind', 'sent_at',
                                                                 'resolved_at', 'request_id', 'at'))  # fmt: skip
    opens = open_requests.opens(found, now)
    drafts = {}
    questions, counted, sent = set(), Counter(), set()
    for note in notes:
        ref = note_rows.ref_of(note)
        counted[ref] += 1
        if note.kind == 'question' and note.resolved_at is None:
            questions.add(ref)
        if note.kind in ('ask', 'sendback') and note.resolved_at is None:
            if note.sent_at is None:
                drafts[ref] = note
            elif opens.get(note.request_id):
                sent.add(ref)
    pending = {entry.ref for entry in entry_rows.waiting([deal.id]).get(deal.id, [])}
    requests = [request.asks or {} for request, links in found.values() if opens.get(request.id)]
    out = out_with_client(deal, found, now)
    facts = request_rail.Facts(drafts, out, pending, questions, counted, sent, requests)
    return facts, notes


def _panes(facts):
    waiting, in_cart = Counter(), Counter()
    for ref in facts.pending | facts.questions:
        waiting[_pane_of(ref)] += 1
    for ref in facts.drafts:
        in_cart[_pane_of(ref)] += 1
    return [{'key': key, 'label': label, 'waiting': waiting[key], 'in_cart': in_cart[key]} for key, label in PANES]


def _pane_of(ref):
    if ref.startswith('doc:'):
        return 'documents'
    return 'census' if ref.startswith('census:') else 'intake'


def _new(notes, facts, seen, pane):
    out = set()
    for note in notes:
        ref = note_rows.ref_of(note)
        if note.kind == 'question' and (seen is None or note.at > seen) and _pane_of(ref) == pane:
            out.add(ref)
    return sorted(out | {ref for ref in facts.pending if _pane_of(ref) == pane and seen is None})


def page(deal, pane, user, now=None):
    now = now or clock.now()
    found = open_requests.load(deal.id)
    facts, notes = _facts(deal, found, now)
    answer = {
        'pane': pane,
        'asks_closed': rules.client_asks_open(deal),
        'panes': _panes(facts),
        'people': _people(found, now),
    }
    if pane == 'intake':
        items = request_rail.intake(deal, Intake.objects.filter(deal_id=deal.id).first(), facts)
    elif pane == 'documents':
        items = request_rail.documents(deal, facts)
    else:
        census_file, columns = request_rail.census(deal, facts)
        items = [census_file]
        answer.update(columns=columns, census_file=census_file)
    refs = {item['ref'] for item in items} | {ref for ref in facts.notes if _pane_of(ref) == pane}
    seen = Seen.objects.filter(deal_id=deal.id, user=user).values_list('seen_at', flat=True).first()
    answer.update(
        counts=rail_rules.counts(items),
        items=items,
        threads=note_rows.threads(deal.id, refs),
        seen_at=_iso(seen),
        new=_new(notes, facts, seen, pane),
    )
    return answer
