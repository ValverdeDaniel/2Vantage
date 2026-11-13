"""`facts_for(deal_ids)`: one facts dict per deal, from every app's `summary.facts` (plan.md §5.10, I.4; O.6 #3).

Agenda imports each app's summary directly (there is no registry in `deals`); a lost deal reads only its own row, since
it has no steps (I66). Per deal: `deal` {id, stage, lost, lost_reason, sold, client_id, owner_id, effective_date},
`intake`, `census`, `quotes`, `proposals`, `rfp`, `commission` {unrated: sold lines no rate applies to}, `review` (its
facts plus `raw_asks`: each open request's stored asks, what Agenda's "waiting on the client" reads, I45),
`documents` {questionnaire_files: [{id, review_state}]} and `nudges` (`agenda.nudges.of`).

Each app's own reads are batched, and the left apps' per-deal parts (intake's providers, quotes' pricing, the
proposal's line sheets) read their rows once for every deal asked, inside one batch scope (`deals.batch`; slice 61): the
Work queue's facts for 300 deals run the same queries as for one (Q.3 #4, Q.7).
"""

from census import summary as census_summary
from commission import summary as commission_summary
from commission.selectors import agency_default
from deals import batch, clock
from deals.models import Deal
from documents.models import Document
from intake import summary as intake_summary
from proposals import summary as proposal_summary
from quotes import summary as quote_summary
from review import summary as review_summary
from review.models import ClientRequest
from rfp import summary as rfp_summary

from . import nudges


def _deal(deal):
    return {
        'id': deal.id,
        'stage': deal.stage,
        'lost': deal.stage == 'lost',
        'lost_reason': deal.lost_reason,
        'sold': deal.stage == 'sold',
        'client_id': deal.client_id,
        'owner_id': deal.owner_id,
        'effective_date': deal.effective_date.isoformat() if deal.effective_date else None,
    }


def _raw_asks(ids):
    found = {}
    rows = ClientRequest.objects.filter(deal_id__in=ids, closed_at__isnull=True).values_list('deal_id', 'id', 'asks')
    for deal_id, request_id, asks in rows:
        found.setdefault(deal_id, {})[request_id] = asks or {}
    return found


def _questionnaire_files(ids):
    found = {}
    files = (
        Document.objects.filter(deal_id__in=ids, kind='questionnaire', protected=False)
        .exclude(review_state='wrong')
        .order_by('id')
        .values_list('deal_id', 'id', 'review_state')
    )
    for deal_id, doc_id, state in files:
        found.setdefault(deal_id, []).append({'id': doc_id, 'review_state': state})
    return found


def _unrated(sold_lines, rated_lines, agency):
    """The sold lines no rate applies to: no agreed rate on the deal and no agency default (H5, H8; I63)."""
    if agency:
        return []
    return [line for line in sold_lines if line not in set(rated_lines)]


def facts_for(deal_ids, now=None, *, lost_too=False):
    """{deal_id: facts} (above), in the same number of queries for one deal or many: every app's per-deal reads run
    once for all of them inside one batch scope (`deals.batch`; Q.3 #4, slice 61). `lost_too`: a lost deal's facts are
    read too (the shell's meters and badges still describe it; it still has no steps)."""
    now = now or clock.now()
    deals = list(Deal.objects.filter(pk__in=list(deal_ids)))
    out = {deal.id: {'deal': _deal(deal)} for deal in deals}
    ids = [deal.id for deal in deals if lost_too or deal.stage != 'lost']
    if not ids:
        return out
    with batch.scope(ids):
        _gather(out, ids, now)
    return out


def _gather(out, ids, now):
    intake = intake_summary.facts(ids)
    census = census_summary.facts(ids)
    quotes = quote_summary.facts(ids)
    proposals = proposal_summary.facts(ids)
    rfp = rfp_summary.facts(ids)
    commission = commission_summary.facts(ids)
    review = review_summary.facts(ids, now)
    raw = _raw_asks(ids)
    files = _questionnaire_files(ids)
    held = nudges.of(ids, now)
    agency = agency_default()
    for deal_id in ids:
        found = out[deal_id]
        sold_lines = (quotes.get(deal_id) or {}).get('sold_lines') or []
        found['deal']['sold'] = found['deal']['sold'] or bool(sold_lines)
        found.update(
            intake=intake.get(deal_id) or {},
            census=census.get(deal_id) or {},
            quotes=quotes.get(deal_id) or {},
            proposals=proposals.get(deal_id) or {},
            rfp=rfp.get(deal_id) or {},
            commission={
                **(commission.get(deal_id) or {}),
                'unrated': _unrated(sold_lines, (commission.get(deal_id) or {}).get('rated_lines') or [], agency),
            },
            review={**(review.get(deal_id) or {}), 'raw_asks': raw.get(deal_id, {})},
            documents={'questionnaire_files': files.get(deal_id, [])},
            nudges=held.get(deal_id, []),
        )
