"""Which plan on the deal a plan the read found is (plan.md §10.4; D59, D116, D117, F141, F143). Pure: plans in.

A found plan is matched only to a live plan of the same line and role (current, renewal, alternate), never to a priced
version (F141). In order: the reader's own reference from an earlier read (`read_ref`); a shared plan-number half
("05182 / 05183" matches either, D116); a shared strong code; then the one plan with its carrier and name. A tier
that finds two plans matches neither. A renewal whose current plan matched is that plan's renewal, if it has one.
"""

from ai import codes

from .merge import norm

ROLE_OF_SIDE = {'current': 'current', 'renewal': 'renewal', 'quote': 'alternate'}


def ref_key(found):
    """The reader's reference for a plan it made, stored on the plan (`read_ref.key`) so the next read finds it."""
    return '|'.join((found['line'], found['side'], norm(found['carrier']), norm(found['name'])))


def _codes_of(plan):
    return [*(plan.codes or []), *codes.parse(plan.plan_number)]


def _one(matches):
    return matches[0] if len(matches) == 1 else None


def candidates(plans, line, role):
    return [plan for plan in plans if plan.line == line and plan.role == role and not plan.derived_from_id]


def match(found, plans, renews_plan=None):
    """(plan, how) or (None, '') for one merged plan against the deal's live plans."""
    role = ROLE_OF_SIDE.get(found['side'], 'alternate')
    pool = candidates(plans, found['line'], role)
    if role == 'renewal' and renews_plan is not None:
        own = [plan for plan in pool if plan.renews_id == renews_plan.id]
        if own:
            return own[0], 'renewal'
    key = ref_key(found)
    tiers = (
        ('read', lambda plan: (plan.read_ref or {}).get('key') == key),
        ('number', lambda plan: bool(codes.number_parts(found['plan_number']) & codes.number_parts(plan.plan_number))),
        ('codes', lambda plan: codes.overlap(found['codes'], _codes_of(plan))),
        ('name', lambda plan: norm(plan.name) == norm(found['name']) and norm(plan.carrier) == norm(found['carrier'])),
    )
    for how, test in tiers:
        hit = _one([plan for plan in pool if test(plan)])
        if hit is not None:
            return hit, how
    return None, ''
