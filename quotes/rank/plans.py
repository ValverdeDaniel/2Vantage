"""What Rank tells Claude about one line's quoted plans (plan.md §10.4; D96, F111, F114; the old pipeline/advisor.py
`_plan_summary`, `plan_summary_lines` and `SUMMARY_FIELD_KEYS_BY_SET` at 891f1b3).

One compact JSON object per quoted plan, in the board's order: its id, carrier, name, whether it is a renewal, the
values its line is chosen on (a dental plan on its annual maximum and orthodontia, not on a deductible it lacks) and
its monthly total from the Advisor's own figures (F114: the old context priced every plan with the medical count).
Lasers never leave the table (§3.8). The field lists are data (the old table, every key a 2V field).
"""

import json

from deals import lines

from .. import fields
from ..selectors.state import line_state

KEYS = {
    'medical': [
        'plan_type', 'network', 'deductible_single', 'deductible_family', 'oop_max_single', 'oop_max_family',
        'coinsurance', 'pcp_copay', 'specialist_copay', 'rx_t1', 'rx_t3', 'rate_ee', 'rate_es', 'rate_ec', 'rate_fam',
    ],
    'dental': [
        'plan_type', 'network', 'den_annual_max', 'den_deductible', 'den_preventive', 'den_basic', 'den_major',
        'den_ortho', 'den_ortho_max', 'den_waiting', 'rate_ee', 'rate_es', 'rate_ec', 'rate_fam',
    ],
    'vision': [
        'plan_type', 'network', 'vis_exam_copay', 'vis_materials_copay', 'vis_frame_allowance',
        'vis_contacts_allowance', 'vis_exam_frequency', 'vis_frame_frequency', 'rate_ee', 'rate_es', 'rate_ec',
        'rate_fam',
    ],
    'life': [
        'plan_type', 'life_schedule', 'life_benefit_max', 'life_guarantee_issue', 'life_add_included',
        'life_age_reduction', 'life_waiver_premium', 'unit_rate', 'group_premium_monthly',
    ],
    'disability': [
        'plan_type', 'dis_elimination', 'dis_benefit_pct', 'dis_max_benefit', 'dis_benefit_duration',
        'dis_own_occupation', 'dis_pre_existing', 'unit_rate', 'group_premium_monthly',
    ],
    'stop_loss': [
        'sl_spec_deductible', 'sl_spec_rate', 'sl_agg_rate', 'sl_other_load', 'sl_agg_factor', 'sl_agg_corridor',
        'sl_contract_basis', 'sl_run_in_months', 'sl_run_out_months', 'tpa_name', 'tpa_admin_fee',
        'group_premium_monthly',
    ],
    'generic': ['plan_type', 'network', 'benefit_summary', 'plan_notes', 'unit_rate', 'group_premium_monthly'],
}  # fmt: skip
NEVER = {'sl_lasers'}


def keys_for(line):
    have = set(fields.keys_for(line))
    wanted = KEYS.get(lines.BY_KEY[line]['field_set'], KEYS['generic'])
    return [key for key in wanted if key in have and key not in NEVER]


def _summary(plan, line, keys, monthly):
    out = {'id': plan.id, 'carrier': plan.carrier, 'plan': plan.name, 'line': lines.label(line)}
    if plan.role == 'renewal':
        out['renewal'] = True
    if plan.recommended:
        out['recommended'] = True
    held = plan.values or {}
    for key in keys:
        value = ' '.join(str(held.get(key) or '').split())
        if value:
            out[key] = value
    if monthly is not None:
        out['monthly_total'] = f'${monthly:,.0f}'
    return out


def plan_lines(deal, line, ids=None):
    """['{json}', …]: the quoted plans of `line` (only those in `ids` when given), in the board's order."""
    state = line_state(deal, line)
    keys = keys_for(line)
    out = []
    for plan in state.plans:
        if plan.role == 'current' or (ids is not None and plan.id not in ids):
            continue
        monthly = (state.results.get(plan.id) or {}).get('monthly')
        out.append(json.dumps(_summary(plan, line, keys, monthly), ensure_ascii=False))
    return out
