"""Who gets what, frozen at booking (plan.md §5.6; H10, H23, H29, H30, H55): the terms a record keeps, and the shares
and dollars worked out from them on read.

- `freeze(by, source, rows, year)`: `{house_pct, rows, from, shares: None, reason: ''}`. Only the terms are frozen: the
  split that applied (`rules.resolve`) and the house's % for the record's year (H29). A producer named by their
  login gets a Party now (H95), as a split save does.
- `for_deal(by, deal, year)` / `for_client(by, client, year)`: the terms a deal's booking, or a booking by hand (H58),
  freezes.
- `shares(records)`: {record id: [share]} computed once per deal (OQ71: a flat or PEPM row pays its amount once on the
  deal, never per line) on the deal's live records' expected revenue, applied to each record; a record booked by hand
  is its own group, and typed shares override only their own record (H55). Each share is `{party, role, share
  (millionths), amount}`, the dollars at cents summing to the record's expected exactly.
- `expected(facts)`: a record's expected annual revenue at cents, or None (a hole).
"""

from decimal import Decimal

from quotes.math import decimal

from . import math, parties, rules, vocab
from .models import ClientSplit, Commission, Settings

HUNDRED = Decimal(100)
MEDICAL = 'medical'


def _text(number):
    return format(Decimal(number).normalize(), 'f')


def freeze(by, source, rows, year):
    """The terms for `rows` (the split that applies, from `source`) in `year` (None = not known: renewal terms)."""
    from .services.splits import stored_row  # services build on reads, never the other way round

    stored = [stored_row(row, by) for row in rows]
    entries = parties.people()
    people = parties.lookup(entries)
    primary = next((row for row in stored if row['role'] == vocab.PRIMARY), None)
    person = people.get(('party', primary['party'])) if primary else None
    pct, _source = rules.producer_pct(person, Settings.get(), year == 1)
    return {'house_pct': _text(HUNDRED - pct), 'rows': stored, 'from': source, 'shares': None, 'reason': ''}


def for_deal(by, deal, year):
    entries = parties.people()
    split = Commission.objects.filter(deal_id=deal.id).values_list('split', flat=True).first()
    client_rows = ClientSplit.objects.filter(client_id=deal.client_id).values_list('rows', flat=True).first()
    source, rows = rules.resolve(
        (split or {}).get('rows'),
        client_rows,
        parties.owner_person(deal.owner_id, entries),
        parties.owner_person(deal.client.owner_id, entries),
    )
    return freeze(by, source, rows, year)


def for_client(by, client, year):
    entries = parties.people()
    client_rows = ClientSplit.objects.filter(client_id=client.id).values_list('rows', flat=True).first()
    source, rows = rules.resolve(None, client_rows, None, parties.owner_person(client.owner_id, entries))
    return freeze(by, source, rows, year)


def party_ids(terms):
    """The parties a record's terms name (the rows and any typed shares), for the Book's own-tier filter (H102)."""
    named = {row.get('party') for row in terms.get('rows') or []}
    named |= {row.get('party') for row in terms.get('shares') or []}
    return sorted(pid for pid in named if pid)


def expected(facts):
    """Expected annual revenue of a record at cents, half up (891f1b3 `record_expected`), or None when a figure it
    needs is missing. At cents, so a line booked as two carriers' records (OQ75) adds up to the tab's whole-dollar
    line figure once shown in dollars."""
    rate = facts.get('rate')
    if not rate:
        return None
    return math.comp_amount(rate, facts.get('premium_annual'), facts.get('employees'), places=2)


def _typed(terms):
    return [
        {'party': row.get('party'), 'role': row['role'], 'share': math.millionths(row['pct'])}
        for row in terms['shares']
    ]


def _group_key(record):
    """Records that share their shares: a deal's records with the same terms, live and void apart; a hand booking
    alone (H.6 `deal_shares`)."""
    terms = record.terms or {}
    if not record.deal_id:
        return ('record', record.id)
    frozen = (terms.get('house_pct'), repr(terms.get('rows')), record.year_number)
    return ('deal', record.deal_id, record.status == vocab.VOID, frozen)


def _employees(members):
    """The headcount a PEPM split row pays on: the medical record's, else the largest (OQ71)."""
    counted = [(record.values.get('employees'), record.line) for record in members if record.values.get('employees')]
    medical = next((count for count, line in counted if line == MEDICAL), None)
    return medical or max((count for count, _ in counted), default=None)


def shares(records):
    """{record id: (expected, [share])}. `records` must hold every record of each deal it names (the caller loads the
    deal's siblings), so a filtered Book row still gets its deal's shares."""
    groups = {}
    for record in records:
        groups.setdefault(_group_key(record), []).append(record)
    out = {}
    for members in groups.values():
        first = members[0]
        terms = first.terms or {}
        figures = {record.id: expected(record.values or {}) for record in members}
        known = [value for value in figures.values() if value is not None]
        total = sum(known, Decimal(0)) if known else None
        rows = math.year_terms(terms.get('rows') or [], first.year_number)
        group = math.compute_shares(total, rows, decimal(terms.get('house_pct') or 100), _employees(members))
        for record in members:
            mine = _typed(record.terms) if (record.terms or {}).get('shares') else group
            amounts = math.dollars(figures[record.id], mine)
            out[record.id] = (
                figures[record.id],
                [{**share, 'amount': amount} for share, amount in zip(mine, amounts, strict=True)],
            )
    return out
