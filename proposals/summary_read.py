"""The facts the builder's deal cards read: the executive summary's, Markets checked's and the page ledger's (plan.md
§8.14; J42, J63–J66). From what the builder has already worked out (quotes' `deal_state`, each line's layout, the
intent), plus two light reads: the census's 65+ count and who the RFP asked.

Only client-safe facts enter: each plan's words ("Carrier · Name", its client name first; J14), its figures from
quotes' results and the few design values the summary compares (never `sl_lasers`, notes or sources). The census's
birth dates are read to count ages and never leave this module (§5.3.7; J66).
"""

from census import fields as census_fields
from census import rollup
from census.models import Member
from deals import lines
from quotes import math as m
from quotes.math import enrollment as counts

# The plan values the summary's design blocks compare (summary_blocks.design).
VALUE_KEYS = (
    'rate_ee',
    'unit_rate',
    'deductible_single',
    'oop_max_single',
    'den_deductible',
    'den_annual_max',
    'vis_exam_copay',
    'vis_frame_allowance',
    'sl_spec_deductible',
)
MEDICAL = 'medical'


def words(row):
    """How the summary names a plan: "Guardian · Dental PPO 1500", its client name first (old `_plan_name`, D-175)."""
    return ' · '.join(part for part in (row.carrier, row.client_name or row.name) if part) or f'Plan {row.id}'


def _plan(plan, state, rows):
    result = state.results[plan.id]
    return {
        'id': plan.id,
        'words': words(rows[plan.id]),
        'carrier': plan.carrier,
        'name': rows[plan.id].client_name or plan.name,
        'monthly': result['monthly'],
        'annual': result['annual'],
        'change': result['change'],
        'bases': list(result['base_ids']),
        'credit': result.get('credit'),
        'values': {key: plan.values.get(key) for key in VALUE_KEYS if plan.values.get(key) not in (None, '')},
    }


def line_facts(line, state, laid, intent_state, intent_row):
    """One line as the summary reads it (`summary_blocks.reading`)."""
    data, rows = state.data, laid.rows
    shown = laid.shown
    sold = [p for p in data.plans if p.sold]
    picks = sold or [p for p in shown if p.recommended]
    found = m.people(data, state.results)
    current_package = next((pk for pk in state.packages if pk['key'] == 'current'), None)
    return {
        'key': line,
        'label': lines.label(line),
        'state': intent_state or 'shopped',
        'shopping': bool((intent_row or {}).get('shopping')) if intent_row else intent_state != 'presented',
        'field_set': lines.BY_KEY[line]['field_set'],
        'composite': data.rate_basis == 'composite',
        'no_people': any(state.results[p.id]['reason'] == 'no_enrollment' for p in shown),
        'people': {'figures': counts.as_plain(found[0]), 'source': found[1]} if found else None,
        'currents': [_plan(p, state, rows) for p in data.current],
        'options': [_plan(p, state, rows) for p in shown if p.role != 'current'],
        'quotes': [_plan(p, state, rows) for p in data.plans if p.role != 'current'],
        'picks': [_plan(p, state, rows) for p in picks],
        'current_package': current_package
        and {
            'monthly': current_package['monthly'],
            'annual': current_package['annual'],
        },
    }


def market_line(line, state, laid, intent_row):
    """One line as Markets checked reads it: its plans in the proposal's order (the ones shown first, as the pages
    read them, then the rest), and the coverage row's carrier for a line with no current plan."""
    data, rows = state.data, laid.rows
    shown_ids = [p.id for p in laid.shown]
    ordered = [data.by_id[pid] for pid in shown_ids] + [p for p in data.plans if p.id not in set(shown_ids)]
    return {
        'key': line,
        'label': lines.label(line),
        'plans': [
            {
                'carrier': p.carrier,
                'name': rows[p.id].client_name or p.name,
                'current': p.role == 'current',
                'shown': p.id in set(shown_ids),
            }
            for p in ordered
        ],
        'incumbent': (intent_row or {}).get('carrier') or '',
        'renewal_note': '',  # "Renewal came in +8%" once the renewal letter's figures are stored (J65)
    }


def negotiated(state, laid):
    """Whether the line shows a carrier's first offer worked down: a priced version of a quote (the "What we
    negotiated" page's facts)."""
    data = state.data
    return any(data.root(p).id != p.id and data.root(p).role != 'current' for p in laid.shown)


def ages(deal):
    """{rows, with_dob, employees_65, dependents_65, as_of}: the census's ages at the effective date, as counts only
    (one query; J66). None without a census."""
    found = list(Member.objects.filter(deal_id=deal.id).values_list('kind', 'values__dob'))
    if not found:
        return None
    as_of = deal.effective_date
    with_dob = [(kind, dob) for kind, dob in found if dob]
    over = [kind for kind, dob in with_dob if (rollup.age_at(dob, as_of) or 0) >= rollup.MEDICARE_AGE] if as_of else []
    return {
        'rows': len(found),
        'with_dob': len(with_dob),
        'employees_65': sum(1 for kind in over if kind == census_fields.EMPLOYEE),
        'dependents_65': sum(1 for kind in over if kind != census_fields.EMPLOYEE),
        'as_of': as_of.strftime('%m/%d/%Y') if as_of else '',
    }


def renewal_offer(_deal):
    """The renewal letter's four facts (renewal_pct_change, renewal_premium_annual, stated_current_premium_annual,
    group_number), or None. plan.md §6.5 asks them of intake's CurrentCoverage (J65, ch28), where no slice has stored
    them yet, so every deal reads None and the renewal blocks refuse with their reason until they are."""
    return None
