"""Warner Pacific Large Group Coverage Form (51+), rev. 12/12/25 (G1). A data module, exempt from the 300-line rule.

The other 51+ medical form, a producer's pick (the band still defaults to Florida Blue, which requires its own):
Warner's form is accepted by every medical carrier except Florida Blue. Ported from old Vantage 891f1b3
(`benefits/questionnaires/wp_lg.py`); its AcroForm field map (`acroform`) is the export's, slice 43's (G59).

Flags as in `fl_blue_51.py`. G31 (new): the waiting period, years in business and agent of record prefill from intake
and the BOR on file; G134 (new): the current and renewal rate grids prefill from the current medical plans and their
renewals, one option per plan up to the form's three.
"""

# A data module: its hand-laid tables stay as written.
# fmt: off

# The three carrier-history rows the paper prints; no overflow convention on the form, so none here either.
HISTORY_ROWS = 3
# Current and renewal rate grids: three option columns, each a plan's name and its four tier rates.
RATE_OPTIONS = 3

YES_NO_CHOICE = ['Yes', 'No']

SECTION_GROUP = {
    'key': 'group', 'number': '1', 'label': 'Group information',
    'intro': 'The header Warner reads first — who the group is, when they want coverage, and how big they are.',
    'fields': [
        {'key': 'group_name', 'label': 'Group Name', 'type': 'text', 'required': True, 'width': 3,
         'prefill': 'legal_name'},
        {'key': 'effective_date', 'label': 'Requested Effective Date', 'type': 'date', 'required': True,
         'prefill': 'anniversary_date'},
        {'key': 'address', 'label': 'Address', 'type': 'text', 'width': 3, 'prefill': 'address_street'},
        {'key': 'phone', 'label': 'Phone', 'type': 'text', 'prefill': 'phone'},
        {'key': 'city', 'label': 'City', 'type': 'text', 'width': 2, 'prefill': 'address_city'},
        {'key': 'state', 'label': 'State', 'type': 'text', 'prefill': 'address_state'},
        {'key': 'zip', 'label': 'Zip', 'type': 'text', 'prefill': 'address_zip'},
        {'key': 'sic_description', 'label': 'Ind. Description / SIC', 'type': 'text', 'width': 2,
         'hint': 'What the business does, or its SIC code.'},
        # ATNE: the prior calendar year's average; never today's headcount.
        {'key': 'atne', 'label': 'ATNE (Average Total # of Employees)', 'type': 'number', 'required': True,
         'prefill': 'atne',
         'hint': 'Average total employees over the PRIOR calendar year — not today’s headcount.'},
        {'key': 'eligible_employees', 'label': '# of Eligible Employees', 'type': 'number', 'required': True,
         'prefill': 'eligible_employees'},
        {'key': 'fein', 'label': 'FEIN / Tax ID', 'type': 'text', 'width': 2, 'prefill': 'fein'},
        {'key': 'current_rates_effective', 'label': 'Current Rates Effective Date', 'type': 'date', 'width': 2},
        {'key': 'years_in_business', 'label': 'Years in Business', 'type': 'number', 'prefill': 'years_in_business'},
        {'key': 'employer_contribution', 'label': 'Employer Contribution', 'type': 'text', 'width': 2,
         'hint': 'e.g. 50% of employee only, or a defined dollar amount.'},
        {'key': 'waiting_period', 'label': 'New Hire Waiting Period', 'type': 'text', 'prefill': 'waiting_period'},
        {'key': 'bid_reason', 'label': 'Reason for issuing request for bids', 'type': 'text', 'width': 3},
    ],
}

SECTION_HISTORY = {
    'key': 'history', 'number': '2', 'label': 'Health insurance history',
    'intro': 'List all health insurance carriers covering your group during the past five (5) years. Please attach '
             'full benefit summaries.',
    'fields': [],
    'blocks': ['carriers'],
}

BLOCK_CARRIERS = {
    'key': 'carriers', 'label': 'Carriers, past five years', 'row_label': 'Carrier', 'add_label': 'Add carrier',
    'empty_label': 'No prior carriers listed.', 'min_rows': 1, 'max_rows': HISTORY_ROWS,
    'fields': [
        {'key': 'carrier', 'label': 'Carrier', 'type': 'text', 'required': True, 'width': 3},
        {'key': 'from_date', 'label': 'From', 'type': 'date'},
        {'key': 'to_date', 'label': 'To', 'type': 'date'},
    ],
}

SECTION_RATES = {
    'key': 'rates', 'number': '3', 'label': 'Rates',
    'intro': 'The current rates and the renewal as offered, up to three options each — one row per tier.',
    'fields': [],
    'blocks': ['current_rates', 'renewal_rates'],
}


def _rate_block(key, label, plan):
    """Current and Renewal are the same five rows, three option columns; `plan` is the plan a row reads (`plan` for
    the current plan, `renewal` for its renewal). Copied as-is from the plan's tier rates (G134); Warner's "Double"
    reads the EE + Spouse rate (OQ56 asks whether it is; built as the old form's own reading)."""
    return {
        'key': key, 'label': label, 'row_label': 'Option', 'add_label': 'Add option',
        'empty_label': 'No options entered.', 'min_rows': 1, 'max_rows': RATE_OPTIONS, 'rows_from': 'current_medical',
        'fields': [
            {'key': 'plan_type', 'label': 'Plan Type', 'type': 'text', 'width': 2,
             'hint': 'The plan’s name, as the carrier prints it.', 'prefill': f'{plan}.name'},
            {'key': 'single', 'label': 'Single', 'type': 'money', 'prefill': f'{plan}.rate_ee'},
            {'key': 'double', 'label': 'Double', 'type': 'money', 'prefill': f'{plan}.rate_es'},
            {'key': 'ee_child', 'label': 'EE + Child', 'type': 'money', 'prefill': f'{plan}.rate_ec'},
            {'key': 'family', 'label': 'Family', 'type': 'money', 'prefill': f'{plan}.rate_fam'},
        ],
    }


BLOCK_CURRENT_RATES = _rate_block('current_rates', 'Current rates', 'plan')
BLOCK_RENEWAL_RATES = _rate_block('renewal_rates', 'Renewal rates', 'renewal')

# The seven questions, verbatim from the form — do not paraphrase.
QUESTIONS = [
    ('q1_hospitalized', '1. Is any employee or dependent currently hospitalized?'),
    ('q2_disabled', '2. Is any employee or dependent disabled?'),
    ('q3_cobra', '3. Is any employee or dependent on COBRA?'),
    ('q4_large_expenses',
     '4. Has any employee or dependent incurred medical expenses in excess of $10,000 during the last 12 months?'),
    ('q5_ongoing_care',
     '5. Is any employee or dependent currently under the care of a physician for any ongoing medical conditions? '
     '(pregnancy, psychiatric, cancer, AIDS, heart conditions, etc.)'),
    ('q6_cancer_treatment', '6. Has any employee or dependent had radiation therapy, chemotherapy, or cancer surgery?'),
    ('q7_family_history',
     '7. Does any employee have a family history of serious inheritable disease? (i.e. muscular dystrophy, cystic '
     'fibrosis, etc.)'),
]

SECTION_MEDICAL = {
    'key': 'medical', 'number': '4', 'label': 'Current medical data',
    'intro': 'For any yes answers, provide age/sex, diagnosis and current status. The form has no space for those '
             'details — record them here and they travel with the request; the carrier’s page carries the answers '
             'themselves.',
    'fields': (
        [{'key': key, 'label': label, 'type': 'choice', 'options': YES_NO_CHOICE, 'width': 3, 'sensitive': True}
         for key, label in QUESTIONS]
        + [
            {'key': 'disability_cobra_detail', 'width': 3, 'type': 'text', 'sensitive': True,
             'label': 'If yes to 2 or 3 — date of onset and current status',
             'hint': 'Indicate whether the member is an employee or a dependent.'},
            {'key': 'medical_detail', 'width': 3, 'type': 'text', 'sensitive': True,
             'label': 'Details for any other yes answer',
             'hint': 'Age/sex, diagnosis and current status — attached to the request, since the form itself has no '
                     'room for it.'},
        ]
    ),
}

CERTIFICATION = (
    'I hereby certify that all information required above is accurate and complete. I understand that any willful '
    'misrepresentation of information provided will result in the termination of my group coverage retroactive to the '
    'effective date of coverage. I understand my obligations for any charges retroactive to the date of coverage. I '
    'understand that this form will be incorporated into my group’s contract if the group elects coverage. Any person '
    'who knowingly and with intent to injure, fraud or deceive any insurer files a statement of claim or an '
    'application containing any false, incomplete or misleading information is guilty of a felony of the third degree.'
)

SECTION_SIGNATURES = {
    'key': 'signatures', 'number': '5', 'label': 'Employer certification',
    'intro': CERTIFICATION,
    'fields': [
        {'key': 'rep_title', 'label': 'Title — Company Representative', 'type': 'text', 'prefill': 'officer_title'},
        {'key': 'agent_of_record', 'label': 'Agent of Record', 'type': 'choice', 'options': YES_NO_CHOICE,
         'prefill': 'agent_of_record', 'broker': True},
        {'key': 'wp_consultant', 'label': 'Warner Pacific Consultant', 'type': 'text', 'broker': True,
         'hint': 'Warner’s own consultant on the account, if known.'},
    ],
}

FORM = {
    'key': 'wp_lg',
    'version': 'rev121225',
    'kind': 'medical',
    'carrier': 'Warner Pacific (51+, all carriers except Florida Blue)',
    'short_label': 'Warner Pacific 51+',
    'export_slug': 'wp-large-group-form',
    'title': 'Large Group Coverage Form',
    'subtitle': 'Warner Pacific — accepted by every medical carrier except Florida Blue, which requires its own '
                '(rev. 12/12/25)',
    'officer_label': 'Authorized company officer',
    'sections': [SECTION_GROUP, SECTION_HISTORY, SECTION_RATES, SECTION_MEDICAL, SECTION_SIGNATURES],
    'blocks': {
        'carriers': BLOCK_CARRIERS,
        'current_rates': BLOCK_CURRENT_RATES,
        'renewal_rates': BLOCK_RENEWAL_RATES,
    },
    'tables': {},
    # The carriers this form is the right one for (`rfp/carriers.py` keys): every medical carrier except Florida Blue.
    'rfp_carriers': ['aetna', 'angle_health', 'avmed', 'cigna', 'curative', 'gravie', 'nationwide', 'optimyl',
                     'sidecar_health', 'trustmark', 'unitedhealthcare'],
    'blank_pdf': 'wp_lg_rev121225.pdf',
}
