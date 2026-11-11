"""Document kinds and roles (plan.md §4.6)."""

KINDS = [
    ('quote', 'Carrier quote'),
    ('renewal', 'Renewal / rates'),
    ('sbc', 'SBC / plan summary'),
    ('census', 'Census'),
    ('invoice', 'Current invoice'),
    ('bor', 'BOR / signed authorization'),
    ('carrier_auth', 'Carrier authorization'),
    ('claims', 'Claims experience'),
    ('plan_doc', 'Plan document / SPD'),
    ('proposal', 'Proposal / presentation'),
    ('other', 'Other'),
]
KIND_KEYS = {key for key, _ in KINDS}

# "What is this document?" — only for quotes, renewals and SBCs.
ROLES = [
    ('current', 'Current plans in force'),
    ('renewal', 'Renewal of the current plans'),
    ('alternates', 'Alternate quotes'),
]
ROLE_KEYS = {key for key, _ in ROLES}
ROLE_KINDS = {'quote', 'renewal', 'sbc'}

# Downloads of these kinds are recorded in Activity (§3.8).
PHI_KINDS = {'census', 'claims'}

ALLOWED_EXTENSIONS = {
    '.pdf',
    '.xlsx',
    '.xlsm',
    '.xls',
    '.csv',
    '.png',
    '.jpg',
    '.jpeg',
    '.docx',
    '.doc',
    '.txt',
    '.eml',
    '.msg',
}
