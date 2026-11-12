"""The Advisor's comparison of one line (plan.md §7.8, F.6): `GET deals/{id}/plans/?line=`.

The plans come in `order.layout`'s order (F120), each priced by the server with its comparison base, its source of
enrollment, its change or the plan whose people it shares (`part_of`), its facts (F122) and its closeness to the
nearest current plan (F121); cells carry compact flags and the documents are listed once (C23). A fixed number of
queries at any size (Q.3 #4); 600 plans stay within 3 MB and 2.5 s (Q.7).
"""

from deals import lines

from .. import closeness, facts, fields, presented
from .. import math as m
from .plans import Documents, base, cells
from .state import line_state


def _priced(plan, result, data):
    renewal_of = data.by_id.get(plan.renews_id) if plan.role == 'renewal' else None
    return {
        'base_ids': result['base_ids'],
        'enrollment_used': result['enrollment_used'],
        'enrollment_source': result['enrollment_source'],
        'premium': {
            'monthly': result['monthly'],
            'annual': result['annual'],
            'reason': result['reason'],
            'quoted': result['quoted'],
            'reason_words': m.REASON_WORDS.get(result['reason']) if result['reason'] else None,
        },
        'change': result['change'],
        'part_of': result['part_of'],
        'employee_cost': m.employee_cost(data.by_id[plan.id]) if data.rate_basis == 'composite' else None,
        'tier_rate_change': (
            m.tier_rate_change(data.by_id[plan.id], renewal_of)
            if renewal_of is not None and data.rate_basis == 'composite'
            else None
        ),
    }


def comparison(deal, line):
    plans, data, results, packages, recommendation = line_state(deal, line, sources=True)
    field_set = lines.BY_KEY[line]['field_set']
    on = {plan.id for plan in presented.presented(data)}
    documents = Documents()
    rows = []
    for plan in plans:
        status = facts.statuses(line, plan.values, plan.sources)
        result = results[plan.id]
        rows.append(
            {
                **base(plan),
                'cells': cells(plan, status, documents),
                **_priced(plan, result, data),
                'presented': plan.id in on,
                'facts': facts.plan_facts(line, plan.values, status, result['monthly']),
                'closeness': closeness.closest(data.by_id[plan.id], data.current, field_set),
            }
        )
    warnings = []
    if any(result['reason'] == 'per_plan_counts_needed' for result in results.values()):
        warnings.append({'code': 'per_plan_counts_needed', 'message': 'Enter enrollment for each current plan'})
    return {
        'line': line,
        'rate_basis': data.rate_basis,
        'groups': [{'key': g, 'label': label, 'fields': keys} for g, label, keys in fields.groups_for(line)],
        'plans': rows,
        'documents': documents.listed(),
        'room': presented.room(data),
        'packages': packages,
        'member_packages': [
            {'id': int(p['key'].removeprefix('package:')), 'name': p['label'], 'plan_ids': p['plan_ids']}
            for p in packages
            if p['key'].startswith('package:')
        ],
        'recommendation': recommendation,
        'warnings': warnings,
    }
