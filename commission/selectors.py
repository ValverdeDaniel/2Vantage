"""Commission's reads (plan.md §7.10, §8.13; H3–H24, H106, H109). GETs write nothing (Q.3 #2).

- `deal_payload(deal, viewer)`: the Commission tab: the rates grid and the deal total (`revenue.line_rows`), the split
  that applies with its source and the live preview, the picker's people, and whether the viewer may save a split.
- `client_payload(client, viewer)`: the client-scope split editor (H106; the client page mounts it in slice 68).
- `preview(...)`: what the split pays in the year, shares in millionths and dollars (H18); the preview endpoint and
  the GET share it, and so does the save's validation (`rules.validate_rows`), so a preview never disagrees with a save.
- `requested_rates(deal)`: the rate each requested line asks the carriers for (H109): rfp prints it (K29).
- `can_save(viewer, owner_id)`: the all tier, or the owner (OQ70 default).
"""

from decimal import Decimal

from accounts.access import commission_tier
from deals import comp as comps
from deals import lines
from deals.models import AgencySettings
from quotes.math import plain

from . import math, parties, revenue, rules, vocab
from .models import ClientSplit, Commission, Settings

HUNDRED = Decimal(100)


def can_save(viewer, owner_id):
    return commission_tier(viewer) == 'all' or bool(owner_id and owner_id == getattr(viewer, 'id', None))


def agency_default():
    return revenue.comp_or_none(AgencySettings.get().default_commission)


def requested_rates(deal):
    """{line: {'rate': Comp, 'source': 'deal' | 'agency'}} for each requested line with a rate: the deal's agreed
    rate, else the agency default (H5, H8, H109)."""
    row = Commission.objects.filter(deal_id=deal.id).values_list('rates', flat=True).first() or {}
    agency = agency_default()
    out = {}
    for line in [key for key in lines.LINE_KEYS if key in set(deal.requested_lines or [])]:
        rate, source = revenue.effective(revenue.comp_or_none(row.get(line)), agency)
        if rate:
            out[line] = {'rate': rate, 'source': source}
    return out


def _text(number):
    return format(Decimal(number).normalize(), 'f')


def year_label(year):
    """The preview's words for the year: first year, renewal (year N), or renewal with the year not known."""
    if year == 1:
        return 'first year'
    return f'renewal, year {year}' if year else 'renewal, year unknown'


def preview(rows, people, settings, revenue_total, employees, year):
    """What `rows` pay in `year` on `revenue_total`: the house and producer %, and each share in millionths, as a
    percentage's text and in dollars (H18). `people` is `parties.lookup`; rows name `party` or `user`."""
    keyed = [{**row, 'party': parties.key_of(row)} for row in rows]
    primary = next((row for row in keyed if row['role'] == vocab.PRIMARY), None)
    first_year = year == 1
    pct, pct_source = rules.producer_pct(people.get(primary['party']) if primary else None, settings, first_year)
    shares = math.compute_shares(revenue_total, math.year_terms(keyed, year), HUNDRED - pct, employees)
    amounts = math.dollars(revenue_total, shares)
    out = []
    for share, amount in zip(shares, amounts, strict=True):
        person = people.get(share['party']) if share['party'] else None
        out.append(
            {
                'key': person['key'] if person else None,
                'name': person['name'] if person else 'House',
                'role': share['role'],
                'share': share['share'],
                'pct': math.pct_text(share['share']),
                'pct_label': math.pct_label(share['share']),
                'amount': plain(amount),
            }
        )
    return {
        'year': year,
        'first_year': first_year,
        'year_label': year_label(year),
        'producer_pct': _text(pct),
        'house_pct': _text(HUNDRED - pct),
        'pct_source': pct_source,
        'revenue': plain(revenue_total),
        'employees': employees,
        'shares': out,
    }


def row_payload(row, people):
    """A stored or cleaned row as the editor reads it, with the person's key, name and kind."""
    person = people.get(parties.key_of(row)) or {}
    return {
        'key': person.get('key'),
        'party': row.get('party'),
        'user': row.get('user') if not row.get('party') else None,
        'name': person.get('name', ''),
        'kind': person.get('kind', ''),
        'role': row['role'],
        'amount': row.get('amount'),
        'amount_label': comps.comp_label(row.get('amount')),
        'renewal_amount': row.get('renewal_amount'),
        'basis': row.get('basis') or vocab.POOL,
        'expires_after_years': row.get('expires_after_years'),
        'works_it': bool(row.get('works_it')),
    }


def _split_block(source, rows, people, entries, viewer, owner_id, scope):
    return {
        'source': source,
        'source_label': vocab.SOURCES[source],
        'rows': [row_payload(row, people) for row in rows],
        'scope': scope,
        'can_save': can_save(viewer, owner_id),
        'needs_primary': source == vocab.HOUSE,
        'parties': parties.picker(entries, rows),
    }


def _client_rows(client_id):
    return ClientSplit.objects.filter(client_id=client_id).values_list('rows', flat=True).first() or []


def deal_payload(deal, viewer):
    row = Commission.objects.filter(deal_id=deal.id).first() or Commission(deal=deal)
    agency = agency_default()
    grid, total, note, (employees, _line) = revenue.line_rows(deal, row.rates or {}, agency)
    entries = parties.people()
    people = parties.lookup(entries)
    source, rows = rules.resolve(
        (row.split or {}).get('rows'),
        _client_rows(deal.client_id),
        parties.owner_person(deal.owner_id, entries),
        parties.owner_person(deal.client.owner_id, entries),
    )
    year = rules.year_number(row.year_number, deal.opened_as)
    scope = vocab.DEAL if source == vocab.DEAL else vocab.CLIENT
    return {
        'deal_id': deal.id,
        'client_id': deal.client_id,
        'client_name': deal.client.name,
        'rows': grid,
        'total': total,
        'note': note,
        'agency_default': agency,
        'agency_default_label': comps.comp_label(agency),
        'year_number': row.year_number,
        'split': _split_block(source, rows, people, entries, viewer, deal.owner_id, scope),
        'basis': {'revenue': total, 'employees': employees, 'year': year},
        'preview': preview(rows, people, Settings.get(), total, employees, year),
    }


def client_payload(client, viewer):
    """The client's split (H106): the client's own, else the client owner, else the house. There is no revenue at the
    client level, so the preview shows percentages only; the year is the first until slice 49's records count."""
    entries = parties.people()
    people = parties.lookup(entries)
    source, rows = rules.resolve(None, _client_rows(client.id), None, parties.owner_person(client.owner_id, entries))
    return {
        'client_id': client.id,
        'client_name': client.name,
        'split': _split_block(source, rows, people, entries, viewer, client.owner_id, vocab.CLIENT),
        'basis': {'revenue': None, 'employees': None, 'year': 1},
        'preview': preview(rows, people, Settings.get(), None, None, 1),
    }


def settings_payload():
    """The Settings tab (H100): the producer % defaults with the house's rest, whether they are confirmed, and the
    agency's default rate."""
    row = Settings.get()
    agency = agency_default()
    confirmed_by = row.confirmed_by if row.confirmed_at else None
    return {
        'first_year_pct': _text(row.first_year_pct),
        'renewal_pct': _text(row.renewal_pct),
        'first_year_house_pct': _text(HUNDRED - row.first_year_pct),
        'renewal_house_pct': _text(HUNDRED - row.renewal_pct),
        'confirmed': row.confirmed_at is not None,
        'confirmed_by': parties.user_name(confirmed_by) if confirmed_by else '',
        'confirmed_at': row.confirmed_at.isoformat() if row.confirmed_at else None,
        'default_commission': agency,
        'default_commission_label': comps.comp_label(agency),
    }
