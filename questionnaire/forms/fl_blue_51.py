"""Florida Blue Underwriting Questionnaire — Supplement to Group Application, For Large Groups (51 or more employees)
(G1). A data module, exempt from the 300-line rule.

The presentation spec: sections, field order, labels and legal copy, ported from old Vantage 891f1b3
(`benefits/questionnaires/fl_blue_51.py`). The option tables and the dependent pickers' data are extracted carrier data
in the generated `fl_blue_51_data.py` (G124).

Field keys are the carrier's own XFA names (`txtCoName`, `numTAP`, `drpMedCat`, …): never rename one, every stored
answer keys on it. Three naming notes from the source form: `TextField2` is the Tax Id; the SIC description is a
second `drpSIC` in the template, disambiguated as `drpSICDesc`; each Yes/No checkbox pair collapses to one `yesno`
field (`chkFBPrior`, `chkVirgin`, `chkMedCon`).

The words are the house vocabulary (§4.5): types `text`, `date`, `number`, `money`, `percent`, `choice`, `yesno`.
Flags (G.6): `sensitive` (medical history: never in Activity values, logs or URLs; G23), `broker` (the agent's own
fields, which a client never writes; G86), `prefill` (a group fact, `questionnaire/prefill.py`; G28) and, on a plan
row, `plan.<fact>` (G30, G134). A block's `rows_from` names the plans its starting rows follow (G134).
"""

# A data module: its hand-laid tables stay as written.
# fmt: off

from . import fl_blue_51_data as data

# Defects in the carrier's own form: the category picker offers labels its change script never matches, so in the
# real Florida Blue PDF choosing either shows no conditions. Mapped onto the branch the author meant (G12).
CATEGORY_ALIASES = {
    'Non-cancerous Tumor': 'Non-Cancerous Tumor',
    'Stomach': 'Stomach/Esophagus',
}
CONDITION_ALIASES = {
    'Unknown Brain/Neurological Condition': 'Unknown Neurological Condition',
}

BID_REASONS = [
    'Comparing Benefits & Rates',
    'Dissatisfaction with Service',
    'Healthcare Reform',
    'Renewal Increase',
    'To Provide Health Coverage',
    'Other',
]

CONTRIBUTION_METHODS = ['Percentage', 'Defined Contribution']

# Question 11's dropdown, verbatim from the carrier template's save list.
SWITCH_COUNTS = ['0', '1', '2', '3', '4', '5+']

STATE_CODES = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA',
    'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR',
    'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
]  # fmt: skip

# The carrier's State picker saves the code and displays the long name; the stamp prints the name (G57, slice 43).
STATE_NAMES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado',
    'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'District of Columbia', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky',
    'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota',
    'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire',
    'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota',
    'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island',
    'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
}  # fmt: skip

# Verbatim from the form's own printed render — do not paraphrase.
HIPAA_NOTICE = (
    'Please answer the following questions to the best of your knowledge for all eligible employees and their '
    'dependents (proprietors, partners, corporate officers, employees, spouses and dependent children). This '
    'information will be used to evaluate medical risk, not eligibility for individual coverage. The Health Insurance '
    'Portability and Accountability Act ("HIPAA") prohibits group health insurance issuers from establishing rules for '
    'eligibility on the basis of health factors. Health factors are defined as: health status; medical condition; '
    'claims experience; receipt of health care; medical history; genetic information; evidence of insurability, and '
    'disability.'
)

CATEGORY_INTRO = (
    'Please use the section below to indicate any applicable medical conditions associated with any individuals '
    'currently eligible or covered on the company’s health insurance policy. The list below provides the medical '
    'categories available within the form. Additional questions will be presented based on the values selected in the '
    'previous questions.'
)

RATES_INTRO = (
    '15. Please use the section below to provide details regarding the company’s current and renewal premiums with '
    'their in force health carrier. Attach a copy of the renewal, if available.'
)

COMMENTS_LABEL = (
    'Comments (Please indicate any additional information that you may have regarding the conditions above and/or if '
    'any individual represents more than 1 condition listed above, please provide a brief explanation below as well.)'
)

OFFICER_ATTESTATION = (
    'The undersigned Company Officer and Agent hereby acknowledges that: 1) the information set out in this '
    'Underwriting Questionnaire will be relied on by Blue Cross and Blue Shield of Florida, Inc./Health Options, Inc.; '
    '(2) this information is complete, truthful and correct; (3) to the best of my knowledge no information has been '
    'withheld or omitted concerning the past and present state of health of eligible employees and their dependents '
    'applying for this coverage and; (4) the summary health information set out in this Underwriting Questionnaire was '
    'not acquired, used, or disclosed other than as is permitted by applicable law, and specifically was not and will '
    'not be used for employment-related actions and/or decisions. I understand that any person who knowingly and with '
    'intent to injure, defraud, or deceive any insurer files a statement of claim or application containing any false, '
    'incomplete or misleading information is guilty of a felony of the third degree.'
)

# The carrier's SIC table less its six "Test Industry" rows (G17, P5): filtered once, when the tables load.
SIC_CODES = [row for row in data.SIC_CODES if not row[1].startswith('Test Industry')]

# --- sections -----------------------------------------------------------------------------------------------------

SECTION_GENERAL = {
    'key': 'general', 'number': 'I', 'label': 'General Information',
    'fields': [
        {'key': 'txtCoName', 'label': '1. Name of Business', 'type': 'text', 'required': True, 'width': 2,
         'prefill': 'legal_name'},
        {'key': 'dteAnnivDate', 'label': '2. Anniversary Date', 'type': 'date', 'required': True,
         'prefill': 'anniversary_date'},
        {'key': 'txtBusAdd', 'label': '3. Business Address', 'type': 'text', 'required': True, 'width': 2,
         'prefill': 'address_street'},
        {'key': 'txtAdd2', 'label': 'Business Address Line 2', 'type': 'text'},
        {'key': 'City', 'label': '4. City', 'type': 'text', 'required': True, 'prefill': 'address_city'},
        {'key': 'State', 'label': '5. State', 'type': 'choice', 'required': True, 'options': STATE_CODES,
         'prefill': 'address_state', 'display_map': STATE_NAMES},
        {'key': 'ZipCode', 'label': '6. Zip Code', 'type': 'text', 'required': True, 'prefill': 'address_zip'},
        {'key': 'drpSIC', 'label': '7. SIC Code', 'type': 'choice', 'options_from': 'sic_codes', 'option_mode': 'code',
         'prefill': 'sic_code', 'pair_with': 'drpSICDesc',
         'hint': 'Pick by code or by description — either sets the other.'},
        {'key': 'drpSICDesc', 'label': 'SIC Description', 'type': 'choice', 'options_from': 'sic_codes',
         'option_mode': 'description', 'prefill': 'sic_description', 'pair_with': 'drpSIC'},
        {'key': 'TextField2', 'label': 'Tax Id', 'type': 'text', 'prefill': 'fein', 'hint': 'FEIN, XX-XXXXXXX'},
    ],
}

SECTION_HISTORY = {
    'key': 'history', 'number': 'II', 'label': 'Health Coverage History',
    'fields': [
        # ATNE: the prior calendar year's average, never today's headcount (`total_employees`).
        {'key': 'numTAP', 'type': 'number', 'required': True, 'width': 3,
         'label': "8. What is the company's Total Average Number of Employees on Payroll in the preceding calendar "
                  'year?',
         'prefill': 'atne'},
        {'key': 'numCurrentCarrierEligCount', 'type': 'number', 'required': True, 'width': 3,
         'label': '9. Total number of current Eligible Employees:', 'prefill': 'eligible_employees'},
        {'key': 'chkFBPrior', 'type': 'yesno', 'required': True, 'width': 3,
         'label': '10. Has this group had Florida Blue health insurance coverage within the past 24 months?'},
        {'key': 'drpNumCarr', 'type': 'choice', 'width': 3, 'options': SWITCH_COUNTS,
         'label': '11. How many times has the group switched health carriers within the past 5 years?'},
        {'key': 'txtRsnBid', 'label': '12. Reason for Current Bid Request', 'type': 'choice', 'required': True,
         'width': 2, 'options': BID_REASONS},
        {'key': 'txtRsnBidComments', 'width': 3, 'type': 'text',
         'label': 'Please provide an explanation for the bid reason:',
         'visible_if': {'field': 'txtRsnBid', 'op': 'eq', 'value': 'Other'}},
    ],
}

SECTION_CARRIER = {
    'key': 'carrier', 'number': 'III', 'label': 'Current Health Carrier Information',
    'fields': [
        {'key': 'chkVirgin', 'type': 'yesno', 'required': True, 'width': 3,
         'label': '13. Is this replacing current medical coverage through another carrier?',
         'prefill': 'replacing_coverage'},
        # The carrier keeps Section III (and question 15) on screen until "No" is picked: `ne`, not eq-'Yes'.
        {'key': 'txtCurrentCarrier', 'label': 'Name of Current Carrier', 'type': 'text', 'width': 2,
         'prefill': 'current_carrier', 'visible_if': {'field': 'chkVirgin', 'op': 'ne', 'value': 'No'}},
        {'key': 'drpEEContMethod', 'label': '14. Employer Contribution Method', 'type': 'choice',
         'options': CONTRIBUTION_METHODS, 'visible_if': {'field': 'chkVirgin', 'op': 'ne', 'value': 'No'}},
        {'key': 'numERConPercent', 'label': 'Employee %', 'type': 'percent',
         'visible_if': {'field': 'drpEEContMethod', 'op': 'eq', 'value': 'Percentage'}},
        {'key': 'numDepConPercent', 'label': 'Dependent %', 'type': 'percent',
         'visible_if': {'field': 'drpEEContMethod', 'op': 'eq', 'value': 'Percentage'}},
        {'key': 'numERConDefined', 'label': 'Employee $', 'type': 'money',
         'visible_if': {'field': 'drpEEContMethod', 'op': 'eq', 'value': 'Defined Contribution'}},
        {'key': 'numDepConDefined', 'label': 'Dependent $', 'type': 'money',
         'visible_if': {'field': 'drpEEContMethod', 'op': 'eq', 'value': 'Defined Contribution'}},
    ],
    'intro_after_fields': RATES_INTRO,
    'blocks': ['plans'],
}

SECTION_MEDICAL = {
    'key': 'medical', 'number': 'IV', 'label': 'Group Medical History',
    'intro': HIPAA_NOTICE,
    'legend': data.CATEGORY_LEGEND,
    'legend_intro': CATEGORY_INTRO,
    'fields': [
        {'key': 'chkMedCon', 'type': 'yesno', 'required': True, 'width': 3, 'sensitive': True,
         'label': '16. Within the past 12 months, have any employees or their dependents been diagnosed or treated for '
                  'any of the conditions listed in the below section. Please select all that apply.'},
        # The carrier prints the comments box below the condition grid it refers to (G21).
        {'key': 'txtMcComments', 'label': COMMENTS_LABEL, 'type': 'text', 'width': 3, 'sensitive': True,
         'placement': 'after_blocks'},
    ],
    'blocks': ['conditions'],
}

SECTION_SIGNATURE = {
    'key': 'signature', 'number': 'V', 'label': 'Applicant Signatures',
    'intro': OFFICER_ATTESTATION,
    'fields': [
        {'key': 'txtgrprepname', 'label': 'Print Name of Authorized Company Officer', 'type': 'text', 'width': 2,
         'required': True, 'prefill': 'officer_name'},
        {'key': 'txtTitleOfficer', 'label': 'Title of Authorized Company Officer', 'type': 'text',
         'prefill': 'officer_title'},
        {'key': 'txtagentname', 'label': 'Print Name of Agent/Agent Number', 'type': 'text', 'width': 2,
         'prefill': 'agent_name', 'broker': True},
        {'key': 'txtAgencyName', 'label': 'Name of Agency', 'type': 'text', 'prefill': 'agency_name', 'broker': True},
    ],
}

# --- repeating blocks -----------------------------------------------------------------------------------------------

BLOCK_PLANS = {
    'key': 'plans', 'label': 'Current plan', 'row_label': 'Plan', 'add_label': 'Add Another Plan',
    'empty_label': 'No current plans listed.', 'min_rows': 1, 'max_rows': 12,
    'rows_from': 'current_medical',  # one starting row per current medical plan (G134)
    'visible_if': {'field': 'chkVirgin', 'op': 'ne', 'value': 'No'},
    'fields': [
        {'key': 'numPlannum', 'label': 'Plan Count', 'type': 'number', 'auto': 'row_number'},
        {'key': 'txtCurrPlanName', 'label': 'Plan Name/Description', 'type': 'text', 'width': 2,
         'prefill': 'plan.name'},
        {'key': 'dteCurrCarrEffDt', 'label': 'Current Plan Effective Date', 'type': 'date',
         'prefill': 'plan.effective_date'},
        # Q15's premiums are typed by staff (OQ56 default): no prefill from the Advisor.
        {'key': 'numCurrRatePrem', 'label': 'Current Premium for Health Coverage', 'type': 'money'},
        {'key': 'numRenPrem', 'label': 'Renewal Premium for Health Coverage', 'type': 'money'},
    ],
}

BLOCK_CONDITIONS = {
    'key': 'conditions', 'label': 'Group Medical Conditions', 'row_label': 'Row', 'add_label': 'Add Condition',
    'empty_label': 'No conditions reported.', 'min_rows': 0, 'max_rows': 60, 'sensitive': True,
    'visible_if': {'field': 'chkMedCon', 'op': 'eq', 'value': 'Yes'},
    'fields': [
        {'key': 'txtMedConRow', 'label': 'Row', 'type': 'number', 'auto': 'row_number'},
        {'key': 'drpMedCat', 'label': 'Medical Category', 'type': 'choice', 'required': True,
         'options_from': 'med_categories'},
        {'key': 'drpMedCondition', 'label': 'Medical Condition', 'type': 'choice',
         'options_from': 'conditions_by_category', 'depends_on': 'drpMedCat', 'alias': 'category'},
        {'key': 'drpMedConDetail', 'label': 'Medical Condition Detail', 'type': 'choice',
         'options_from': 'details_by_condition', 'depends_on': 'drpMedCondition', 'alias': 'condition'},
        {'key': 'numNumEEMedCon', 'type': 'number', 'required': True, 'width': 2,
         'label': 'How many total individuals are associated with this condition?'},
        {'key': 'txtSurgPlanned', 'type': 'number', 'effect': 'surgery',
         'label': 'Number of individuals with planned surgeries:'},
        {'key': 'txtSurgUnplanned', 'type': 'number', 'effect': 'surgery',
         'label': 'Number of individuals with no planned surgeries:'},
        {'key': 'txtSurgUnknown', 'type': 'number', 'effect': 'surgery',
         'label': 'Number of individuals where surgery is unknown:'},
        {'key': 'txtTransplantPlanned', 'type': 'number', 'effect': 'transplant',
         'label': 'Number of individuals with planned transplants:'},
        {'key': 'txtTransplantUnplanned', 'type': 'number', 'effect': 'transplant',
         'label': 'Number of individuals with no planned transplants:'},
        {'key': 'txtTransplantUnknown', 'type': 'number', 'effect': 'transplant',
         'label': 'Number of individuals where transplants are unknown:'},
        {'key': 'numCancerDetailyes', 'type': 'number', 'effect': 'cancer_counts',
         'label': 'Number of Individuals with additional information regarding their condition.'},
        {'key': 'num_CancerDetailsno', 'type': 'number', 'effect': 'cancer_counts',
         'label': 'Number of individuals with no additional information regarding their condition.'},
        {'key': 'txtMedIll', 'type': 'text', 'width': 3,
         'label': 'Provide details regarding illness, medications, date of last treatment, etc.',
         'visible_if': {'field': 'numCancerDetailyes', 'op': 'gt', 'value': 0}},
    ],
    # The fields whose answers decide a row's effects (G13; P1: no Florida Blue names in the engine).
    'effect_drivers': {'category': 'drpMedCat', 'condition': 'drpMedCondition'},
}

FORM = {
    'key': 'fl_blue_51',
    'version': 'v9',
    'kind': 'medical',
    'carrier': 'Florida Blue',
    'short_label': 'Florida Blue 51+',
    'export_slug': 'medical-questionnaire',
    'title': 'Florida Blue Underwriting Questionnaire',
    'subtitle': 'Supplement to Group Application — For Large Groups (51 or more employees)',
    'officer_label': 'Authorized company officer',
    'sections': [SECTION_GENERAL, SECTION_HISTORY, SECTION_CARRIER, SECTION_MEDICAL, SECTION_SIGNATURE],
    'blocks': {'plans': BLOCK_PLANS, 'conditions': BLOCK_CONDITIONS},
    'tables': {
        'sic_codes': SIC_CODES,
        'med_categories': data.MED_CATEGORIES,
        'conditions_by_category': data.CONDITIONS_BY_CATEGORY,
        'details_by_condition': data.DETAILS_BY_CONDITION,
        'category_effects': data.CATEGORY_EFFECTS,
        'condition_effects': data.CONDITION_EFFECTS,
        'condition_overrides': data.CONDITION_OVERRIDES,
        # Effect flags on while a row has no category yet: the carrier template shows the two cancer-count boxes on a
        # fresh row, and its category change script hides them (hand-written: the template says it by presence).
        'initial_effects': ['cancer_counts'],
    },
    'aliases': {'category': CATEGORY_ALIASES, 'condition': CONDITION_ALIASES},
    'blank_pdf': 'fl_blue_51_blank_v9.pdf',
}
