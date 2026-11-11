"""Reads for the Advisor (plan.md §7.7). Builds plain data for the pure math and returns payloads."""

from deals import lines

from . import fields
from . import math as m
from . import packages as pk
from .models import Package, Plan

ROLE_ORDER = {'current': 0, 'renewal': 1, 'alternate': 2}


def ordered_plans(deal, line):
    plans = list(Plan.objects.filter(deal=deal, line=line).prefetch_related('replaces'))
    return sorted(plans, key=lambda p: (ROLE_ORDER[p.role], p.sort_order, p.id))


def plan_data(plan):
    return m.PlanData(
        id=plan.id,
        role=plan.role,
        carrier=plan.carrier,
        name=plan.name,
        values=plan.values,
        enrollment=plan.enrollment,
        enrollment_on=plan.enrollment_on,
        renews=plan.renews_id,
        replaces=tuple(p.id for p in plan.replaces.all()),
        recommended=plan.recommended,
        sold=plan.sold,
    )


def member_packages(deal, line):
    return [
        (p.id, p.name, [plan.id for plan in p.plans.all()])
        for p in Package.objects.filter(deal=deal, line=line).prefetch_related('plans')
    ]


def line_state(deal, line):
    """Everything computed about one line: (plans, LineData, results, packages, recommendation)."""
    plans = ordered_plans(deal, line)
    data = m.LineData(rate_basis=lines.BY_KEY[line]['rate_basis'], plans=[plan_data(p) for p in plans])
    results = pk.evaluate(data)
    members = member_packages(deal, line)
    return plans, data, results, pk.line_packages(data, results, members), pk.recommendation(data, results, members)


def statuses(plan):
    """missing / blank / to_check per field (§3.7, §5.4); 'ok' keys are left out."""
    status = {}
    values = plan.values
    quoted_only = values.get('group_premium_monthly') and not any(values.get(k) for k in fields.TIER_RATE_KEYS)
    for key in fields.keys_for(plan.line):
        field = fields.BY_KEY[key]
        if values.get(key) in (None, ''):
            exempt = quoted_only and key in fields.TIER_RATE_KEYS
            status[key] = 'missing' if field['required'] and not exempt else 'blank'
        elif plan.sources.get(key, {}).get('origin') == 'ai' and not plan.sources[key].get('confirmed_by'):
            status[key] = 'to_check'
    return status


def plan_payload(plan, result=None, data=None):
    payload = {
        'id': plan.id,
        'line': plan.line,
        'role': plan.role,
        'carrier': plan.carrier,
        'name': plan.name,
        'plan_number': plan.plan_number,
        'renews_id': plan.renews_id,
        'replaces_ids': [p.id for p in plan.replaces.all()],
        'option_label': plan.option_label,
        'starred': plan.starred,
        'recommended': plan.recommended,
        'sold': plan.sold,
        'sort_order': plan.sort_order,
        'notes': plan.notes,
        'values': plan.values,
        'sources': plan.sources,
        'status': statuses(plan),
        'enrollment': plan.enrollment,
        'enrollment_on': plan.enrollment_on,
    }
    if result is not None:
        payload.update(
            {
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
                'employee_cost': m.employee_cost(data.by_id[plan.id]),
                'tier_rate_change': (
                    m.tier_rate_change(data.by_id[plan.id], data.by_id[plan.renews_id])
                    if plan.role == 'renewal' and plan.renews_id in data.by_id and data.rate_basis == 'composite'
                    else None
                ),
            }
        )
    return payload


def comparison(deal, line):
    plans, data, results, packages, recommendation = line_state(deal, line)
    warnings = []
    if any(results[p.id]['reason'] == 'per_plan_counts_needed' for p in plans):
        warnings.append({'code': 'per_plan_counts_needed', 'message': 'Enter enrollment for each current plan'})
    return {
        'line': line,
        'rate_basis': data.rate_basis,
        'groups': [{'key': g, 'label': label, 'fields': keys} for g, label, keys in fields.groups_for(line)],
        'plans': [plan_payload(p, results[p.id], data) for p in plans],
        'packages': packages,
        'member_packages': [
            {'id': pid, 'name': name, 'plan_ids': ids} for pid, name, ids in member_packages(deal, line)
        ],
        'recommendation': recommendation,
        'warnings': warnings,
    }


def lines_summary(deal):
    keys = list(deal.requested_lines)
    for line in Plan.objects.filter(deal=deal).values_list('line', flat=True).distinct():
        if line not in keys:
            keys.append(line)
    keys.sort(key=lambda k: lines.LINE_KEYS.index(k) if k in lines.LINE_KEYS else 999)
    rows = []
    for key in keys:
        plans = Plan.objects.filter(deal=deal, line=key)
        counts = {role: plans.filter(role=role).count() for role in ROLE_ORDER}
        _, _, _, _, recommendation = line_state(deal, key) if plans.exists() else (None,) * 4 + ({'covered': False},)
        rows.append(
            {
                'line': key,
                'label': lines.label(key),
                'requested': key in deal.requested_lines,
                **counts,
                'starred': plans.filter(starred=True).count(),
                'recommended': plans.filter(recommended=True).count(),
                'recommendation_covered': recommendation['covered'],
                'sold_plans': [f'{p.carrier} {p.name}' for p in plans.filter(sold=True)],
            }
        )
    return rows
