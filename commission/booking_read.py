"""The Commission tab after the sale (plan.md §8.13; H23, H25, H35, H37, H108, H120): the `booking` block of the tab's
payload. GETs write nothing.

- `state`: `none` before a sale; `unbooked` when the deal is sold but what it books today has no live record (the
  receiver failed, or the sold set moved while it could not book): "Sold — not booked · Book now" (H25); `booked`.
- Every deal user learns the state and the record count. The ledger's figures follow the tier (H102): the records the
  viewer may see, with the shares their tier allows, the totals and the holes; the house figures are the all tier's.
- `frozen` (H23): who gets what as booked, per line when the lines differ, read from the records' terms.
- `stale` (H120): booked records whose `sale` keys differ from what the deal would book today, with the expected
  revenue before and after ("Out of date: $X → $Y · Update", a one-click rebook).
- `disclosure`: the CAA disclosure is offered to the all tier once a medical, dental or vision line is booked (H108).
"""

from deals.rules import LOST
from quotes.math import plain

from . import book_rules, record_read, terms, to_book, visibility, vocab
from .disclosure import MDV_LINES
from .models import Record

NONE, UNBOOKED, BOOKED = 'none', 'unbooked', 'booked'


def state_of(pairs, left):
    if not pairs and not any(record.status != vocab.VOID for record in left):
        return NONE
    gaps = any(record is None or record.status == vocab.VOID for _target, record in pairs)
    extra = any(record.status != vocab.VOID for record in left)
    return UNBOOKED if gaps or extra else BOOKED


def _stale(pairs):
    out = []
    for wanted, record in pairs:
        if record is None or record.status == vocab.VOID:
            continue
        merged = book_rules.facts(record)
        keys = book_rules.stale_keys(merged, record.sources or {}, wanted.facts)
        if not keys:
            continue
        today = {**record.values, **{key: wanted.facts.get(key) for key in keys if key in book_rules.VALUES}}
        before, after = terms.expected(record.values), terms.expected(today)
        out.append(
            {
                'record_id': record.id,
                'line': record.line,
                'carrier': record.carrier,
                'keys': keys,
                'before': plain(before),
                'after': plain(after),
            }
        )
    return out


def _frozen(rows):
    """[{line, line_label, shares}] as booked: one list when every line shares the same terms (H23)."""
    signature = {row['line']: [(s['party'], s['role'], s['share']) for s in row['shares']] for row in rows}
    if len({repr(value) for value in signature.values()}) <= 1:
        return [{'line': None, 'line_label': '', 'shares': rows[0]['shares']}] if rows else []
    return [{'line': row['line'], 'line_label': row['line_label'], 'shares': row['shares']} for row in rows]


def block(deal, viewer, states):
    """The tab's `booking` block for `viewer` (a `visibility.Viewer`); `states` are the deal's line states."""
    records = list(Record.objects.filter(deal_id=deal.id).select_related('client', 'booked_by', 'updated_by'))
    pairs, left = book_rules.match(records, to_book.targets(deal, states))
    live = [record for record in records if record.status != vocab.VOID]
    out = {
        'state': state_of(pairs, left),
        'record_count': len(live),
        'can_book': viewer.all and deal.stage != LOST,
        'sees_ledger': viewer.sees_ledger,
    }
    if not viewer.sees_ledger:
        return out
    shown = [record for record in live if viewer.all or viewer.party_id in (record.party_ids or [])]
    rows = record_read.payloads(shown, viewer, {record.id: record for record in records})
    out.update(
        {
            'records': rows,
            'totals': record_read.totals(rows, viewer),
            'frozen': _frozen(rows),
            'people': record_read.who_gets_what(rows),
            'stale': _stale(pairs) if viewer.all else [],
            'disclosure': viewer.all and any(record.line in MDV_LINES for record in live),
        }
    )
    return out


def viewer_of(user):
    return visibility.Viewer(user)
