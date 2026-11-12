"""Commission's deal facts for Agenda and the Overview (plan.md §5.10; H38, H39; O.2). The Overview (slice 62) and
Agenda (slice 60) read them; nothing here writes.

- `facts(deal_ids)`: {deal_id: {rated_lines, records, booked_expected, holes, booked}} for any number of deals in two
  queries, the same for every viewer: counts and flags only, no share and no one's earnings.
- `card(deal, viewer)`: the Overview's commission card (H38, H39): the expected figure, its note and the split chips
  for every deal user (D-066); the booked block's figures as the viewer's tier allows (H102).
"""

from decimal import Decimal

from quotes.math import plain

from . import book_rules, selectors, terms, vocab
from .models import Commission, Record


def facts(deal_ids):
    deal_ids = list(deal_ids)
    out = {
        deal_id: {'rated_lines': [], 'records': 0, 'booked_expected': None, 'holes': 0, 'booked': False}
        for deal_id in deal_ids
    }
    for deal_id, rates in Commission.objects.filter(deal_id__in=deal_ids).values_list('deal_id', 'rates'):
        out[deal_id]['rated_lines'] = sorted(rates or {})
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
