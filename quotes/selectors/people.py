"""What each line knows of its people beyond its plans (plan.md §5.5, §5.3.6; F88–F91, N.1), read once per request.

`load(deal_id, line_keys)` → {line: `shapes.People`}: the lines' `LineEnrollment` rows (the whole-line figure, the
switch and `typed_at`) and the census's stored rollup for each line with its last import time, in two queries (the
census's figures come from `CensusFacts`, never a census query per plan, C23). Medical's people, which worksite
tier-rated lines borrow (OQ19) and stop-loss counts as lives (F98), are set by `state.deal_state`, which prices medical
first.
"""

from census import facts as census_facts
from census import rollup
from deals import lines

from ..models import LineEnrollment
from ..shapes import People

MEDICAL = 'medical'


def borrows(line_key):
    """A line that reads medical's people: worksite tier-rated lines and stop-loss."""
    entry = lines.BY_KEY.get(line_key) or {}
    return bool(entry.get('proxy')) or entry.get('rate_basis') == 'stop_loss'


def load(deal_id, line_keys):
    rows = {row.line: row for row in LineEnrollment.objects.filter(deal_id=deal_id, line__in=list(line_keys))}
    stored = census_facts.stored(deal_id)
    out = {}
    for key in line_keys:
        row = rows.get(key)
        out[key] = People(
            on=row.on if row else True,
            figure=dict(row.enrollment) if row else {},
            typed_at=row.typed_at if row else None,
            census=rollup.for_line(stored['rollup'], key),
            imported_at=stored['last_import_at'],
        )
    return out
