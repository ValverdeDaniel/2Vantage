"""What each line knows of its people beyond its plans (plan.md §5.5, §5.3.6; F88–F91, N.1), read once per request.

`load(deal_id, line_keys)` → {line: `shapes.People`}: the lines' `LineEnrollment` rows (the whole-line figure, the
switch, `typed_at` and `census_seen`) and the census's stored rollup for each line with its last import time, plus how
many imports the deal has applied (`applied_imports`, what F91 compares `census_seen` with), in at most three queries
(the census's figures come from `CensusFacts`, never a census query per plan, C23). Medical's people, which worksite
tier-rated lines borrow (OQ19) and stop-loss counts as lives (F98), are set by `state.deal_state`, which prices medical
first.
"""

from django.db.models import Count

from census import facts as census_facts
from census import rollup
from census.models import CensusImport
from deals import batch, lines

from ..models import LineEnrollment
from ..shapes import People

MEDICAL = 'medical'


def borrows(line_key):
    """A line that reads medical's people: worksite tier-rated lines and stop-loss."""
    entry = lines.BY_KEY.get(line_key) or {}
    return bool(entry.get('proxy')) or entry.get('rate_basis') == 'stop_loss'


def applied_imports(deal_id, stored=None):
    """How many census imports the deal has applied: a count that only grows (an applied import is never discarded),
    so "an import came after the typed counts" never rests on the clock (F91). No query while nothing was imported."""
    stored = stored or census_facts.stored(deal_id)
    if stored['last_import_at'] is None:
        return 0
    return batch.per_deal('quotes.applied_imports', deal_id, _applied, 0)


def _applied(ids):
    applied = CensusImport.objects.filter(deal_id__in=ids, status=CensusImport.APPLIED)
    return dict(applied.order_by().values('deal_id').annotate(n=Count('id')).values_list('deal_id', 'n'))


def _enrollment_rows(ids):
    return batch.grouped(LineEnrollment.objects.filter(deal_id__in=ids), lambda row: row.deal_id)


def load(deal_id, line_keys):
    wanted = set(line_keys)
    found = batch.per_deal('quotes.line_enrollment', deal_id, _enrollment_rows, ())
    rows = {row.line: row for row in found if row.line in wanted}
    stored = census_facts.stored(deal_id)
    imports = applied_imports(deal_id, stored)
    out = {}
    for key in line_keys:
        row = rows.get(key)
        out[key] = People(
            on=row.on if row else True,
            figure=dict(row.enrollment) if row else {},
            typed_at=row.typed_at if row else None,
            census=rollup.for_line(stored['rollup'], key),
            imported_at=stored['last_import_at'],
            imports=imports,
            census_seen=row.census_seen if row else None,
        )
    return out
