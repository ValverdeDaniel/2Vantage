"""How close a quote is to a current plan (plan.md §5.4; F51, F121, D-174). Pure.

The score is the old Advisor's "closest to current", ported from the browser to the server: over the line's numeric
axes (per field set, numbers only, so text such as "90 days" never ranks on noise), the mean relative distance
|value − anchor| / max(|anchor|, 1), where a current plan anchors each axis it has and a quote missing an anchored
axis takes a fixed 1.0. With several current plans a quote scores against the nearest one. A fresh star on an
unlinked quote links it to `nearest` (F51); the board's "Closest to current" sort reads `closest` (F32).
"""

from . import values as cleaning

AXES = {
    'medical': ['deductible_single', 'oop_max_single', 'coinsurance', 'rate_ee'],
    'dental': ['den_deductible', 'den_annual_max', 'rate_ee'],
    'vision': ['vis_exam_copay', 'vis_frame_allowance', 'rate_ee'],
    'life': ['unit_rate'],
    'disability': ['dis_benefit_pct', 'dis_max_benefit', 'unit_rate'],
    'stop_loss': ['sl_spec_deductible', 'sl_spec_rate', 'sl_agg_factor'],
    'generic': ['unit_rate'],
}


def _number(plan, key):
    return cleaning.as_float(plan.values.get(key))


def score(plan, current, field_set):
    """The distance from `plan` to `current` (0 is identical), or None when the current plan has none of the axes."""
    anchored = [(key, _number(current, key)) for key in AXES.get(field_set, AXES['generic'])]
    anchored = [(key, anchor) for key, anchor in anchored if anchor is not None]
    if not anchored:
        return None
    total = 0.0
    for key, anchor in anchored:
        value = _number(plan, key)
        total += 1.0 if value is None else abs(value - anchor) / max(abs(anchor), 1)
    return total / len(anchored)


def _scored(plan, currents, field_set):
    scores = [(score(plan, current, field_set), current.id) for current in currents]
    return [(s, cid) for s, cid in scores if s is not None]


def nearest(plan, currents, field_set):
    """The id of the current plan nearest `plan` (the first in slot order on a tie), or None when the line has fewer
    than two current plans or none has any of the axes."""
    if len(currents) < 2:
        return None
    scores = _scored(plan, currents, field_set)
    return min(scores, key=lambda pair: pair[0])[1] if scores else None


def closest(plan, currents, field_set):
    """The score against the nearest current plan, or None (no current plan with an axis; current plans score none)."""
    if plan.role == 'current':
        return None
    scores = _scored(plan, currents, field_set)
    return min(s for s, _ in scores) if scores else None
