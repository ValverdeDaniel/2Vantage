"""The request tray as the screens read it (plan.md §7.13 `GET review/tray/`; L49–L52, L54; B12; old 891f1b3
`review/notes.py` `tray`, `_TrayRead`, `intake_asks_out`): what waits to go to the client, where each item would go or
why it cannot yet, the open links it can go on, and what is already out with the client. A fixed number of queries
however many drafts wait (the drafts, the Intake row and people they name, the requests and their links, the notes out).

`tray(deal)` → {count, asks_closed, items, links, needs_new, out}:
- an item {id, ref, surface (intake | census | documents: the snippet's sections), kind (ask | sendback), title, text,
  at, by, target {key, request_id, names, expires_at, days_left} | None, why, why_code (needs_link | needs_pin | gone |
  ''), gone, named};
- `links`: every request that can take an ask, newest first, as a destination card (`open_requests.card`);
- `needs_new`: the ids no open link can take, which "Choose who ▸" makes a new link for (L52, U1);
- `out`: {ref: when it was first asked} for what an open link the client was sent asks now, and each ask or send-back
  that went out and is still open: the intake tab's "Asked <date>" (B12) and the "＋ Ask all" that leaves them be.
Staff only. Reads only.
"""

from deals import clock, rules
from intake.models import Intake

from ..portal import asked as asked_rules
from ..rules import policy
from ..rules import tray as tray_rules
from . import items as item_rows
from . import notes as note_rows
from . import open_requests


def _iso(moment):
    return moment.isoformat() if moment else None


def _target(found, request_id, now):
    request, links = found[request_id]
    live = tray_rules.live_links(links, now)
    latest = max((link.expires_at for link in live), default=None)
    return {
        'key': f'request:{request.id}',
        'request_id': request.id,
        'names': open_requests.names(links, now),
        'expires_at': _iso(latest),
        'days_left': policy.days_left(latest, now) if latest else None,
    }


def _first(out, ref, at):
    if at is not None and (ref not in out or at < out[ref]):
        out[ref] = at


def out_with_client(deal, found, now):
    """{ref: first sent} for what an open, sent request asks now, and each open ask or send-back that went out."""
    out = {}
    intake = None
    for request, links in found.values():
        sent = [
            link.sent_at for link in links if link.sent_at and policy.opens(link, now, closed=bool(request.closed_at))
        ]
        if not sent:
            continue
        intake = intake or Intake.objects.filter(deal_id=deal.id).first()
        for ref in asked_rules.outline(request, deal, intake):
            _first(out, ref, min(sent))
    opens = open_requests.opens(found, now)
    for note in note_rows.sent_asks([deal.id]).get(deal.id, []):
        if opens.get(note.request_id):
            _first(out, note_rows.ref_of(note), note.sent_at)
    return {ref: at.isoformat() for ref, at in out.items()}


def tray(deal, now=None):
    now = now or clock.now()
    drafts = note_rows.drafts(deal.id)
    items = item_rows.resolve(deal, [note_rows.ref_of(note) for note in drafts])
    found = open_requests.load(deal.id)
    candidates = open_requests.candidates(found, now)
    own = open_requests.own_requests(found)
    rows, needs_new = [], []
    for note in drafts:
        item = items[note_rows.ref_of(note)]
        ask = tray_rules.Item(item.ref, item.section, item.gone, own.get(item.own_link), note.request_id, item.pin)
        target, why = tray_rules.target(ask, candidates)
        if target is None and not item.gone:
            needs_new.append(note.id)
        rows.append(
            {
                'id': note.id,
                'ref': item.ref,
                'surface': item.surface,
                'kind': note.kind,
                'title': item.label,
                'text': note.text,
                'at': _iso(note.at),
                'by': note_rows.payload(note)['by'] if note.author_id else '',
                'target': _target(found, target.request_id, now) if target else None,
                'why': why,
                'why_code': tray_rules.CODES.get(why, ''),
                'gone': item.gone,
                'named': note.request_id is not None,
            }
        )
    cards = [open_requests.card(*found[c.request_id], now) for c in sorted(candidates, key=_newest, reverse=True)]
    return {
        'count': len(rows),
        'asks_closed': rules.client_asks_open(deal),
        'items': rows,
        'links': cards,
        'needs_new': needs_new,
        'out': out_with_client(deal, found, now),
    }


def _newest(candidate):
    return (candidate.created_at, candidate.request_id)
