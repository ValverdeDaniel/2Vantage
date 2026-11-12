"""Standard Stop Loss Disclosure Form — SIIA endorsed, October 2015 (G1). A data module, exempt from the 300-line rule.

The universal stop-loss disclosure every stop-loss carrier accepts, a producer's opt-in on the checklist's stop-loss
row (OQ58 default) and used beside the medical form for level- and self-funded groups. Ported from old Vantage
891f1b3 (`benefits/questionnaires/stop_loss_siia.py`); its AcroForm field map is the export's, slice 43's (G59).

The claimant rows are this year's people (`sensitive`, the whole block; G23): never in Activity values, logs or URLs.
"""

# A data module: its hand-laid tables stay as written.
# fmt: off

SEXES = ['M', 'F']
RELATIONSHIPS = ['EE', 'Sp', 'Ch']
# The paper column takes one letter; the readable word is stored and the export prints the letter (slice 43).
COVERAGE_STATUSES = ['Active', 'COBRA', 'Retiree', 'Termed']
COVERAGE_STATUS_LETTERS = {'Active': 'A', 'COBRA': 'C', 'Retiree': 'R', 'Termed': 'T'}

# Verbatim from the form's own printed pages — do not paraphrase.
DISCLOSURE_CRITERIA = (
    'List on the Disclosure Form all risks known to: '
    '1. Be currently disabled, confined to a Medical Facility, or have been precertified within the last three months. '
    '2. Have received medical services during the current plan year the cost of which exceeds the lesser of, 50% of '
    'the lowest Specific Retention Amount applied for or $50,000, and for which bills have been received by the Claims '
    'Administrator and entered into their Claims System. '
    '3. Have been identified as a candidate for Case Management and as having the potential to exceed during the '
    'policy period, the lesser of, 50% of the lowest Specific Retention Amount applied for, or $50,000. '
    '4. Have been diagnosed, during the current plan year, with a condition represented by any of the ICD-10 codes '
    'contained in the attached list [and have also received medical services costing $5,000 during the same period].'
)

SPONSOR_ATTESTATION = (
    'The Plan Sponsor named below represents that the above list accurately discloses all potentially catastrophic '
    'risks in accordance with the instructions attached to this form and that it is the result of a diligent search in '
    'accordance with those instructions.'
)

SECTION_RISKS = {
    'key': 'risks', 'number': '', 'label': 'Disclosure of Known Risks',
    'intro': DISCLOSURE_CRITERIA,
    'fields': [
        {'key': 'no_risks', 'type': 'yesno', 'width': 3, 'sensitive': True,
         'label': 'If there are no risks to report which meet the disclosure criteria above, please check this box.',
         'hint': 'Yes = the box is checked: there is no one to disclose.'},
    ],
    'blocks': ['risks'],
}

BLOCK_RISKS = {
    'key': 'risks', 'label': 'Known risks', 'row_label': 'Risk', 'add_label': 'Add Individual',
    'empty_label': 'No risks reported.', 'min_rows': 1, 'max_rows': 10, 'sensitive': True,
    # The grid applies until "no risks" is actually checked: `ne`, not eq-'No'.
    'visible_if': {'field': 'no_risks', 'op': 'ne', 'value': 'Yes'},
    'fields': [
        {'key': 'risk_identifier', 'label': 'Risk Identifier', 'type': 'text', 'required': True,
         'deidentified': True, 'hint': 'De-identified — initials or member ID, never a full name.'},
        {'key': 'dob', 'label': 'DOB', 'type': 'date'},
        {'key': 'sex', 'label': 'Sex', 'type': 'choice', 'options': SEXES},
        {'key': 'relationship', 'label': 'EE, Sp or Ch', 'type': 'choice', 'options': RELATIONSHIPS},
        {'key': 'coverage_status', 'label': 'Active, COBRA, Retiree, or Termed', 'type': 'choice',
         'options': COVERAGE_STATUSES, 'display_map': COVERAGE_STATUS_LETTERS},
        {'key': 'term_date', 'label': 'Term Date', 'type': 'date'},
        {'key': 'diagnosis', 'label': 'Diagnosis', 'type': 'text', 'required': True, 'width': 2,
         'hint': 'The condition / ICD-10 category — see the reference list on the attached pages of the form.'},
        {'key': 'last_service_date', 'label': 'Most Recent Date of Service', 'type': 'date'},
        {'key': 'expenses_incurred', 'label': 'Expenses Incurred This Plan Year', 'type': 'money'},
    ],
}

SECTION_SIGNATURES = {
    'key': 'signatures', 'number': '', 'label': 'Signatures',
    'intro': SPONSOR_ATTESTATION,
    'fields': [
        {'key': 'plan_sponsor', 'label': 'Plan Sponsor', 'type': 'text', 'required': True, 'width': 2,
         'prefill': 'legal_name'},
        {'key': 'sponsor_name', 'label': 'Name — Plan Sponsor', 'type': 'text', 'required': True,
         'prefill': 'officer_name'},
        {'key': 'sponsor_title', 'label': 'Title — Plan Sponsor', 'type': 'text', 'prefill': 'officer_title'},
        # No prefill for the claims administrator: a wrong guess on a disclosure is worse than a blank.
        {'key': 'claims_admin', 'label': 'Claims Administrator', 'type': 'text', 'width': 2},
        {'key': 'admin_name', 'label': 'Name — Claims Administrator', 'type': 'text'},
        {'key': 'admin_title', 'label': 'Title — Claims Administrator', 'type': 'text'},
        {'key': 'broker_entity', 'label': 'Agent/Broker', 'type': 'text', 'width': 2, 'prefill': 'agency_name',
         'broker': True},
        {'key': 'broker_name', 'label': 'Name — Agent/Broker', 'type': 'text', 'prefill': 'agent_name',
         'broker': True},
        {'key': 'broker_title', 'label': 'Title — Agent/Broker', 'type': 'text', 'broker': True},
    ],
}

FORM = {
    'key': 'stop_loss_siia',
    'version': 'oct2015',
    'kind': 'stop_loss',
    'carrier': 'SIIA (all stop-loss carriers)',
    'short_label': 'Stop Loss Disclosure (SIIA)',
    'export_slug': 'stop-loss-disclosure',
    'title': 'Standard Stop Loss Disclosure Form',
    'subtitle': 'Self-Insurance Institute of America, Inc. (SIIA) Endorsed — October 2015',
    'officer_label': 'Plan sponsor — authorized company officer',
    'sections': [SECTION_RISKS, SECTION_SIGNATURES],
    'blocks': {'risks': BLOCK_RISKS},
    'tables': {},
    'blank_pdf': 'stop_loss_siia.pdf',
}
