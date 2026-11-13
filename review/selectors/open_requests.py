"""The deal's requests as the tray weighs them (plan.md §5.8; L52; old 891f1b3 `notes._open_targets`, `_card`): two
queries (the requests, their links with contacts) however many there are.

- `load(deal_id)` → {request_id: (request, [link])}, every request on the deal, oldest first.
- `candidates(found, now)` → [rules.tray.Candidate]: the requests that can take an ask now (not closed, a link not
  turned off and inside its ceiling), each with the sections it asks, its links' weakest security and its people's
  names.
- `own_requests(found)` → {link id: request id}, the request an answer came through.
- `opens(found, now)` → {request_id: bool}: whether anyone can open the request now (an ask on one that does not
  asks nobody, L.6).
- `card(request, links, now)`: one destination as the tray shows it (L52): its people, whether each was sent, opened,
  the days left, and when the link will run out once the ask joins it (`expires_if_sent`, its life again from now).
  Names and dates only, never a value.
"""

from ..models import ClientLink, ClientRequest
from ..rules import asks as ask_rules
from ..rules import policy
from ..rules import tray as tray_rules


def _iso(moment):
    return moment.isoformat() if moment else None


def load(deal_id):
    requests = list(ClientRequest.objects.filter(deal_id=deal_id).order_by('id'))
    links = {}
    for link in ClientLink.objects.filter(request__deal_id=deal_id).select_related('contact').order_by('id'):
        links.setdefault(link.request_id, []).append(link)
    return {request.id: (request, links.get(request.id, [])) for request in requests}


def own_requests(found):
    """{link id: request id}: the request a send-back's answer came through, by its link."""
    return {link.id: request.id for request, links in found.values() for link in links}


def names(links, now):
    return list(dict.fromkeys(link.name for link in tray_rules.live_links(links, now) if link.name))


def candidates(found, now):
    out = []
    for request, links in found.values():
        if tray_rules.can_take(request.closed_at, links, now):
            sections = ask_rules.sections(request.asks)
            weakest = tray_rules.weakest(links, now)
            out.append(tray_rules.Candidate(request.id, request.created_at, sections, weakest, names(links, now)))
    return out


def opens(found, now):
    return {
        request_id: any(policy.opens(link, now, closed=request.closed_at is not None) for link in links)
        for request_id, (request, links) in found.items()
    }


def card(request, links, now):
    live = tray_rules.live_links(links, now)
    return {
        'key': f'request:{request.id}',
        'request_id': request.id,
        'created_at': _iso(request.created_at),
        'names': names(links, now),
        'people': [
            {
                'link_id': link.id,
                'name': link.name,
                'security': link.security,
                'sent_at': _iso(link.sent_at),
                'opened': link.open_count,
                'last_opened_at': _iso(link.last_opened_at),
                'submitted_at': _iso(link.submitted_at),
                'expires_at': _iso(link.expires_at),
                'days_left': policy.days_left(link.expires_at, now),
                'expires_if_sent': _iso(policy.renewed(link.expires_at, link.ceiling_at, now)),
            }
            for link in live
        ],
    }
