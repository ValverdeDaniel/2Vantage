"""The Book and By person (plan.md §7.10, §8.18; H45, H49–H51, H68): reads over the booked records, scoped to the
viewer's tier (`visibility`), in a fixed number of queries whatever their size. GETs write nothing.

- `filters(params)`: the Book's filters (H49): `q` (client, carrier, plan), `client`, `deal`, `party`, `record`,
  `status` (blank: every status but void; `void` shows the void ones), `year` (the effective year). A bad id answers
  400. The person filter is the all tier's (the own tier sees only its own records anyway).
- `book(params, viewer)`: {rows (capped, H50), capped, totals (the tiles, H45: expected, house, pool, next 12 months,
  booked records), groups (each client's sums, for Group by client), years}. One answer per filter change carries the
  rows and the totals; the browser sums nothing (rule 5).
- `people(params, viewer)`: By person (H68): each person's records and expected share, and their share of the book;
  the own tier sees its own row only. `person_records(key, params, viewer)` is the drill-down.
"""

import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from deals import clock
from quotes.math import plain, round_decimal

from . import record_read, visibility, vocab
from .models import Record
from .services.clean import record_id

FILTER_IDS = ('client', 'deal', 'party', 'record')
HOUSE = 'house'


def filters(params):
    """{name: cleaned value} of the filters asked for; 400 on a bad one."""
    out = {}
    q = ' '.join(str(params.get('q') or '').split())[:100]
    if q:
        out['q'] = q
    for name in FILTER_IDS:
        if params.get(name) not in (None, ''):
            out[name] = record_id(params.get(name), name)
    status = params.get('status') or ''
    if status and status not in vocab.STATUS_KEYS:
        raise ValidationError({'status': ['Pick a status.']})
    out['status'] = status
    year = params.get('year') or ''
    if year:
        if not str(year).isdigit() or not 1900 < int(year) < 2200:
            raise ValidationError({'year': ['Pick a year.']})
        out['year'] = int(year)
    return out


def queryset(wanted, viewer):
    records = Record.objects.select_related('client', 'booked_by', 'updated_by')
    records = visibility.scoped(records, viewer)
    if wanted.get('q'):
        q = wanted['q']
        records = records.filter(
            Q(client__name__icontains=q) | Q(carrier__icontains=q) | Q(values__plan_label__icontains=q)
        )
    for name in ('client', 'deal'):
        if name in wanted:
            records = records.filter(**{f'{name}_id': wanted[name]})
    if 'record' in wanted:
        records = records.filter(pk=wanted['record'])
    if 'party' in wanted and viewer.all:
        records = records.filter(party_ids__contains=[wanted['party']])
    status = wanted.get('status')
    records = records.filter(status=status) if status else records.exclude(status=vocab.VOID)
    if 'year' in wanted:
        records = records.filter(effective_date__year=wanted['year'])
    return records.order_by('client__name', '-effective_date', 'line', 'id')


def _month_starts(today):
    out = []
    for i in range(12):
        index = today.month - 1 + i
        out.append(date(today.year + index // 12, index % 12 + 1, 1))
    return out


def _year_after(day):
    last = calendar.monthrange(day.year + 1, day.month)[1]
    return date(day.year + 1, day.month, min(day.day, last))


def next_twelve(rows, today):
    """Expected revenue over the next 12 months from live records in force each month (expected ÷ 12 a month across
    each term, a term being a year unless it has its own end; 891f1b3 `rollup_summary`'s forward view)."""
    total, counted = Decimal(0), False
    months = _month_starts(today)
    for row in rows:
        if row['status'] not in vocab.LIVE or row['expected'] is None or not row['effective_date']:
            continue
        start = date.fromisoformat(row['effective_date']).replace(day=1)
        end = date.fromisoformat(row['term_end']) if row['term_end'] else _year_after(start)
        monthly = round_decimal(Decimal(str(row['expected'])) / 12, 2)
        for first in months:
            if start <= first < end:
                total += monthly
                counted = True
    return plain(total) if counted else None


def book(params, viewer):
    wanted = filters(params)
    records = list(queryset(wanted, viewer))
    rows = record_read.payloads(records, viewer)
    totals = {**record_read.totals(rows, viewer), 'next_12': next_twelve(rows, clock.today())}
    years = sorted({row['effective_date'][:4] for row in rows if row['effective_date']}, reverse=True)
    capped = len(rows) > vocab.BOOK_CAP
    return {
        'rows': rows[: vocab.BOOK_CAP],
        'capped': capped,
        'cap': vocab.BOOK_CAP,
        'totals': totals,
        'groups': groups(rows, viewer),
        'years': years,
    }


def groups(rows, viewer):
    """{client id: the client's sums} for "Group by client" (H50): expected and house over its live rows."""
    by_client = {}
    for row in rows:
        by_client.setdefault(row['client_id'], []).append(row)
    return {client_id: record_read.totals(members, viewer) for client_id, members in by_client.items()}


def _person_key(share):
    return HOUSE if share['role'] == 'house' else share['party']


def people(params, viewer):
    """By person (H68): [{key, party, name, kind, records, expected, share_of_book}] by expected, largest first."""
    wanted = filters({'year': params.get('year'), 'status': ''})
    rows = [row for row in record_read.payloads(list(queryset(wanted, viewer)), viewer) if row['status'] in vocab.LIVE]
    found = {}
    for row in rows:
        for share in row['shares']:
            entry = found.setdefault(
                _person_key(share),
                {'key': _person_key(share), 'party': share['party'], 'name': share['name'], 'kind': share['kind']},
            )
            entry['records'] = entry.get('records', 0) + 1
            if share['amount'] is not None:
                entry['expected'] = entry.get('expected', Decimal(0)) + Decimal(str(share['amount']))
    total = sum((entry.get('expected', Decimal(0)) for entry in found.values()), Decimal(0))
    out = []
    for entry in found.values():
        mine = entry.pop('expected', None)
        entry['expected'] = plain(round_decimal(mine, 2)) if mine is not None else None
        entry['share_of_book'] = plain(round_decimal(mine * 100 / total, 1)) if mine is not None and total else None
        out.append(entry)
    out.sort(key=lambda entry: -(entry['expected'] or 0))
    years = sorted({row['effective_date'][:4] for row in rows if row['effective_date']}, reverse=True)
    return {'rows': out, 'years': years, 'total': plain(total) if rows else None}


def person_records(key, params, viewer):
    """The records behind one person's row (H68's drill-down), with their own share on each."""
    if key != HOUSE:
        key = record_id(key, 'party')
    if key == HOUSE and not viewer.all:
        return {'rows': []}
    if viewer.tier == visibility.OWN and key != viewer.party_id:
        return {'rows': []}
    wanted = filters({'year': params.get('year'), 'status': ''})
    records = queryset(wanted, viewer)
    if key != HOUSE:
        records = records.filter(party_ids__contains=[key])
    rows = [row for row in record_read.payloads(list(records), viewer) if row['status'] in vocab.LIVE]
    out = []
    for row in rows:
        mine = next((share for share in row['shares'] if _person_key(share) == key), None)
        if mine is not None:
            out.append({**row, 'mine': mine})
    return {'rows': out}
