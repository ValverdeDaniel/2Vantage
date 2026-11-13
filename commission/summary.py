"""Commission's deal facts for Agenda and the Overview (plan.md §5.10; H38, H39; O.2). The Overview (slice 62) and
Agenda (slice 60) read them; nothing here writes.

- `facts(deal_ids)`: {deal_id: {rated_lines, records, booked_expected, holes, booked, needs_primary}} for any number
  of deals in a fixed number of queries, the same for every viewer: counts and flags only, no share and no one's
  earnings. `needs_primary`: no producer is set (no split on the deal or its client, and no active owner), so the
  house keeps 100 % — the sidebar's Commission "1" (H9; slice 61).
- `card(deal, viewer)`: the Overview's commission card (H38, H39): the expected figure, its note and the split chips
  for every deal user (D-066); the booked block's figures as the viewer's tier allows (H102).
"""

from decimal import Decimal

from deals.models import Deal
from quotes.math import plain

from . import book_rules, parties, rules, selectors, terms, vocab
from .models import ClientSplit, Commission, Record


def _needs_primary(out, splits):
    """Each deal's `needs_primary` (H9): `rules.resolve` falls through to the house (H10)."""
    deals = list(Deal.objects.filter(pk__in=list(out)).values_list('id', 'client_id', 'owner_id', 'client__owner_id'))
    clients = ClientSplit.objects.filter(client_id__in={row[1] for row in deals}).values_list('client_id', 'rows')
    client_rows = dict(clients)
    entries = parties.people() if deals else []
    for deal_id, client_id, owner_id, client_owner_id in deals:
        source, _rows = rules.resolve(
            splits.get(deal_id),
            client_rows.get(client_id),
            parties.owner_person(owner_id, entries),
            parties.owner_person(client_owner_id, entries),
        )
        out[deal_id]['needs_primary'] = source == vocab.HOUSE


def facts(deal_ids):
    deal_ids = list(deal_ids)
    out = {
        deal_id: {
            'rated_lines': [],
            'records': 0,
            'booked_expected': None,
            'holes': 0,
            'booked': False,
            'needs_primary': False,
        }
        for deal_id in deal_ids
    }
    splits = {}
    stored = Commission.objects.filter(deal_id__in=deal_ids).values_list('deal_id', 'rates', 'split')
    for deal_id, rates, split in stored:
        out[deal_id]['rated_lines'] = sorted(rates or {})
        splits[deal_id] = (split or {}).get('rows')
    _needs_primary(out, splits)
    totals = {}
    for record in Record.objects.filter(deal_id__in=deal_ids).exclude(status=vocab.VOID):
        entry = out[record.deal_id]
        entry['records'] += 1
        entry['booked'] = True
        merged = book_rules.facts(record)
        entry['holes'] += 1 if book_rules.holes(merged, record.sources or {}, record.year_number, record.deal_id) else 0
        expected = terms.expected(record.values or {}) if record.status in vocab.LIVE else None
        if expected is not None:
            totals[record.deal_id] = totals.get(record.deal_id, Decimal(0)) + expected
    for deal_id, total in totals.items():
        out[deal_id]['booked_expected'] = plain(total)
    return out


def card(deal, viewer):
    """The Overview card: what every deal user sees, and the booked block by tier."""
    payload = selectors.deal_payload(deal, viewer)
    booking = payload['booking']
    chips = [
        {'role': share['role'], 'name': share['name'], 'pct_label': share['pct_label']}
        for share in payload['preview']['shares']
        if share['role'] != 'house'
    ]
    return {
        'expected': payload['total'],
        'note': payload['note'],
        'chips': chips,
        'booking': {key: booking[key] for key in ('state', 'record_count', 'sees_ledger', 'totals') if key in booking},
    }
