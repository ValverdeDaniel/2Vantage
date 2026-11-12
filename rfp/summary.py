"""The RFP's facts for the Agenda and the Overview (plan.md §5.10; K.4 "Read by others"; K119, K123). Reads only.

`facts(deal_ids)` → `{deal_id: {route, carriers, drafts_sent, drafts_total, first_sent_on, last_sent_on, cards_done,
cards_total, due_date, awaiting}}`: the route (stored, else the band's), how many carriers are picked, how many drafts
are marked sent of how many the route makes (Warner: one; direct: one per picked carrier, plus "Other carriers"),
the first and last send dates (the follow-up counts from the first when `marketed_at` is blank, K123), the cards
marked completed, the due date, and `awaiting`: the carriers asked that no plan has come from since their send (old
follow-up fired only on a deal with no plans at all). Never builds cards per deal. The requests and the plans are one
query each; only a deal whose route still follows the band reads its headcount (a batched headcount slot is the
Agenda's to add, slice 60, as for `intake.summary`).
"""

from datetime import datetime

from deals import carriers as identities
from deals.models import Deal
from quotes.models import Plan

from . import cleaners, services
from .models import RfpRequest


def _route(deal, stored):
    return services.route_now(deal, stored)


def _when(text):
    try:
        return datetime.fromisoformat(str(text)) if text else None
    except ValueError:
        return None


def _awaiting(sends, plans):
    """Names asked whose carrier has no plan created since the send that asked them."""
    out, seen = [], set()
    for send in sends.values():
        if not isinstance(send, dict):
            continue
        for entry in send.get('asked') or []:
            token = entry.get('key') or identities.identity(entry.get('name'))
            if not token or token in seen:
                continue
            seen.add(token)
            since = _when(send.get('at'))
            if not any(carrier == token and (since is None or created >= since) for carrier, created in plans):
                out.append(entry.get('name') or token)
    return out


def facts(deal_ids):
    ids = list(deal_ids)
    rows = {row.deal_id: row for row in RfpRequest.objects.filter(deal_id__in=ids)}
    plans = {}
    for deal_id, carrier, created in Plan.objects.filter(deal_id__in=ids).values_list(
        'deal_id', 'carrier', 'created_at'
    ):
        plans.setdefault(deal_id, []).append((identities.identity(carrier), created))
    out = {}
    for deal in Deal.objects.filter(pk__in=ids):
        row = rows.get(deal.id)
        stored = cleaners.stored(row)
        route = _route(deal, stored['route'])
        picked = [key for key in stored['carriers'] if key in identities.BY_KEY]
        total = 1 if route != 'direct' else len(picked) + (1 if stored['other_carriers'].strip() else 0)
        sends = dict((row.sends if row else None) or {})
        dates = sorted(str(send.get('on')) for send in sends.values() if isinstance(send, dict) and send.get('on'))
        out[deal.id] = {
            'route': route,
            'carriers': len(picked),
            'drafts_sent': len(sends),
            'drafts_total': total,
            'first_sent_on': dates[0] if dates else None,
            'last_sent_on': dates[-1] if dates else None,
            'cards_done': sum(1 for card in services.CARD_KEYS if ((row.done if row else None) or {}).get(card)),
            'cards_total': len(services.CARD_KEYS),
            'due_date': stored['due_date'],
            'awaiting': _awaiting(sends, plans.get(deal.id, [])),
        }
    return out
