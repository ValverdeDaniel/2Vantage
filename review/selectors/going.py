"""Which client answers went back to the client (plan.md §8.8; L14, L16, L120; slice 56; `rules.tray.going_back`), for
the summary's section counts, the queue's Going back phase, "Approve N ready" and the export check's line.

- `opens(requests, links, now)` → {request_id: bool} from rows already read (the summary's);
- `opens_for(deal_ids, now)` → the same in two queries (the requests, their links);
- `refs(deal_ids, waiting, opens)` → {deal_id: {ref}}: one query of the open asks and send-backs.
"""

from ..models import ClientLink, ClientRequest
from ..rules import policy
from ..rules import tray as tray_rules
from . import notes as note_rows


def opens(requests, links, now):
    return {
        request.id: any(
            policy.opens(link, now, closed=request.closed_at is not None) for link in links.get(request.id, [])
        )
        for request in requests
    }


def opens_for(deal_ids, now):
    requests = list(ClientRequest.objects.filter(deal_id__in=list(deal_ids)).only('id', 'closed_at'))
    links = {}
    for link in ClientLink.objects.filter(request_id__in=[r.id for r in requests]).only(
        'id', 'request_id', 'revoked_at', 'expires_at'
    ):
        links.setdefault(link.request_id, []).append(link)
    return opens(requests, links, now)


def refs(deal_ids, waiting, opened):
    found = note_rows.going(deal_ids, opened)
    out = {}
    for deal_id in deal_ids:
        drafted, sent = found.get(deal_id, (set(), {}))
        out[deal_id] = tray_rules.going_back(waiting.get(deal_id, []), drafted, sent)
    return out
