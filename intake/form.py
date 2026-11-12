"""The intake questions (plan.md §4.5; B1, B2). A data module, exempt from the 300-line rule.

QUESTIONS was generated on 2026-11-11 from old Vantage at commit 891f1b3, `benefits/market/intake.py`: its module-level
literals `SECTIONS`, `STATE_CODES`, `INTAKE_FIELD_SEED` and `FIELD_HELP` were parsed with `ast` (STATE_CODES resolved
inside the seed) and never imported (OQ108's default). The old words were renamed to §4.5's: data types num → number,
pct → percent, yn → yesno, enum → choice; requirement classes qb → need 'Q' (quote-blocking), cond → 'C' (counts when
shown), svc → '' (optional); `visible_if` → `shown_when`; FIELD_HELP → each question's `help`. `employee_count`'s
hint '#' is dropped, as §4.5 shows none.

`client_guidance` (†) is an answer but not one of the questions: it never counts toward readiness, is never asked on
the portal and never prints on a client file (§4.5, O.6 #16). `target_effective_date` writes `Deal.effective_date`
(B1). The questionnaire catalogue and the form choices (G1, G4) join this module with the checklist (slice 40).
"""

SECTIONS = [
    ('employer', 'Employer information'),
    ('eligibility', 'Eligibility & workforce'),
    ('goals', 'Goals & preferences'),
    ('compliance', 'Compliance & regulatory'),
]

TYPES = ('text', 'number', 'money', 'percent', 'date', 'yesno', 'choice', 'multi')
NEEDS = {'Q': 'Quote-blocking', 'C': 'Counts when shown', '': 'Optional'}
OPS = ('gt', 'gte', 'eq', 'nonempty')

STATES = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA',
    'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR',
    'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
]

QUESTIONS = [
    {
        'key': 'legal_name',
        'section': 'employer',
        'label': 'Legal Company Name',
        'type': 'text',
        'need': 'Q',
        'help': (
            'Your exact registered business name — as it appears on your IRS documents or business license, not a '
            'nickname or DBA.'
        ),
    },
    {
        'key': 'dba',
        'section': 'employer',
        'label': 'DBA',
        'type': 'text',
        'hint': 'Doing business as',
        'need': '',
        'help': (
            "Any name you operate or bill under that's different from your legal name. Leave blank if they're the "
            'same.'
        ),
    },
    {
        'key': 'fein',
        'section': 'employer',
        'label': 'FEIN',
        'type': 'text',
        'hint': 'XX-XXXXXXX',
        'need': 'Q',
        'help': (
            "Your 9-digit federal Tax ID (XX-XXXXXXX). It's at the top of your IRS CP-575 confirmation letter, or on "
            "any payroll tax form (Form 941) or a W-2 you've issued."
        ),
    },
    {
        'key': 'entity_type',
        'section': 'employer',
        'label': 'Business Structure',
        'type': 'choice',
        'options': ['LLC', 'S-Corp', 'C-Corp', 'Partnership', 'Non-profit', 'Sole proprietorship'],
        'need': '',
        'help': (
            'How your business is organized (LLC, S-Corp, etc.) — on your business tax return or formation documents.'
        ),
    },
    {
        'key': 'sic_code',
        'section': 'employer',
        'label': 'NAICS / SIC Code',
        'type': 'text',
        'hint': 'e.g. 3441 — Fabricated Structural Metal',
        'need': 'Q',
        'help': (
            "Your industry code. It's on your business tax return, your workers'-comp policy, or search your industry "
            'at naics.com.'
        ),
    },
    {'key': 'years_in_business', 'section': 'employer', 'label': 'Years in Business', 'type': 'number', 'need': ''},
    {'key': 'website', 'section': 'employer', 'label': 'Website', 'type': 'text', 'hint': 'https://…', 'need': ''},
    {
        'key': 'address_physical',
        'section': 'employer',
        'label': 'Physical Address',
        'type': 'text',
        'hint': 'Street, city, state, ZIP',
        'need': 'Q',
        'help': 'The street address where your business physically operates (not a PO box).',
    },
    {
        'key': 'address_mailing',
        'section': 'employer',
        'label': 'Mailing Address',
        'type': 'text',
        'hint': 'If different from physical',
        'need': '',
    },
    {
        'key': 'situs_state',
        'section': 'employer',
        'label': 'Situs State',
        'type': 'choice',
        'options': STATES,
        'hint': 'e.g. TX',
        'need': 'Q',
        'help': (
            'The state where your business is headquartered and files its taxes — this drives which plans carriers can '
            'offer you.'
        ),
    },
    {
        'key': 'states_operating',
        'section': 'employer',
        'label': 'States of Operation',
        'type': 'multi',
        'options': STATES,
        'hint': 'Every state with employees',
        'need': 'Q',
        'help': "Every state where you have employees working — check your payroll records if you're unsure.",
    },
    {'key': 'location_count', 'section': 'employer', 'label': 'Number of Locations', 'type': 'number', 'need': ''},
    {
        'key': 'total_employees',
        'section': 'eligibility',
        'label': 'Total Employees',
        'type': 'number',
        'need': 'Q',
        'help': (
            "Everyone on payroll today, full- and part-time — your payroll system's headcount is the quickest source."
        ),
    },
    {
        'key': 'atne',
        'section': 'eligibility',
        'label': 'ATNE (prior-year average)',
        'type': 'number',
        'need': '',
        'help': (
            "Your average total number of employees over the PRIOR calendar year — not today's headcount. Carriers use "
            'it to decide whether you are a small or large group, so it matters most near 50. Payroll can usually run '
            'it.'
        ),
    },
    {
        'key': 'employee_count',
        'section': 'eligibility',
        'label': 'Eligible Employees',
        'type': 'number',
        'need': 'Q',
        'help': (
            'How many employees are eligible for benefits (usually full-time). Your payroll or HR system can total '
            'this.'
        ),
    },
    {
        'key': 'enrolled_count',
        'section': 'eligibility',
        'label': 'Currently Enrolled — Medical',
        'type': 'number',
        'need': '',
        'help': 'How many employees are actually signed up for medical today — on your latest carrier invoice or bill.',
    },
    {
        'key': 'enrolled_life_count',
        'section': 'eligibility',
        'label': 'Currently Enrolled — Basic Life',
        'type': 'number',
        'need': '',
        'help': (
            "How many employees have basic life coverage — often everyone, even those who waived medical. It's on your "
            "life carrier's invoice."
        ),
    },
    {'key': 'waiving_count', 'section': 'eligibility', 'label': 'Waiving Coverage', 'type': 'number', 'need': ''},
    {
        'key': 'waive_reason',
        'section': 'eligibility',
        'label': 'Main Waive Reason',
        'type': 'choice',
        'options': ["Spouse's plan", 'Medicare', 'Other coverage', 'Cost', 'Other'],
        'need': 'C',
        'shown_when': {'field': 'waiving_count', 'op': 'gt', 'value': 0},
    },
    {'key': 'contractor_count', 'section': 'eligibility', 'label': '1099 Contractors', 'type': 'number', 'need': ''},
    {
        'key': 'payroll_frequency',
        'section': 'eligibility',
        'label': 'Payroll Frequency',
        'type': 'choice',
        'options': ['Weekly', 'Bi-weekly', 'Semi-Monthly', 'Monthly'],
        'need': '',
        'help': 'How often you run payroll (weekly, bi-weekly, etc.).',
    },
    {'key': 'payroll_vendor', 'section': 'eligibility', 'label': 'Payroll Vendor', 'type': 'text', 'need': ''},
    {
        'key': 'payroll_vendor_contact',
        'section': 'eligibility',
        'label': 'Payroll Vendor Contact',
        'type': 'text',
        'need': '',
    },
    {
        'key': 'payroll_processing',
        'section': 'eligibility',
        'label': 'Payroll Processing',
        'type': 'choice',
        'options': ['API', 'Manual'],
        'need': '',
    },
    {'key': 'multi_location', 'section': 'eligibility', 'label': 'Multiple Locations', 'type': 'yesno', 'need': ''},
    {
        'key': 'locations_list',
        'section': 'eligibility',
        'label': 'Locations',
        'type': 'text',
        'hint': 'List each location',
        'need': '',
        'shown_when': {'field': 'multi_location', 'op': 'eq', 'value': 'Yes'},
    },
    {
        'key': 'commission_employees',
        'section': 'eligibility',
        'label': 'Commission-Based Employees',
        'type': 'yesno',
        'need': '',
    },
    {
        'key': 'classes_divisions',
        'section': 'eligibility',
        'label': 'Classes / Divisions',
        'type': 'text',
        'hint': 'List classes or divisions, if any',
        'need': '',
    },
    {
        'key': 'waiting_period',
        'section': 'eligibility',
        'label': 'Waiting Period',
        'type': 'choice',
        'options': [
            'Immediately',
            '1st of the month following hire date',
            '1st of the month following 30 days',
            '1st of the month following 60 days',
            '90 days',
        ],
        'need': '',
        'help': (
            "How long a new hire waits before benefits start — it's in your current plan summary or new-hire "
            'paperwork.'
        ),
    },
    {
        'key': 'hours_threshold',
        'section': 'eligibility',
        'label': 'Hours/Week for Eligibility',
        'type': 'number',
        'hint': '1–40',
        'need': '',
    },
    {'key': 'union', 'section': 'eligibility', 'label': 'Union Employees', 'type': 'yesno', 'need': ''},
    {'key': 'employee_class_1', 'section': 'eligibility', 'label': 'Employee Class 1', 'type': 'text', 'need': ''},
    {'key': 'employee_class_2', 'section': 'eligibility', 'label': 'Employee Class 2', 'type': 'text', 'need': ''},
    {
        'key': 'contribution_by_class',
        'section': 'eligibility',
        'label': 'Contribution Strategy by Class',
        'type': 'text',
        'need': '',
    },
    {
        'key': 'child_age_limit',
        'section': 'eligibility',
        'label': 'Dependent Child Age Limit',
        'type': 'number',
        'hint': 'e.g. 26',
        'need': '',
        'help': 'The age a dependent child ages off your plan (commonly 26).',
    },
    {
        'key': 'domestic_partner',
        'section': 'eligibility',
        'label': 'Domestic Partner Coverage',
        'type': 'yesno',
        'need': '',
    },
    {
        'key': 'reinstatement',
        'section': 'eligibility',
        'label': 'Reinstatement Rule',
        'type': 'choice',
        'options': ['No Reinstatement', 'Standard (3 Months)', 'Other'],
        'need': '',
    },
    {'key': 'budget_target', 'section': 'goals', 'label': 'Monthly Budget Target', 'type': 'money', 'need': ''},
    {
        'key': 'acceptable_increase_pct',
        'section': 'goals',
        'label': 'Acceptable Increase',
        'type': 'percent',
        'hint': '% over current',
        'need': '',
    },
    {
        'key': 'network_priorities',
        'section': 'goals',
        'label': 'Network Priorities',
        'type': 'text',
        'hint': 'Must-keep providers / networks',
        'need': '',
    },
    {
        'key': 'contribution_philosophy',
        'section': 'goals',
        'label': 'Contribution Philosophy',
        'type': 'text',
        'hint': 'e.g. ER pays 75% EE-only',
        'need': '',
    },
    {'key': 'pain_points', 'section': 'goals', 'label': 'Pain Points Today', 'type': 'text', 'need': ''},
    {'key': 'decision_date', 'section': 'goals', 'label': 'Decision Date', 'type': 'date', 'need': ''},
    {
        'key': 'target_effective_date',
        'section': 'goals',
        'label': 'Target Effective Date',
        'type': 'date',
        'need': '',
        'help': "The date you'd like new coverage to start — usually the day after your current plan renews.",
    },
    {
        'key': 'self_funded',
        'section': 'compliance',
        'label': 'Are you self-funded?',
        'type': 'yesno',
        'hint': 'The company pays claims itself (incl. level-funded)',
        'need': '',
        'help': (
            'Does your company pay employee claims itself rather than paying a carrier a fixed premium? Level-funded '
            'plans count as self-funded. If you just pay a monthly premium, answer No.'
        ),
    },
    {
        'key': 'section_125',
        'section': 'compliance',
        'label': 'Section 125 (POP / WRAP)',
        'type': 'yesno',
        'hint': 'Required for any group with pre-tax premiums',
        'need': '',
        'help': (
            "Do you take employee premiums out of pay pre-tax? Almost all groups do — if unsure, leave it and we'll "
            'confirm.'
        ),
    },
    {
        'key': 'section_125_handler',
        'section': 'compliance',
        'label': 'Section 125 — Who Handles It?',
        'type': 'text',
        'hint': 'Vendor, TPA, CPA, or in-house',
        'need': '',
        'shown_when': {'field': 'section_125', 'op': 'eq', 'value': 'Yes'},
        'help': (
            'The vendor, TPA, CPA, or person at your company who maintains your Section 125 plan document. Leave blank '
            "if you'd like us to help place it."
        ),
    },
    {
        'key': 'ale_status',
        'section': 'compliance',
        'label': 'ACA ALE (50+ FTE)',
        'type': 'yesno',
        'hint': 'Applicable Large Employer under the ACA',
        'need': '',
        'help': 'Did you average 50+ full-time (and equivalent) employees last year? If yes, ACA employer rules apply.',
    },
    {
        'key': 'form_5500_required',
        'section': 'compliance',
        'label': 'Form 5500 Filing Required',
        'type': 'yesno',
        'hint': '100+ participants on the first day of the plan year',
        'need': '',
        'help': (
            'Do you have 100+ people enrolled across your benefit plans? If unsure, leave it — we verify this for you.'
        ),
    },
    {
        'key': 'form_5500_handler',
        'section': 'compliance',
        'label': 'Form 5500 — Who Handles It?',
        'type': 'text',
        'hint': 'Vendor, TPA, CPA, or in-house',
        'need': '',
        'shown_when': {'field': 'form_5500_required', 'op': 'eq', 'value': 'Yes'},
        'help': (
            "The vendor, TPA, CPA, or person at your company who files your Form 5500. Leave blank if you'd like us to "
            'help place it.'
        ),
    },
    {'key': 'aca_1095c', 'section': 'compliance', 'label': '1095-C / 1094-C Filing (ALE)', 'type': 'yesno', 'need': ''},
    {
        'key': 'aca_1095c_handler',
        'section': 'compliance',
        'label': '1095-C — Who Handles It?',
        'type': 'text',
        'hint': 'Vendor, TPA, CPA, or in-house',
        'need': '',
        'shown_when': {'field': 'aca_1095c', 'op': 'eq', 'value': 'Yes'},
        'help': (
            'The vendor, payroll company, or person at your company who prepares and files your 1095-C forms. Leave '
            "blank if you'd like us to help place it."
        ),
    },
    {
        'key': 'aca_1095b',
        'section': 'compliance',
        'label': '1095-B / 1094-B Filing',
        'type': 'yesno',
        'hint': 'Small employers with level-funded plans (except Aetna)',
        'need': '',
    },
    {
        'key': 'aca_1095b_handler',
        'section': 'compliance',
        'label': '1095-B — Who Handles It?',
        'type': 'text',
        'hint': 'Vendor, TPA, CPA, or in-house',
        'need': '',
        'shown_when': {'field': 'aca_1095b', 'op': 'eq', 'value': 'Yes'},
        'help': (
            'The vendor, carrier, or person at your company who prepares and files your 1095-B forms. Leave blank if '
            "you'd like us to help place it."
        ),
    },
    {
        'key': 'pcori_filing',
        'section': 'compliance',
        'label': 'PCORI Filing',
        'type': 'yesno',
        'hint': 'Self- and level-funded plans; IRS Form 720, due July 31',
        'need': '',
        'help': (
            'Self-funded and level-funded plans owe a small annual PCORI fee, filed with IRS Form 720 by July 31. If '
            "unsure, leave it — we'll verify this for you."
        ),
    },
    {
        'key': 'pcori_handler',
        'section': 'compliance',
        'label': 'PCORI — Who Handles It?',
        'type': 'text',
        'hint': 'Vendor, TPA, CPA, or in-house',
        'need': '',
        'shown_when': {'field': 'pcori_filing', 'op': 'eq', 'value': 'Yes'},
        'help': (
            "The vendor, TPA, CPA, or person at your company who files your PCORI fee. Leave blank if you'd like us to "
            'help place it.'
        ),
    },
]

GUIDANCE = 'client_guidance'
GUIDANCE_LIMIT = 4000
# How the Goals card shows `client_guidance` (†): an answer, never a question (no need, never on the portal).
GUIDANCE_QUESTION = {
    'key': GUIDANCE,
    'section': 'goals',
    'label': 'Client guidance',
    'type': 'text',
    'hint': 'What the client wants: budget, networks, lines, deductible or benefit levels',
    'need': '',
    'limit': GUIDANCE_LIMIT,
    'help': 'Rank and Claude read this; it never prints on a client file.',
}
EFFECTIVE_DATE = 'target_effective_date'

KEYS = [question['key'] for question in QUESTIONS]
BY_KEY = {question['key']: question for question in QUESTIONS}
ANSWER_KEYS = [*KEYS, GUIDANCE]  # what `Intake.answers` may hold


def meta():
    """`/api/meta/`'s `intake.form`: the sections with their questions, in order."""
    return {
        'sections': [
            {'key': key, 'label': label, 'questions': [dict(q) for q in QUESTIONS if q['section'] == key]}
            for key, label in SECTIONS
        ],
        'needs': [{'key': key, 'label': label} for key, label in NEEDS.items()],
        'guidance': GUIDANCE_QUESTION,
    }
