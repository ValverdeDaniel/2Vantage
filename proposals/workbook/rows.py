"""The house row maps: which design rows each line's tabs show, in order (plan.md §9.4; old `presentation_model` at
891f1b3, phases 4, 10c, 10d). A data module.

A Row is (label, field keys, flag); a None label is the field's own. The flag is 'pair' (the keys print as one text,
"single / family"), 'indent' (a label indented two levels) or 'inout' (in and out of network in one box). A Band is a
heading that shows only when one of its rows does. A row's id is its first key. The rates tab keeps MEDICAL_ROWS and
its own out-of-network band; the Compare, Composite Rates and All Plans tabs print Bryke's COMPARE_MEDICAL_ROWS.
The team's settled points (minimum value and Part D rows; no mental health row) hold: `mental_health_outpatient` is
not a client field (quotes.fields), so it never shows.
"""

from collections import namedtuple

from quotes import fields

Row = namedtuple('Row', 'label keys flag')
Band = namedtuple('Band', 'id label rows')

LEVEL_FUNDED = Band(
    'lf',
    'Level-Funded Detail',
    (
        Row(None, ('lf_claim_funding',), ''),
        Row(None, ('lf_stop_loss_premium',), ''),
        Row(None, ('lf_admin_fee',), ''),
        Row(None, ('lf_tro',), ''),
        Row(None, ('lf_surplus_share',), ''),
    ),
)

MEDICAL_ROWS = (
    Row('Network', ('network',), ''),
    Row('Plan Type', ('plan_type',), ''),
    Row('Metal Level', ('metal_level',), ''),
    Row('Deductible Type', ('deductible_type',), ''),
    Row('Individual/Family Deductible', ('deductible_single', 'deductible_family'), 'pair'),
    Row('Coinsurance', ('coinsurance',), ''),
    Row('Out-of-Pocket Maximum', ('oop_max_single', 'oop_max_family'), 'pair'),
    Row('Doctor Visits (PCP)', ('pcp_copay',), ''),
    Row('Specialty Visits', ('specialist_copay',), ''),
    Row('Telehealth', ('telehealth',), ''),
    Row('Mental Health (Outpatient)', ('mental_health_outpatient',), ''),
    Row('Diagnostic Tests (X-ray & Blood)', ('diagnostic_test',), ''),
    Row('Advanced Imaging (CT / MRI)', ('advanced_imaging',), ''),
    Row('Pharmacy Deductible', ('rx_deductible',), ''),
    Row('Tier 1: Generic', ('rx_t1',), 'indent'),
    Row('Tier 2: Preferred', ('rx_t2',), 'indent'),
    Row('Tier 3: Non-preferred', ('rx_t3',), 'indent'),
    Row('Tier 4: Specialty', ('rx_t4',), 'indent'),
    Row('Mail Order', ('rx_mail_order',), 'indent'),
    Row('Urgent Care', ('urgent_care_copay',), ''),
    Row('Emergency Room', ('er_copay',), ''),
    Row('Inpatient Hospital', ('inpatient',), ''),
    Row('Outpatient Surgery', ('outpatient_surgery',), ''),
    Band(
        'oon',
        'Out-of-Network Benefits',
        (
            Row('Individual/Family Deductible', ('deductible_single_oon', 'deductible_family_oon'), 'pair'),
            Row('Coinsurance', ('coinsurance_oon',), ''),
            Row('Out-of-Pocket Maximum', ('oop_max_single_oon', 'oop_max_family_oon'), 'pair'),
        ),
    ),
    LEVEL_FUNDED,
    Band('compliance', 'Compliance', (Row(None, ('minimum_value',), ''), Row(None, ('part_d_creditable',), ''))),
)

DENTAL_ROWS = (
    Row('Network', ('network',), ''),
    Row('Individual/Family Deductible', ('den_deductible', 'den_deductible_family'), 'pair'),
    Row('Annual Maximum', ('den_annual_max',), ''),
    Row('Preventive Services', ('den_preventive',), ''),
    Row('Basic Services', ('den_basic',), ''),
    Row('Major Services', ('den_major',), ''),
    Row('Orthodontia', ('den_ortho', 'den_ortho_max'), 'pair'),
    Row('Waiting Periods', ('den_waiting',), ''),
)

VISION_ROWS = (
    Row('Network', ('network',), ''),
    Row('Frequency (Exam / Frame)', ('vis_exam_frequency', 'vis_frame_frequency'), 'pair'),
    Row('Exam', ('vis_exam_copay',), ''),
    Row('Lenses (materials)', ('vis_materials_copay',), ''),
    Row('Frame Allowance', ('vis_frame_allowance',), ''),
    Row('Contacts (Elective)', ('vis_contacts_allowance',), ''),
)

# Accident, hospital, critical illness, gap and voluntary worksite share one.
WORKSITE_ROWS = (
    Row('Benefit Summary', ('benefit_summary',), ''),
    Row('Notes', ('plan_notes',), ''),
)

OTHER_BAND = 'Other Plan Details'

# Bryke's rows for a medical line on the Compare, Composite Rates and All Plans tabs: in and out of network in one
# box, the OOP max beside the deductible, diagnostic tests above imaging.
COMPARE_MEDICAL_ROWS = (
    Row('Plan Type', ('plan_type',), ''),
    Row('Network', ('network',), ''),
    Row('Metal Tier', ('metal_level',), ''),
    Row('Deductible Type', ('deductible_type',), ''),
    Row('Ind. Deductible (In/Out)', ('deductible_single', 'deductible_single_oon'), 'inout'),
    Row('Fam. Deductible (In/Out)', ('deductible_family', 'deductible_family_oon'), 'inout'),
    Row('Coinsurance — member pays (In/Out)', ('coinsurance', 'coinsurance_oon'), 'inout'),
    Row('Ind. OOP Max (In/Out)', ('oop_max_single', 'oop_max_single_oon'), 'inout'),
    Row('Fam. OOP Max (In/Out)', ('oop_max_family', 'oop_max_family_oon'), 'inout'),
    Row('PCP Copay', ('pcp_copay',), ''),
    Row('Specialist Copay', ('specialist_copay',), ''),
    Row('Telehealth', ('telehealth',), ''),
    Row('Mental Health (Outpatient)', ('mental_health_outpatient',), ''),
    Row('Diagnostic Tests (X-ray & Blood)', ('diagnostic_test',), ''),
    Row('Advanced Imaging (CT / MRI)', ('advanced_imaging',), ''),
    Row('Rx Deductible', ('rx_deductible',), ''),
    Row('Rx Drug Card (T1 / T2 / T3)', ('rx_t1', 'rx_t2', 'rx_t3'), 'pair'),
    Row('Specialty Rx', ('rx_t4',), ''),
    Row('Mail Order', ('rx_mail_order',), ''),
    Row('Urgent Care', ('urgent_care_copay',), ''),
    Row('Emergency Room', ('er_copay',), ''),
    Row('Inpatient Hospital', ('inpatient',), ''),
    Row('Outpatient Surgery', ('outpatient_surgery',), ''),
    Row('Minimum Value / Part D', ('minimum_value', 'part_d_creditable'), 'pair'),
    LEVEL_FUNDED,
)

# Never design rows: the rates and contributions have their own block, the group premium is the stated row, the plan
# number joins the Plan row, and the SBC link is a link (never URL text).
NEVER_DESIGN = frozenset(
    [*fields.TIER_RATE_KEYS, *fields.CONTRIB_KEYS, 'unit_rate', 'group_premium_monthly', 'plan_number', 'sbc_url']
)


def house_rows(field_set):
    """The design map for a line's field set; anything not medical, dental or vision uses the worksite map."""
    return {'medical': MEDICAL_ROWS, 'dental': DENTAL_ROWS, 'vision': VISION_ROWS}.get(field_set, WORKSITE_ROWS)


def flat(house):
    for entry in house:
        if isinstance(entry, Band):
            yield from entry.rows
        else:
            yield entry
