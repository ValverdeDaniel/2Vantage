"""The census columns (plan.md §4.4, §5.3.3; C.5; OQ16, OQ17). A data module, exempt from the 300-line rule.

Generated from plan.md §4.4 (keys, labels, groups, types and Required codes, in display order) with the help text of
old Vantage 891f1b3 `market/census_request.py` (`CENSUS_FIELD_HELP`) and the choices of `market/validation.py`
(`CENSUS_CHOICES`, `TIER_CHOICES`). `is_required` is the one rule for a required cell: nothing else decides it.

Required codes: `A` every person · `E` employees only · `L:<line>` employees only, when the line is requested ·
`M` employees only, when medical is requested and the deal has medical in force today · '' optional.
SSN is optional, kept and validated when present, shown masked, never asked on the portal (OQ16's default).
"""

from collections import namedtuple

from documents.kinds import TABULAR

GROUPS = [
    ('identity', 'Identity'),
    ('demographics', 'Demographics'),
    ('employment', 'Employment'),
    ('medical', 'Medical'),
    ('dental', 'Dental'),
    ('vision', 'Vision'),
    ('life', 'Life'),
    ('disability', 'Disability'),
]

# type: text · ssn · date · tier · money · number (§5.3.1 cleans each).
FIELDS = [
    {
        'key': 'ext_emp_id',
        'label': 'Emp ID',
        'group': 'identity',
        'type': 'text',
        'required': '',
        'help': "Your own employee number or payroll ID, if you use one. Leave blank if you don't.",
    },
    {
        'key': 'first_name',
        'label': 'First Name',
        'group': 'identity',
        'type': 'text',
        'required': 'A',
        'help': 'Legal first name as it appears on their Social Security card — not a nickname.',
    },
    {
        'key': 'middle_name',
        'label': 'Middle Name',
        'group': 'identity',
        'type': 'text',
        'required': '',
        'help': 'Middle name or initial, if known. Optional.',
    },
    {
        'key': 'last_name',
        'label': 'Last Name',
        'group': 'identity',
        'type': 'text',
        'required': 'A',
        'help': 'Legal last name as it appears on their Social Security card.',
    },
    {
        'key': 'relationship',
        'label': 'Relationship',
        'group': 'identity',
        'type': 'text',
        'required': '',
        'help': 'Who this person is to the employee — Spouse, Child, or Domestic Partner.',
    },
    {
        'key': 'subscriber_ssn',
        'label': 'Employee SSN',
        'group': 'identity',
        'type': 'ssn',
        'required': '',
        'help': "The EMPLOYEE's Social Security number, on a dependent's row — it links the dependent to them.",
    },
    {
        'key': 'dob',
        'label': 'Date of Birth',
        'group': 'demographics',
        'type': 'date',
        'required': 'A',
        'help': 'Date of birth. Any common format works (MM/DD/YYYY or YYYY-MM-DD).',
    },
    {
        'key': 'ssn',
        'label': 'SSN',
        'group': 'demographics',
        'type': 'ssn',
        'required': '',
        # OQ16: optional. The old text said carriers require it; they quote without it (§4.4).
        'help': '9-digit Social Security number, if you have it. Optional: carriers quote without it.',
    },
    {
        'key': 'gender',
        'label': 'Gender',
        'group': 'demographics',
        'type': 'text',
        'required': 'A',
        'help': 'M or F, as the carrier will need it on the enrollment.',
    },
    {
        'key': 'address1',
        'label': 'Address',
        'group': 'demographics',
        'type': 'text',
        'required': '',
        'help': 'Home street address (not a PO box) — carriers rate by where people live.',
    },
    {
        'key': 'address2',
        'label': 'Address 2',
        'group': 'demographics',
        'type': 'text',
        'required': '',
        'help': 'Apartment, suite or unit number, if any.',
    },
    {
        'key': 'city',
        'label': 'City',
        'group': 'demographics',
        'type': 'text',
        'required': '',
        'help': 'Home city.',
    },
    {
        'key': 'state',
        'label': 'State',
        'group': 'demographics',
        'type': 'text',
        'required': '',
        'help': 'Two-letter state of the home address (e.g. FL).',
    },
    {
        'key': 'zip',
        'label': 'ZIP',
        'group': 'demographics',
        'type': 'text',
        'required': 'E',
        'help': '5-digit home ZIP code — this decides the rating area.',
    },
    {
        'key': 'county',
        'label': 'County',
        'group': 'demographics',
        'type': 'text',
        'required': '',
        'help': "Home county. Leave it blank if you're not sure — we can work it out from the ZIP code.",
    },
    {
        'key': 'phone',
        'label': 'Phone',
        'group': 'demographics',
        'type': 'text',
        'required': '',
        'help': 'A phone number for the employee. Optional.',
    },
    {
        'key': 'email',
        'label': 'Email',
        'group': 'demographics',
        'type': 'text',
        'required': '',
        'help': 'A work email for the employee, if you have one. Carriers use it for enrollment confirmations.',
    },
    {
        'key': 'division',
        'label': 'Division',
        'group': 'employment',
        'type': 'text',
        'required': '',
        'help': 'Division or location code, if your company tracks one. Optional.',
    },
    {
        'key': 'emp_class',
        'label': 'Class',
        'group': 'employment',
        'type': 'text',
        'required': '',
        'help': "Benefit class, if your plan has more than one (e.g. Hourly / Salaried, or 'All Eligible').",
    },
    {
        'key': 'job_title',
        'label': 'Job Title',
        'group': 'employment',
        'type': 'text',
        'required': '',
        'help': 'Job title. Some carriers use it to classify the role.',
    },
    {
        'key': 'hire_date',
        'label': 'Hire Date',
        'group': 'employment',
        'type': 'date',
        'required': '',
        'help': 'Date of hire — it sets when benefits start. From your payroll or HR system.',
    },
    {
        'key': 'employment_status',
        'label': 'Employment Status',
        'group': 'employment',
        'type': 'text',
        'required': '',
        'help': 'Full-time or Part-time. Carriers quote full-time only, so we need to know which is which.',
    },
    {
        'key': 'hours_per_week',
        'label': 'Hours / Week',
        'group': 'employment',
        'type': 'number',
        'required': 'E',
        'help': 'Hours worked per week. It decides who counts as full-time, which is how carriers size the group.',
    },
    {
        'key': 'annual_salary',
        'label': 'Annual Salary',
        'group': 'employment',
        'type': 'money',
        'required': '',
        'help': 'Annual base salary. Needed only to quote life and disability, which pay a multiple of it.',
    },
    {
        'key': 'work_state',
        'label': 'Work State',
        'group': 'employment',
        'type': 'text',
        'required': '',
        'help': 'Two-letter state where this person works, if different from where they live.',
    },
    {
        'key': 'term_date',
        'label': 'Termination Date',
        'group': 'employment',
        'type': 'date',
        'required': '',
        'help': 'Termination date, for anyone no longer employed who is still on the list.',
    },
    {
        'key': 'rehire_date',
        'label': 'Rehire Date',
        'group': 'employment',
        'type': 'date',
        'required': '',
        'help': 'Rehire date, if this person left and came back.',
    },
    {
        'key': 'medical_plan',
        'label': 'Medical Plan',
        'group': 'medical',
        'type': 'text',
        'required': 'M',
        'help': "The medical plan they're on today, as it's named on your carrier invoice.",
    },
    {
        'key': 'medical_tier',
        'label': 'Medical Tier',
        'group': 'medical',
        'type': 'tier',
        'required': 'L:medical',
        'help': (
            'Who is covered on medical: EE (employee only), ES (+ spouse), EC (+ child(ren)) or FAM (family). '
            "'Waived' if they declined."
        ),
    },
    {
        'key': 'effective_date',
        'label': 'Medical Effective Date',
        'group': 'medical',
        'type': 'date',
        'required': '',
        'help': "The date their current medical coverage started — on your carrier's enrollment confirmation.",
    },
    {
        'key': 'waiver_reason',
        'label': 'Waiver Reason',
        'group': 'medical',
        'type': 'text',
        'required': '',
        'help': (
            "For anyone declining coverage, why — usually a spouse's plan, a parent's plan, Medicare or Medicaid. "
            "Blank is fine if you don't know."
        ),
    },
    {
        'key': 'dental_plan',
        'label': 'Dental Plan',
        'group': 'dental',
        'type': 'text',
        'required': '',
        'help': "The dental plan they're on today, as named on your invoice.",
    },
    {
        'key': 'dental_tier',
        'label': 'Dental Tier',
        'group': 'dental',
        'type': 'tier',
        'required': 'L:dental',
        'help': (
            'Who is covered on dental: EE (employee only), ES (+ spouse), EC (+ child(ren)) or FAM (family). '
            "'Waived' if they declined."
        ),
    },
    {
        'key': 'dental_effective_date',
        'label': 'Dental Effective Date',
        'group': 'dental',
        'type': 'date',
        'required': '',
        'help': 'The date their dental coverage started.',
    },
    {
        'key': 'vision_plan',
        'label': 'Vision Plan',
        'group': 'vision',
        'type': 'text',
        'required': '',
        'help': "The vision plan they're on today, as named on your invoice.",
    },
    {
        'key': 'vision_tier',
        'label': 'Vision Tier',
        'group': 'vision',
        'type': 'tier',
        'required': 'L:vision',
        'help': (
            'Who is covered on vision: EE (employee only), ES (+ spouse), EC (+ child(ren)) or FAM (family). '
            "'Waived' if they declined."
        ),
    },
    {
        'key': 'vision_effective_date',
        'label': 'Vision Effective Date',
        'group': 'vision',
        'type': 'date',
        'required': '',
        'help': 'The date their vision coverage started.',
    },
    {
        'key': 'basic_life_amount',
        'label': 'Basic Life Amount',
        'group': 'life',
        'type': 'money',
        'required': '',
        'help': "The employer-paid life insurance amount (e.g. $25,000 or 1× salary), from your life carrier's bill.",
    },
    {
        'key': 'basic_life_effective_date',
        'label': 'Basic Life Effective Date',
        'group': 'life',
        'type': 'date',
        'required': '',
        'help': 'The date their basic life coverage started.',
    },
    {
        'key': 'vol_life_amount',
        'label': 'Voluntary Life Amount',
        'group': 'life',
        'type': 'money',
        'required': '',
        'help': 'Any extra life insurance the employee bought themselves. Blank means none.',
    },
    {
        'key': 'vol_life_effective_date',
        'label': 'Vol Life Effective Date',
        'group': 'life',
        'type': 'date',
        'required': '',
        'help': 'The date their voluntary life coverage started.',
    },
    {
        'key': 'std_amount',
        'label': 'STD Benefit Amount',
        'group': 'disability',
        'type': 'money',
        'required': '',
        'help': 'Short-term disability weekly benefit, if enrolled. Blank means none.',
    },
    {
        'key': 'std_effective_date',
        'label': 'STD Effective Date',
        'group': 'disability',
        'type': 'date',
        'required': '',
        'help': 'The date their short-term disability coverage started.',
    },
    {
        'key': 'ltd_amount',
        'label': 'LTD Benefit Amount',
        'group': 'disability',
        'type': 'money',
        'required': '',
        'help': 'Long-term disability monthly benefit, if enrolled. Blank means none.',
    },
    {
        'key': 'ltd_effective_date',
        'label': 'LTD Effective Date',
        'group': 'disability',
        'type': 'date',
        'required': '',
        'help': 'The date their long-term disability coverage started.',
    },
]

TIER_CHOICES = [
    ('EE', 'EE: Employee only'),
    ('ES', 'ES: Employee + Spouse'),
    ('EC', 'EC: Employee + Child(ren)'),
    ('FAM', 'FAM: Family'),
    ('Waived', 'Waived: declined this line'),
]
WAIVED = 'Waived'

STATE_CODES = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS',
    'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC',
    'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
]  # fmt: skip

# Accepted values offered as choices (§4.4). Suggestions, never a closed list: other spellings are still read (§5.3).
CHOICES = {
    'gender': [('M', 'Male'), ('F', 'Female')],
    'relationship': [('Spouse', 'Spouse'), ('Child', 'Child'), ('Domestic Partner', 'Domestic Partner')],
    'employment_status': [
        ('Full-time', 'Full-time'),
        ('Part-time', 'Part-time'),
        ('COBRA', 'COBRA continuation'),
        ('Retiree', 'Retiree'),
    ],
    'state': [(code, code) for code in STATE_CODES],
    'work_state': [(code, code) for code in STATE_CODES],
}

BY_KEY = {field['key']: field for field in FIELDS}
KEYS = [field['key'] for field in FIELDS]
TIER_KEYS = [field['key'] for field in FIELDS if field['type'] == 'tier']
SSN_KEYS = ('ssn', 'subscriber_ssn')

# Each line's own census columns: its plan text and tier (composite lines), or the column its volume sums (§4.1).
PLAN_FIELDS = {'medical': 'medical_plan', 'dental': 'dental_plan', 'vision': 'vision_plan'}
VOLUME_FIELDS = {
    'basic_life_add': 'basic_life_amount',
    'voluntary_life': 'vol_life_amount',
    'individual_life': 'vol_life_amount',
    'std': 'std_amount',
    'voluntary_std': 'std_amount',
    'ltd': 'annual_salary',
    'voluntary_ltd': 'annual_salary',
}

# The grid's line chips (C2): which lines turn a group's columns on.
GROUP_LINES = {
    'medical': ['medical'],
    'dental': ['dental'],
    'vision': ['vision'],
    'life': ['basic_life_add', 'voluntary_life', 'individual_life'],
    'disability': ['std', 'ltd', 'voluntary_std', 'voluntary_ltd'],
}

# A dependent inherits the employee's employment and elections, and their ZIP (§5.3.3 step 1).
DEPENDENT_EXEMPT_GROUPS = ('employment', 'medical', 'dental', 'vision', 'life', 'disability')
DEPENDENT_EXEMPT_KEYS = ('zip',)

AUTO, REQUIRED, WAIVED_RULE = 'auto', 'required', 'waived'
RULES = [(AUTO, 'Auto'), (REQUIRED, 'Required'), (WAIVED_RULE, 'Waived')]  # per deal and column (OQ17, C27)

EMPLOYEE, DEPENDENT = 'employee', 'dependent'
KINDS = [(EMPLOYEE, 'Employee'), (DEPENDENT, 'Dependent')]

# What requiredness reads of the deal: its lines to quote, and whether medical is in force today (intake).
Context = namedtuple('Context', 'requested_lines medical_in_force')


def is_required(key, kind, context, rules=None, carrier_required=None):
    """Whether a `kind` person's `key` cell is required on this deal (§5.3.3). The first step that applies decides:
    a dependent's employment, election and ZIP cells never; the deal's Waived or Required rule; A and E; a requested
    line's tier (L); the current medical plan when medical is requested and in force (M); a carrier file that needs
    it for this kind of person; otherwise not."""
    field = BY_KEY[key]
    if kind == DEPENDENT and (field['group'] in DEPENDENT_EXEMPT_GROUPS or key in DEPENDENT_EXEMPT_KEYS):
        return False
    rule = (rules or {}).get(key, AUTO)
    if rule == WAIVED_RULE:
        return False
    if rule == REQUIRED:
        return True
    code = field['required']
    if code == 'A':
        return True
    if code == 'E':
        return kind == EMPLOYEE
    requested = context.requested_lines or ()
    if code.startswith('L:'):
        return code[2:] in requested
    if code == 'M':
        return 'medical' in requested and bool(context.medical_in_force)
    needed = (carrier_required or {}).get(key) or {}
    return bool(needed.get(EMPLOYEE if kind == EMPLOYEE else DEPENDENT))


def required_keys(kind, context, rules=None, carrier_required=None):
    """The keys `is_required` answers yes for one kind of person, in display order (one call per kind, not per cell)."""
    return [key for key in KEYS if is_required(key, kind, context, rules, carrier_required)]


def label(key):
    field = BY_KEY.get(key)
    return field['label'] if field else key


def choices(key):
    """(value, label) pairs a column offers; [] for free text. Every tier column offers the tiers plus Waived."""
    if BY_KEY.get(key, {}).get('type') == 'tier':
        return TIER_CHOICES
    return CHOICES.get(key, [])


def meta():
    """The census section of /api/meta/."""
    return {
        'groups': [{'key': key, 'label': name} for key, name in GROUPS],
        'fields': [
            {**field, 'choices': [{'value': v, 'label': t} for v, t in choices(field['key'])]} for field in FIELDS
        ],
        'group_lines': GROUP_LINES,
        'rules': [{'key': key, 'label': name} for key, name in RULES],
        'kinds': [{'key': key, 'label': name} for key, name in KINDS],
        'import_accept': list(TABULAR),  # what the import door reads (§5.3.2 step 1); a PDF roster is Claude's (51)
    }
