"""The Proposal's facts for Agenda and the Overview (plan.md §5.10, O.2; I56–I58, J164): `facts(deal_ids) -> {deal_id:
dict}`, counts, versions and dates only, the same for every viewer. Agenda (slice 60) is the first reader.

Per deal:
- `latest`: the newest issued proposal {version, issued_at (ISO)}, else None (I57, I58);
- `needs`, `picked`: the lines that need our recommendation (on the proposal, not kept as they are, with options and
  nothing sold; `ready.subjects`'s rule) and how many of them have it (I56: "m of n lines recommended");
- `ready`: Issue's gate would let it go (`ready.ready`, the builder's banner and Issue's one answer).
The issues are one query whatever the deal count; the lines are the builder's own fact sheets (`builder.laid_lines`),
worked out for each deal with plans inside one batch scope (`deals.batch`; slice 61), so their rows are read once for
every deal: the same queries for 1 deal or 300 (Q.3 #4).
"""

from deals import batch
from quotes.models import Plan

from . import builder, ready
from .models import ProposalIssue


def _needs(sheet):
    return not sheet['off'] and not sheet['kept'] and bool(sheet['options']) and not sheet['sold']


def _lines(deal):
    stored, stored_marks = builder.stored_rows(deal)
    _blocks, sheets, _entries = builder.laid_lines(deal, stored, stored_marks)
    needing = [sheet for sheet in sheets if _needs(sheet)]
    return {
        'needs': len(needing),
        'picked': sum(1 for sheet in needing if not sheet['missing']),
        'ready': ready.ready(sheets)['ok'],
    }


def facts(deal_ids):
    with batch.scope(deal_ids):
        return _facts(deal_ids)


def _facts(deal_ids):
    deals = batch.deals(deal_ids)
    out = {deal.id: {'latest': None, 'needs': 0, 'picked': 0, 'ready': False} for deal in deals}
    issued = (
        ProposalIssue.objects.filter(deal_id__in=list(out), state=ProposalIssue.ISSUED)
        .order_by('deal_id', '-version')
        .values_list('deal_id', 'version', 'issued_at')
    )
    for deal_id, version, issued_at in issued:
        if out[deal_id]['latest'] is None:
            out[deal_id]['latest'] = {'version': version, 'issued_at': issued_at.isoformat() if issued_at else None}
    with_plans = set(Plan.objects.filter(deal_id__in=list(out)).values_list('deal_id', flat=True))
    for deal in deals:
        if deal.id in with_plans:
            out[deal.id].update(_lines(deal))
    return out
