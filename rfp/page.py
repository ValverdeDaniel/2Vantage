"""The RFP tab's payload (plan.md §7.11, §8.12; K4, K6–K9, K17–K29): what the page draws above the packet. A GET writes
nothing and makes no row (a deal with no RfpRequest reads as the defaults).

- `client_name`: intake's legal name, else the client's name (K4, X-150).
- `request`: the settings with every default filled in: the route and the band's own (`route_default`), what is
  stored (`route_stored`), the funding and whether it is the default (`funding_default`), the carriers picked, other
  carriers, the due date and the notes.
- `band`: the size band from the one headcount (K17, K18; `quotes.facts`), with its count, where the count came
  from and whether it is an estimate; `enrollment`: the three answers to "how many are enrolled" and the warning that
  names them when they differ (K19, `quotes.facts.enrollment_check`).
- `carriers`: one chip per carrier, eligibility and its reason (K23, K24). `lines`: the requested lines (K16).
- `commission`: the text the form prints (K29), from the agency default until commission is built.
- `census`: the census line (K8). `done`: the cards' marks, each with the marker's name (K9).
"""

from django.contrib.auth import get_user_model

from census import facts as census_facts
from deals import carriers as identities
from deals import lines
from deals.models import AgencySettings
from intake.models import Intake
from quotes import facts as quote_facts
from quotes.selectors.headcount import WHERE

from . import cleaners, request, services
from .models import RfpRequest


def _names(ids):
    wanted = {pk for pk in ids if pk}
    if not wanted:
        return {}
    return {user.id: user.get_full_name() or user.username for user in get_user_model().objects.filter(pk__in=wanted)}


def marks(done):
    """{card: {by: name, by_id, at}} for the cards marked completed, in page order."""
    found = {card: stamp for card, stamp in (done or {}).items() if card in services.CARD_KEYS and stamp}
    names = _names(stamp.get('by') for stamp in found.values())
    return {
        card: {'by': names.get(stamp.get('by'), ''), 'by_id': stamp.get('by'), 'at': stamp.get('at')}
        for card in services.CARD_KEYS
        if (stamp := found.get(card))
    }


def band_block(check):
    used = check['used']
    key = request.band(used['count'])
    return {
        'key': key,
        'label': request.band_label(key),
        'count': used['count'],
        'source': used['source'],
        'estimate': bool(used['estimate']),
        'from': WHERE.get(used['source'], ''),
    }


def band_block_for(deal):
    """The band alone, for a write's answer (no cross-check)."""
    return band_block({'used': quote_facts.enrolled_headcount(deal)})


def request_block(deal, row, band_key):
    stored = cleaners.stored(row)
    route, route_default = request.route(stored['route'], band_key)
    funding = request.funding(stored['funding'], services.default_funding(deal) if stored['funding'] is None else [])
    return {
        'route': route,
        'route_default': route_default,
        'route_stored': stored['route'],
        'carriers': stored['carriers'],
        'other_carriers': stored['other_carriers'],
        'funding': funding,
        'funding_default': stored['funding'] is None,
        'due_date': stored['due_date'],
        'notes': stored['notes'],
    }


def census_block(deal_id):
    found = census_facts.summary(census_facts.stored(deal_id))
    return {
        'has_roster': found['employees'] + found['dependents'] > 0,
        'employees': found['employees'],
        'dependents': found['dependents'],
        'readiness_pct': found['readiness_pct'],
        'errors': found['errors'],
    }


def request_parts(deal, row, band_key):
    """The blocks a request edit redraws: the settings, the carrier chips and the marks."""
    block = request_block(deal, row, band_key)
    requested = [line for line in lines.LINE_KEYS if line in set(deal.requested_lines or [])]
    chips = request.chips(set(block['carriers']), band_key, requested, identities.CARRIERS)
    return {'request': block, 'carriers': chips, 'done': marks(row.done if row else {})}


def page(deal):
    row = RfpRequest.objects.filter(deal_id=deal.id).first()
    check = quote_facts.enrollment_check(deal)
    band = band_block(check)
    requested = [line for line in lines.LINE_KEYS if line in set(deal.requested_lines or [])]
    answers = Intake.objects.filter(deal_id=deal.id).values_list('answers', flat=True).first() or {}
    text, breakdown = request.commission_text(requested, {}, AgencySettings.get().default_commission)
    return {
        'deal_id': deal.id,
        'client_name': str(answers.get('legal_name') or '').strip() or deal.client.name,
        **request_parts(deal, row, band['key']),
        'band': band,
        'enrollment': {key: check[key] for key in ('intake', 'census', 'advisor', 'differ', 'warning')},
        'lines': [{'key': line, 'label': lines.label(line)} for line in requested],
        'commission': {'text': text, 'breakdown': breakdown, 'source': 'agency' if text else ''},
        'census': census_block(deal.id),
    }
