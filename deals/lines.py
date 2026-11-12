"""Lines of coverage, tiers and funding (plan.md §4.1, §4.2, §4.6).

Generated from plan.md §4.1 by script (§14); a data module, exempt from the 300-line rule.
"""

LINES = [
    {
        'key': 'medical',
        'label': 'Medical',
        'short': 'Med',
        'field_set': 'medical',
        'rate_basis': 'composite',
        'tier_field': 'medical_tier',
        'proxy': False,
    },
    {
        'key': 'dental',
        'label': 'Dental',
        'short': 'Den',
        'field_set': 'dental',
        'rate_basis': 'composite',
        'tier_field': 'dental_tier',
        'proxy': False,
    },
    {
        'key': 'vision',
        'label': 'Vision',
        'short': 'Vis',
        'field_set': 'vision',
        'rate_basis': 'composite',
        'tier_field': 'vision_tier',
        'proxy': False,
    },
    {
        'key': 'basic_life_add',
        'label': 'Basic Life & AD&D',
        'short': 'Life',
        'field_set': 'life',
        'rate_basis': 'volume_1000',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'voluntary_life',
        'label': 'Voluntary Life',
        'short': 'Vol Life',
        'field_set': 'life',
        'rate_basis': 'volume_1000',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'std',
        'label': 'Short-Term Disability',
        'short': 'STD',
        'field_set': 'disability',
        'rate_basis': 'weekly_10',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'ltd',
        'label': 'Long-Term Disability',
        'short': 'LTD',
        'field_set': 'disability',
        'rate_basis': 'payroll_100',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'voluntary_worksite',
        'label': 'Voluntary / Worksite',
        'short': 'Worksite',
        'field_set': 'generic',
        'rate_basis': 'composite',
        'tier_field': 'medical_tier',
        'proxy': True,
    },
    {
        'key': 'hsa',
        'label': 'HSA',
        'short': 'HSA',
        'field_set': 'generic',
        'rate_basis': 'pepm',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'fsa',
        'label': 'FSA',
        'short': 'FSA',
        'field_set': 'generic',
        'rate_basis': 'pepm',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'hra',
        'label': 'HRA',
        'short': 'HRA',
        'field_set': 'generic',
        'rate_basis': 'pepm',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'eap',
        'label': 'EAP',
        'short': 'EAP',
        'field_set': 'generic',
        'rate_basis': 'pepm',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'telehealth',
        'label': 'Telehealth',
        'short': 'Telehealth',
        'field_set': 'generic',
        'rate_basis': 'pepm',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'voluntary_std',
        'label': 'Voluntary STD',
        'short': 'Vol STD',
        'field_set': 'disability',
        'rate_basis': 'weekly_10',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'voluntary_ltd',
        'label': 'Voluntary LTD',
        'short': 'Vol LTD',
        'field_set': 'disability',
        'rate_basis': 'payroll_100',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'accident',
        'label': 'Accident',
        'short': 'Accident',
        'field_set': 'generic',
        'rate_basis': 'composite',
        'tier_field': 'medical_tier',
        'proxy': True,
    },
    {
        'key': 'hospital',
        'label': 'Hospital Indemnity',
        'short': 'Hospital',
        'field_set': 'generic',
        'rate_basis': 'composite',
        'tier_field': 'medical_tier',
        'proxy': True,
    },
    {
        'key': 'critical_illness',
        'label': 'Critical Illness',
        'short': 'CI',
        'field_set': 'generic',
        'rate_basis': 'composite',
        'tier_field': 'medical_tier',
        'proxy': True,
    },
    {
        'key': 'legal',
        'label': 'Legal',
        'short': 'Legal',
        'field_set': 'generic',
        'rate_basis': 'pepm',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'identity_theft',
        'label': 'Identity Theft',
        'short': 'ID Theft',
        'field_set': 'generic',
        'rate_basis': 'pepm',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'gap',
        'label': 'Gap',
        'short': 'Gap',
        'field_set': 'generic',
        'rate_basis': 'composite',
        'tier_field': 'medical_tier',
        'proxy': True,
    },
    {
        'key': 'dependent_care_fsa',
        'label': 'Dependent Care FSA',
        'short': 'DCFSA',
        'field_set': 'generic',
        'rate_basis': 'pepm',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'ichra',
        'label': 'ICHRA',
        'short': 'ICHRA',
        'field_set': 'generic',
        'rate_basis': 'pepm',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'pet',
        'label': 'Pet',
        'short': 'Pet',
        'field_set': 'generic',
        'rate_basis': 'pepm',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'individual_life',
        'label': 'Individual Life',
        'short': 'Ind Life',
        'field_set': 'life',
        'rate_basis': 'volume_1000',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'stop_loss',
        'label': 'Stop-Loss',
        'short': 'Stop-Loss',
        'field_set': 'stop_loss',
        'rate_basis': 'stop_loss',
        'tier_field': None,
        'proxy': False,
    },
    {
        'key': 'pbm',
        'label': 'PBM (Pharmacy)',
        'short': 'PBM',
        'field_set': 'generic',
        'rate_basis': 'pepm',
        'tier_field': None,
        'proxy': False,
    },
]

LINE_KEYS = [line['key'] for line in LINES]
BY_KEY = {line['key']: line for line in LINES}

TIERS = [
    ('EE', 'Employee only'),
    ('ES', 'Employee + Spouse'),
    ('EC', 'Employee + Child(ren)'),
    ('FAM', 'Family'),
]
TIER_CODES = [code for code, _ in TIERS]

# Current coverage and the medical plan field `funding` (§4.6).
FUNDING = [
    ('fully_insured', 'Fully insured'),
    ('level_funded', 'Level-funded'),
    ('self_funded', 'Self-funded'),
]

# Typed enrollment by rate basis (§5.5): tier counts, benefit volume or payroll, or lives. quotes/math reads it.
ENROLLMENT_KEYS = {
    'composite': TIER_CODES,
    'volume_1000': ['volume'],
    'weekly_10': ['volume'],
    'payroll_100': ['volume'],
    'pepm': ['lives'],
    'stop_loss': ['lives'],
}


def get(key):
    return BY_KEY.get(key)


def label(key):
    line = BY_KEY.get(key)
    return line['label'] if line else key


def meta():
    return [dict(line) for line in LINES]
