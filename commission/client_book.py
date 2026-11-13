"""The client's booked records, on the client page's Commissions tab (plan.md §7.10, §8.5; CL25, H106; slice 68):
`GET clients/{id}/commission/records/`.

The Book's own read (`book.queryset`, `record_read`) narrowed to one client and grouped by plan year, newest first, as
the old client statement grouped them (891f1b3 `ClientCommissionsTab.jsx`: "Booked, by plan year"), each year's sums
worked out here, since the browser sums nothing (rule 5). It follows the viewer's tier exactly as the Book does
(`visibility`; H102, OQ73): the all tier sees every record, every share and the house's figures; the own tier sees the
records it holds a share in, and on them its own share only, with no house or pool figure; the none tier is refused
with the Book's 403. Void records are left out, as on the Book. Reads only; the same queries at any size.

{client_id, tier: all | own, rows: [the Book's record], totals: {records, live, expected, holes, house?, pool?,
 next_12}, years: [{key, label, deal_id | null, records: [id], expected, house?, holes, change_pct | null,
 disclosure}]}

A year's `deal_id` is the deal its records were booked from when they share one (else None: a record added to the book
by hand has none); `change_pct` is its expected against the year before it, a whole per cent, half up; `disclosure`
says the CAA disclosure of that deal is the viewer's to download (the all tier, a deal and a medical, dental or vision
line; H108).
"""

from decimal import Decimal

from deals import clock
from quotes.math import plain, round_decimal

from . import book, record_read
from .disclosure import MDV_LINES

HUNDRED = Decimal(100)


def _year_of(row):
    return (row['effective_date'] or '')[:4]


def _change(expected, before):
    if expected is None or not before:
        return None
    return plain(round_decimal((Decimal(str(expected)) - Decimal(str(before))) / Decimal(str(before)) * HUNDRED))


def years(rows, viewer):
    """The rows' plan years, newest first (an undated record's group last), with their sums."""
    grouped = {}
    for row in rows:
        grouped.setdefault(_year_of(row), []).append(row)
    keys = sorted((key for key in grouped if key), reverse=True) + ([''] if '' in grouped else [])
    out = []
    for key in keys:
        members = grouped[key]
        sums = record_read.totals(members, viewer)
        deals = {row['deal_id'] for row in members}
        deal_id = next(iter(deals)) if len(deals) == 1 else None
        found = {
            'key': key,
            'label': key or '—',
            'deal_id': deal_id,
            'records': [row['id'] for row in members],
            'expected': sums['expected'],
            'holes': sums['holes'],
            'disclosure': bool(viewer.all and deal_id and any(row['line'] in MDV_LINES for row in members)),
        }
        if viewer.all:
            found['house'] = sums['house']
        out.append(found)
    for index, found in enumerate(out):
        before = out[index + 1]['expected'] if index + 1 < len(out) else None
        found['change_pct'] = _change(found['expected'], before)
    return out


def client_book(client, viewer):
    records = list(book.queryset({'client': client.id}, viewer))
    rows = record_read.payloads(records, viewer)
    totals = {**record_read.totals(rows, viewer), 'next_12': book.next_twelve(rows, clock.today())}
    return {
        'client_id': client.id,
        'tier': viewer.tier,
        'rows': rows,
        'totals': totals,
        'years': years(rows, viewer),
    }
