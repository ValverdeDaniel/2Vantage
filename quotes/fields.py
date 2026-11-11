"""Plan fields (plan.md §4.3).

Generated from plan.md §4.3 by script (§14); a data module, exempt from the 300-line rule.
`applies` names the lines a field belongs to; `client` says whether it may print on a client document.
"""

from deals import lines as line_vocab

GROUPS = [
    ('info', 'Plan info'),
    ('deduct', 'Deductibles & maximums'),
    ('copay', 'Copays & services'),
    ('rx', 'Prescription'),
    ('lf', 'Level-funded split'),
    ('rates', 'Monthly rates'),
    ('contrib', 'Employer contribution'),
    ('den_ben', 'Dental benefits'),
    ('vis_ben', 'Vision benefits'),
    ('life_ben', 'Life benefits'),
    ('dis_ben', 'Disability benefits'),
    ('gen_ben', 'Plan benefits'),
    ('sl_terms', 'Stop-loss terms'),
]

# key, label, group, type, required, applies
_ROWS = [
    ('network', 'Network', 'info', 'text', False, 'all'),
    ('plan_type', 'Plan Type', 'info', 'text', False, 'all'),
    ('plan_number', 'Plan Number', 'info', 'text', False, 'all'),
    ('funding', 'Funding', 'info', 'choice', True, 'medical'),
    ('metal_level', 'Metal Level', 'info', 'text', False, 'medical'),
    ('minimum_value', 'Meets Minimum Value (ACA)', 'info', 'yesno', False, 'medical'),
    ('part_d_creditable', 'Medicare Part D Creditable', 'info', 'yesno', False, 'medical'),
    ('sbc_url', 'Summary of Benefits (SBC) link', 'info', 'url', False, 'medical'),
    ('deductible_type', 'Deductible Type', 'deduct', 'text', False, 'medical'),
    ('deductible_single', 'Deductible (Single)', 'deduct', 'amount', True, 'medical'),
    ('deductible_family', 'Deductible (Family)', 'deduct', 'amount', False, 'medical'),
    ('deductible_single_oon', 'Deductible (Single) — OON', 'deduct', 'amount', False, 'medical'),
    ('deductible_family_oon', 'Deductible (Family) — OON', 'deduct', 'amount', False, 'medical'),
    ('oop_max_single', 'OOP Max (Single)', 'deduct', 'amount', True, 'medical'),
    ('oop_max_family', 'OOP Max (Family)', 'deduct', 'amount', False, 'medical'),
    ('oop_max_single_oon', 'OOP Max (Single) — OON', 'deduct', 'amount', False, 'medical'),
    ('oop_max_family_oon', 'OOP Max (Family) — OON', 'deduct', 'amount', False, 'medical'),
    ('coinsurance', 'Coinsurance (member share)', 'deduct', 'percent', False, 'medical'),
    ('coinsurance_oon', 'Coinsurance — OON', 'deduct', 'percent', False, 'medical'),
    ('pcp_copay', 'PCP Copay', 'copay', 'amount', True, 'medical'),
    ('specialist_copay', 'Specialist Copay', 'copay', 'amount', False, 'medical'),
    ('telehealth', 'Telehealth', 'copay', 'text', False, 'medical'),
    ('urgent_care_copay', 'Urgent Care Copay', 'copay', 'amount', False, 'medical'),
    ('er_copay', 'ER Copay', 'copay', 'amount', False, 'medical'),
    ('inpatient', 'Inpatient Hospital', 'copay', 'text', False, 'medical'),
    ('outpatient_surgery', 'Outpatient Surgery', 'copay', 'text', False, 'medical'),
    ('diagnostic_test', 'Diagnostic Tests (X-ray & Blood)', 'copay', 'text', False, 'medical'),
    ('advanced_imaging', 'Advanced Imaging (CT / MRI)', 'copay', 'text', False, 'medical'),
    ('mental_health_outpatient', 'Mental Health (Outpatient)', 'copay', 'text', False, 'medical'),
    ('rx_deductible', 'Rx Deductible', 'rx', 'amount', False, 'medical'),
    ('rx_t1', 'Rx Tier 1', 'rx', 'amount', False, 'medical'),
    ('rx_t2', 'Rx Tier 2', 'rx', 'amount', False, 'medical'),
    ('rx_t3', 'Rx Tier 3', 'rx', 'amount', False, 'medical'),
    ('rx_t4', 'Rx Tier 4 / Specialty', 'rx', 'amount', False, 'medical'),
    ('rx_mail_order', 'Rx Mail Order', 'rx', 'text', False, 'medical'),
    ('lf_claim_funding', 'Claim Funding / Aggregate (monthly)', 'lf', 'rate', False, 'medical'),
    ('lf_stop_loss_premium', 'Stop-Loss Premium (monthly)', 'lf', 'rate', False, 'medical'),
    ('lf_admin_fee', 'Admin Fee (monthly)', 'lf', 'rate', False, 'medical'),
    ('lf_tro', 'Terminal Reserve / TRO (monthly)', 'lf', 'rate', False, 'medical'),
    ('lf_surplus_share', 'Surplus Share', 'lf', 'text', False, 'medical'),
    ('rate_ee', 'Rate — EE', 'rates', 'rate', True, 'composite lines'),
    ('rate_es', 'Rate — EE + Spouse', 'rates', 'rate', True, 'composite lines'),
    ('rate_ec', 'Rate — EE + Child(ren)', 'rates', 'rate', True, 'composite lines'),
    ('rate_fam', 'Rate — Family', 'rates', 'rate', True, 'composite lines'),
    ('unit_rate', 'Unit Rate', 'rates', 'rate4', True, 'life, disability, PEPM lines'),
    ('group_premium_monthly', 'Group Premium / mo (quoted)', 'rates', 'rate', False, 'all'),
    ('contrib_ee', 'Employer Contrib — EE', 'contrib', 'rate', False, 'composite lines'),
    ('contrib_es', 'Employer Contrib — ES', 'contrib', 'rate', False, 'composite lines'),
    ('contrib_ec', 'Employer Contrib — EC', 'contrib', 'rate', False, 'composite lines'),
    ('contrib_fam', 'Employer Contrib — FAM', 'contrib', 'rate', False, 'composite lines'),
    ('den_annual_max', 'Annual Maximum', 'den_ben', 'amount', True, 'dental'),
    ('den_deductible', 'Deductible (Individual)', 'den_ben', 'amount', True, 'dental'),
    ('den_deductible_family', 'Deductible (Family)', 'den_ben', 'amount', False, 'dental'),
    ('den_preventive', 'Preventive & Diagnostic', 'den_ben', 'percent', True, 'dental'),
    ('den_basic', 'Basic Services', 'den_ben', 'percent', False, 'dental'),
    ('den_major', 'Major Services', 'den_ben', 'percent', False, 'dental'),
    ('den_ortho', 'Orthodontia', 'den_ben', 'percent', False, 'dental'),
    ('den_ortho_max', 'Ortho Lifetime Max', 'den_ben', 'amount', False, 'dental'),
    ('den_waiting', 'Waiting Periods', 'den_ben', 'text', False, 'dental'),
    ('vis_exam_copay', 'Exam Copay', 'vis_ben', 'amount', True, 'vision'),
    ('vis_materials_copay', 'Materials Copay', 'vis_ben', 'amount', False, 'vision'),
    ('vis_frame_allowance', 'Frame Allowance', 'vis_ben', 'amount', True, 'vision'),
    ('vis_contacts_allowance', 'Contacts Allowance', 'vis_ben', 'amount', False, 'vision'),
    ('vis_exam_frequency', 'Exam Frequency', 'vis_ben', 'text', False, 'vision'),
    ('vis_frame_frequency', 'Frame Frequency', 'vis_ben', 'text', False, 'vision'),
    ('life_schedule', 'Benefit Schedule', 'life_ben', 'text', True, 'life lines'),
    ('life_benefit_max', 'Benefit Maximum', 'life_ben', 'amount', False, 'life lines'),
    ('life_guarantee_issue', 'Guarantee Issue', 'life_ben', 'amount', False, 'life lines'),
    ('life_add_included', 'AD&D Included', 'life_ben', 'yesno', False, 'life lines'),
    ('life_age_reduction', 'Age Reduction Schedule', 'life_ben', 'text', False, 'life lines'),
    ('life_waiver_premium', 'Waiver of Premium', 'life_ben', 'yesno', False, 'life lines'),
    ('dis_elimination', 'Elimination Period', 'dis_ben', 'text', True, 'disability lines'),
    ('dis_benefit_pct', 'Benefit Percentage', 'dis_ben', 'percent', True, 'disability lines'),
    ('dis_max_benefit', 'Maximum Benefit', 'dis_ben', 'amount', True, 'disability lines'),
    ('dis_benefit_duration', 'Benefit Duration', 'dis_ben', 'text', False, 'disability lines'),
    ('dis_own_occupation', 'Own-Occupation Period', 'dis_ben', 'text', False, 'disability lines'),
    ('dis_pre_existing', 'Pre-Existing Limitation', 'dis_ben', 'text', False, 'disability lines'),
    ('benefit_summary', 'Benefit Summary', 'gen_ben', 'text', True, 'generic lines'),
    ('plan_notes', 'Notes', 'gen_ben', 'text', False, 'generic lines'),
    ('sl_spec_deductible', 'Specific Deductible (per person)', 'sl_terms', 'rate', False, 'stop_loss'),
    ('sl_spec_rate', 'Specific Premium PEPM', 'sl_terms', 'rate', False, 'stop_loss'),
    ('sl_agg_rate', 'Aggregate Premium PEPM', 'sl_terms', 'rate', False, 'stop_loss'),
    ('sl_other_load', 'TLO / Other SL Load PEPM', 'sl_terms', 'rate', False, 'stop_loss'),
    ('sl_agg_factor', 'Expected Claims Factor PEPM', 'sl_terms', 'rate', False, 'stop_loss'),
    ('sl_agg_corridor', 'Aggregate Corridor', 'sl_terms', 'number', False, 'stop_loss'),
    ('sl_agg_floor', 'Min Annual Aggregate Deductible', 'sl_terms', 'rate', False, 'stop_loss'),
    ('sl_contract_basis', 'Contract Basis (incurred/paid)', 'sl_terms', 'text', False, 'stop_loss'),
    ('sl_run_in_months', 'Run-In Period (months)', 'sl_terms', 'number', False, 'stop_loss'),
    ('sl_run_in_limit', 'Run-In Dollar Limit', 'sl_terms', 'amount', False, 'stop_loss'),
    ('sl_run_out_months', 'Run-Out / Paid Window (months)', 'sl_terms', 'number', False, 'stop_loss'),
    ('sl_tlo', 'TLO Included / Terms', 'sl_terms', 'text', False, 'stop_loss'),
    ('sl_lasers', 'Lasers (ID amount, ID amount)', 'sl_terms', 'text', False, 'stop_loss'),
    ('sl_collateral', 'Collateral / Captive Fees (annual)', 'sl_terms', 'amount', False, 'stop_loss'),
    ('tpa_name', 'TPA', 'sl_terms', 'text', False, 'stop_loss'),
    ('tpa_admin_fee', 'Admin / TPA / Network PEPM', 'sl_terms', 'rate', False, 'stop_loss'),
    ('tpa_rate_guarantee', 'TPA Rate Guarantee', 'sl_terms', 'text', False, 'stop_loss'),
]

# Never printed on a client document (§4.3). `sl_lasers` is claimant data; the team removed outpatient
# mental health on 2026-11-05.
NOT_FOR_CLIENTS = {'sl_lasers', 'mental_health_outpatient'}

CHOICES = {'funding': line_vocab.FUNDING}

FIELDS = [
    {
        'key': key,
        'label': label,
        'group': group,
        'type': type_,
        'required': required,
        'applies': applies,
        'client': key not in NOT_FOR_CLIENTS,
        'choices': [{'key': k, 'label': v} for k, v in CHOICES.get(key, [])],
    }
    for key, label, group, type_, required, applies in _ROWS
]
BY_KEY = {field['key']: field for field in FIELDS}
TIER_RATE_KEYS = ['rate_ee', 'rate_es', 'rate_ec', 'rate_fam']
CONTRIB_KEYS = ['contrib_ee', 'contrib_es', 'contrib_ec', 'contrib_fam']
# Groups a renewal and a copied alternate do not inherit (§5.4).
PRICE_GROUPS = {'rates', 'contrib', 'lf'}

# Which groups each field set shows, in display order (§4.3).
FIELD_SET_GROUPS = {
    'medical': ['info', 'deduct', 'copay', 'rx', 'lf', 'rates', 'contrib'],
    'dental': ['info', 'den_ben', 'rates', 'contrib'],
    'vision': ['info', 'vis_ben', 'rates', 'contrib'],
    'life': ['info', 'life_ben', 'rates'],
    'disability': ['info', 'dis_ben', 'rates'],
    'generic': ['info', 'gen_ben', 'rates', 'contrib'],
    'stop_loss': ['info', 'sl_terms', 'rates'],
}


def _applies(field, line):
    applies = field['applies']
    if applies == 'all':
        return True
    if applies == 'composite lines':
        return line['rate_basis'] == 'composite'
    if applies == 'life, disability, PEPM lines':
        return line['field_set'] in ('life', 'disability') or line['rate_basis'] == 'pepm'
    if applies.endswith(' lines'):
        return line['field_set'] == applies[: -len(' lines')]
    return line['key'] == applies


# Kept as columns on Plan (§6.6), not as values: listed for its label only.
COLUMN_FIELDS = {'plan_number'}


def groups_for(line_key):
    """[(group key, group label, [field keys])] for a line, empty groups dropped."""
    line = line_vocab.get(line_key)
    if not line:
        return []
    labels = dict(GROUPS)
    result = []
    for group in FIELD_SET_GROUPS[line['field_set']]:
        keys = [f['key'] for f in FIELDS if f['group'] == group and f['key'] not in COLUMN_FIELDS and _applies(f, line)]
        if keys:
            result.append((group, labels[group], keys))
    return result


def keys_for(line_key):
    return [key for _, _, keys in groups_for(line_key) for key in keys]


def meta():
    return {
        'groups': [{'key': key, 'label': label} for key, label in GROUPS],
        'fields': FIELDS,
        'line_groups': {
            line['key']: [{'key': g, 'label': lbl, 'fields': keys} for g, lbl, keys in groups_for(line['key'])]
            for line in line_vocab.LINES
        },
    }
