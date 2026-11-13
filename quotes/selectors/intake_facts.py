"""What quotes tells intake about the plans (plan.md §3.3, O.1; B24, F144): fills `intake.providers.quote_lines`, and
`incumbent`, the one read of the carrier and funding in force on a line (`quotes.facts.incumbent` calls it).

One light query: the deal's live plans without their JSON columns, except the medical `funding` value.
"""

from django.db.models.fields.json import KT

from deals import batch, lines
from intake import selectors as intake_selectors
from intake.models import CurrentCoverage

from .. import presented
from ..models import Plan
from ..shapes import LineData, PlanData

FIELDS = ('id', 'line', 'role', 'carrier', 'starred', 'recommended', 'sold', 'sort_order')


def _batched(ids):
    plans = Plan.objects.filter(deal_id__in=ids).annotate(funding=KT('values__funding'))
    rows = plans.values('deal_id', *FIELDS, 'funding').order_by('sort_order', 'id')
    return batch.grouped(rows, lambda row: row.pop('deal_id'))


def _rows(deal_id, line=None):
    if batch.holds(deal_id):  # every deal's plans in one query (`deals.batch`), each row a copy
        found = batch.per_deal('quotes.plan_rows', deal_id, _batched, ())
        return [dict(row) for row in found if line is None or row['line'] == line]
    plans = Plan.objects.filter(deal_id=deal_id)
    if line is not None:
        plans = plans.filter(line=line)
    return list(plans.annotate(funding=KT('values__funding')).values(*FIELDS, 'funding').order_by('sort_order', 'id'))


def _current(rows):
    """{carrier, funding} of a line's current plans (their carriers once each, in slot order; the first funding
    given), or None when the line has none."""
    current = [row for row in rows if row['role'] == 'current']
    if not current:
        return None
    carriers = list(dict.fromkeys(row['carrier'] for row in current if row['carrier']))
    funding = next((str(row['funding']) for row in current if row['funding']), '')
    return {'carrier': ', '.join(carriers), 'funding': funding}


def quote_lines(deal_id):
    """{line: {presented, sold, current}} for every line holding plans: how many plans it presents (before the
    intent's off rule), whether one is sold, and its current plans' carrier and funding."""
    by_line = {}
    for row in _rows(deal_id):
        by_line.setdefault(row['line'], []).append(row)
    out = {}
    for line, rows in by_line.items():
        plans = [
            PlanData(
                id=row['id'],
                role=row['role'],
                carrier=row['carrier'],
                recommended=row['recommended'],
                sold=row['sold'],
                starred=row['starred'],
                sort_order=row['sort_order'],
            )
            for row in rows
        ]
        basis = lines.BY_KEY[line]['rate_basis'] if line in lines.BY_KEY else 'composite'
        out[line] = {
            'presented': len(presented.presented(LineData(basis, plans, key=line))),
            'sold': any(row['sold'] for row in rows),
            'current': _current(rows),
        }
    return out


def incumbent(deal, line):
    """The carrier and funding in force on a line (F144; §6.5): the line's current plans once the Advisor has them,
    else its first in-force current-coverage row; None when neither says. RFP, commission and the Overview call it.
    Returns {carrier, funding, source} with source 'plans' or 'coverage'."""
    deal_id = getattr(deal, 'id', deal)
    current = _current(_rows(deal_id, line))
    if current:
        return {**current, 'source': 'plans'}
    if batch.holds(deal_id):
        rows = [row for row in intake_selectors.coverage_rows(deal_id) if row.line == line and row.in_force]
        found = {'carrier': rows[0].carrier, 'funding': rows[0].funding} if rows else None
    else:
        row = CurrentCoverage.objects.filter(deal_id=deal_id, line=line, in_force=True).order_by('sort_order', 'id')
        found = row.values('carrier', 'funding').first()
    if found and (found['carrier'] or found['funding']):
        return {**found, 'source': 'coverage'}
    return None
