"""The facts the Next ranking reads, for one deal (plan.md §8.8; L3, L4, L14, L25; `rules.next`). A fixed number of
queries: the client's open questions and the answers waiting, the newest ask sent on each request, the census counts
and the quotes' facts; the requests' rows and the Missing lane come from the Board that already read them.

`entries(deal, rows, found, lane, now)` → the ranked entries (`rules.next.rank`, up to 8): `rows` the deal's request
rows (`selectors.requests`), `found` its `summary.facts`, `lane` its Missing lane (`selectors.missing.lane`).
"""

from datetime import datetime

from django.db.models import Count, Max, Min

from census.models import CensusFacts
from quotes import summary as quotes_summary

from ..models import ASK_KINDS, ReviewNote
from ..rules import next as next_rules
from ..rules import requests as request_rules
from . import entries as entry_rows


def _moment(value):
    if isinstance(value, datetime) or not value:
        return value or None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _links(deal, rows):
    newest = dict(
        ReviewNote.objects.filter(deal_id=deal.id, kind__in=ASK_KINDS, sent_at__isnull=False)
        .values_list('request_id')
        .annotate(at=Max('sent_at'))
    )
    out = []
    for row in rows:
        if row['state'] not in request_rules.OPEN_STATES:
            continue
        for person in row['recipients']:
            asked = [at for at in (_moment(person['sent_at']), newest.get(row['id'])) if at]
            opened = _moment(person['last_opened_at'])
            out.append({
                'link_id': person['link_id'],
                'request_id': row['id'],
                'name': person['name'],
                'days_left': person['days_left'],
                'sent': person['sent'],
                'submitted': bool(person['submitted_at']),
                'expired': person['expired'] or person['revoked'],
                'unopened': bool(asked) and (opened is None or opened < max(asked)),
            })  # fmt: skip
    return out


def _questions(deal):
    grouped = (
        ReviewNote.objects.filter(deal_id=deal.id, kind='question', resolved_at__isnull=True)
        .values('surface')
        .annotate(n=Count('id'), oldest=Min('at'))
    )
    return {row['surface']: (row['n'], row['oldest']) for row in grouped}


def _answers(deal):
    out = {}
    for entry in entry_rows.waiting([deal.id]).get(deal.id, []):
        count, oldest = out.get(entry.surface, (0, None))
        at = _moment(entry.at)
        out[entry.surface] = (count + 1, min(filter(None, (oldest, at)), default=None))
    return out


def entries(deal, rows, found, lane, now):
    counts = {row['key']: row['count'] for row in lane}
    people = CensusFacts.objects.filter(deal_id=deal.id).values_list('employees', 'dependents').first() or (0, 0)
    quotes = (quotes_summary.facts([deal.id]).get(deal.id) or {}).get('quotes', 0)
    facts = {
        'links': _links(deal, rows),
        'questions': _questions(deal),
        'intake_required': counts.get('intake', 0),
        'census_required': counts.get('census', 0),
        'no_census': sum(people) == 0,
        'quotes_in': bool(quotes),
        'answers': _answers(deal),
        'files': (found.get('pending') or {}).get('documents', 0),
    }
    return next_rules.rank(facts, now)
