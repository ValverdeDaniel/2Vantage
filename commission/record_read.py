"""A booked record as the screens read it (plan.md §7.10, §8.13, §8.18; H35, H37, H51, H53): one payload for a Book row,
the booking summary and the record drawer, with its expected revenue, its shares (as the viewer's tier allows), its
holes and where each fact came from. GETs write nothing.

- `with_siblings(records)`: the records plus every other record of their deals, in one query, because shares are
  worked out once per deal (`terms.shares`, H29) and a filtered row must still get its deal's shares.
- `payloads(records, viewer)`: [row] in the given order, with the people's names read once.
"""

from decimal import Decimal

from deals import comp as comps
from deals import lines
from quotes.math import decimal, plain

from . import book_rules, math, parties, terms, visibility, vocab
from .models import Record

ROLE_LABELS = {'house': 'House', **dict(vocab.ROLES)}


def with_siblings(records):
    """{id: record} for `records` and their deals' other records (one query)."""
    out = {record.id: record for record in records}
    deal_ids = {record.deal_id for record in records if record.deal_id}
    if deal_ids:
        for record in Record.objects.filter(deal_id__in=deal_ids).exclude(pk__in=list(out)):
            out[record.id] = record
    return out


def year_label(record):
    if record.year_number:
        return f'yr {record.year_number}'
    return 'year unknown'


def _share_rows(shares, people):
    out = []
    for share in shares:
        person = people.get(('party', share['party'])) if share['party'] else None
        out.append(
            {
                'party': share['party'],
                'key': person['key'] if person else None,
                'name': person['name'] if person else 'House',
                'kind': person['kind'] if person else 'house',
                'role': share['role'],
                'role_label': ROLE_LABELS.get(share['role'], share['role']),
                'share': share['share'],
                'pct': math.pct_text(share['share']),
                'pct_label': math.pct_label(share['share']),
                'amount': plain(share['amount']),
            }
        )
    return out


def money(text):
    return plain(decimal(text)) if text not in (None, '') else None


def origins(record):
    return {key: (entry or {}).get('origin') for key, entry in (record.sources or {}).items()}


def payload(record, figures, people, viewer):
    """One record: its facts, expected revenue, holes and the shares the viewer may see."""
    expected, shares = figures
    merged = book_rules.facts(record)
    house = next((share['amount'] for share in shares if share['role'] == 'house'), None)
    rate = record.values.get('rate')
    return {
        'id': record.id,
        'client_id': record.client_id,
        'client_name': record.client.name,
        'client_archived': record.client.archived_at is not None,
        'deal_id': record.deal_id,
        'line': record.line,
        'line_label': lines.label(record.line),
        'carrier': record.carrier,
        'plan_label': record.values.get('plan_label', ''),
        'plan_ids': record.values.get('plan_ids', []),
        'policy_number': record.values.get('policy_number', ''),
        'effective_date': merged.get('effective_date'),
        'term_end': merged.get('term_end'),
        'year_number': record.year_number,
        'year_label': year_label(record),
        'is_renewal': record.is_renewal,
        'status': record.status,
        'status_label': vocab.STATUS_LABELS.get(record.status, record.status),
        'premium_annual': money(record.values.get('premium_annual')),
        'rate': rate,
        'rate_label': comps.comp_label(rate),
        'employees': record.values.get('employees'),
        'sources': origins(record),
        'expected': plain(expected),
        'house_share': plain(house) if viewer.all else None,
        'shares': _share_rows(visibility.visible_shares(shares, viewer), people),
        'typed_shares': bool((record.terms or {}).get('shares')),
        'reason': (record.terms or {}).get('reason', '') if viewer.all else '',
        'split_from': (record.terms or {}).get('from', ''),
        'holes': book_rules.holes(merged, record.sources or {}, record.year_number, record.deal_id),
        'notes': record.notes,
        'booked_at': record.booked_at.isoformat() if record.booked_at else None,
        'booked_by': parties.user_name(record.booked_by) if record.booked_by_id else '',
        'updated_by': parties.user_name(record.updated_by) if record.updated_by_id else '',
    }


def payloads(records, viewer, everything=None):
    """[row] for `records` (with `client`, `booked_by` and `updated_by` selected). `everything` is `with_siblings`'s
    answer when the caller already has it."""
    everything = everything or with_siblings(records)
    figures = terms.shares(list(everything.values()))
    people = parties.lookup(parties.people())
    return [payload(record, figures[record.id], people, viewer) for record in records]


def totals(rows, viewer):
    """The tiles' figures over Book rows (H45): expected counts booked and active records only (bug 5)."""
    live = [row for row in rows if row['status'] in vocab.LIVE]
    expected = [Decimal(str(row['expected'])) for row in live if row['expected'] is not None]
    total = sum(expected, Decimal(0)) if expected else None
    holes = sum(1 for row in rows if row['holes'])
    out = {'records': len(rows), 'live': len(live), 'expected': plain(total), 'holes': holes}
    if viewer.all:
        house = [Decimal(str(row['house_share'])) for row in live if row['house_share'] is not None]
        house_total = sum(house, Decimal(0)) if house else None
        out['house'] = plain(house_total)
        out['pool'] = plain(total - house_total) if total is not None and house_total is not None else None
    return out


ROLE_ORDER = ('house', *vocab.ROLE_KEYS)


def who_gets_what(rows):
    """Each person's share across the rows (the booking summary's "Who gets what", H35): their role, the share or its
    range across the lines, and their dollars summed on the server (rule 5)."""
    people = {}
    for row in rows:
        for share in row['shares']:
            key = (share['role'], share['party'])
            entry = people.setdefault(
                key, {'role': share['role'], 'role_label': share['role_label'], 'name': share['name'],
                      'kind': share['kind'], 'shares': [], 'amount': None},
            )  # fmt: skip
            entry['shares'].append(share['share'])
            if share['amount'] is not None:
                entry['amount'] = (entry['amount'] or Decimal(0)) + Decimal(str(share['amount']))
    out = []
    for entry in sorted(people.values(), key=lambda entry: ROLE_ORDER.index(entry['role'])):
        low, high = min(entry['shares']), max(entry['shares'])
        label = math.pct_label(low) if low == high else f'{math.pct_label(low)[:-1]}–{math.pct_label(high)}'
        out.append({**{k: v for k, v in entry.items() if k != 'shares'}, 'pct_label': label,
                    'amount': plain(entry['amount'])})  # fmt: skip
    return out
