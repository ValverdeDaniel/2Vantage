"""Per-line counts for the Advisor's line tabs (plan.md §7.8; F.5 #37, J81): `GET deals/{id}/plans/lines/`.

Two light queries at any plan count: the deal's plans without their JSON columns, and their links. Coverage of the
recommendation reads links only, so nothing is priced here. `off` is intake's word for a line kept off the proposal
(F13): its rule (`intake.selectors.line_facts`) reads the coverage intent in two more queries.
"""

from deals import lines
from intake import coverage as intake_coverage
from intake.selectors import line_facts

from .. import packages as pk
from .. import presented
from ..models import Plan
from ..shapes import LineData, PlanData
from .state import replaced_ids

ROLES = ('current', 'renewal', 'alternate')
FIELDS = ('id', 'line', 'role', 'carrier', 'name', 'renews_id', 'starred', 'recommended', 'sold', 'sort_order')


def lines_summary(deal):
    rows = list(Plan.objects.filter(deal=deal).values(*FIELDS))
    links = replaced_ids(from_plan__deal=deal, from_plan__removed_at__isnull=True)
    by_line = {}
    for row in rows:
        by_line.setdefault(row['line'], []).append(row)
    keys = [key for key in lines.LINE_KEYS if key in deal.requested_lines or key in by_line]
    keys += [key for key in by_line if key not in keys]
    _states, off = line_facts(deal, {key: {'sold': any(row['sold'] for row in rows)} for key, rows in by_line.items()})
    summary = []
    for key in keys:
        plans = [
            PlanData(
                id=row['id'],
                role=row['role'],
                carrier=row['carrier'],
                name=row['name'],
                renews=row['renews_id'],
                replaces=tuple(links.get(row['id'], ())),
                recommended=row['recommended'],
                sold=row['sold'],
                starred=row['starred'],
                sort_order=row['sort_order'],
            )
            for row in by_line.get(key, [])
        ]
        data = LineData(lines.BY_KEY[key]['rate_basis'] if key in lines.BY_KEY else 'composite', plans, key=key)
        covered, _missing = pk.coverage(data) if plans else (False, [])
        summary.append(
            {
                'line': key,
                'label': lines.label(key),
                'requested': key in deal.requested_lines,
                **{role: sum(1 for p in plans if p.role == role) for role in ROLES},
                'starred': sum(1 for p in plans if p.starred),
                'recommended': sum(1 for p in plans if p.recommended),
                'recommendation_covered': covered,
                'columns': len(presented.presented(data)),
                'room': presented.room(data),
                'sold_plans': [p.words for p in sorted(plans, key=lambda p: (p.sort_order, p.id)) if p.sold],
                'off': off.get(key),  # 'left_off' | 'not_in_intent' | None: the "Off the proposal" chip (F13)
                'off_reason': intake_coverage.OFF_LABELS.get(off.get(key), ''),
            }
        )
    return summary
