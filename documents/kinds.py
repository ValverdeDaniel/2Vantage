"""Document kinds, buckets and roles (plan.md §4.6, E.6; O.6 #12). A data module: served by /api/meta/.

Each kind says what a file IS: its label, the bucket the Documents tab files it under (E1), the extensions it accepts
(checked against the file's first bytes at upload, E6, E7), whether the quick "File as" list offers it (Daniel's six,
E5), whether it asks what the file is (its role, E13) and whether it is PHI (its downloads and views are logged, E99;
§3.8). Issued proposals are kind `proposal`: protected and never screened (J.6.4). The wrap, POP and sold-paperwork
kinds wait with close-out and implementation (OQ26); `commission_statement` waits with the ledger (OQ6).
"""

# How each extension is read, and so which viewer shows it (E21): one place (the old docscan.kinds.SHAPES).
PDF, IMAGE, SHEET = 'pdf', 'image', 'sheet'
SHAPES = {
    '.pdf': PDF,
    '.png': IMAGE,
    '.jpg': IMAGE,
    '.jpeg': IMAGE,
    '.xlsx': SHEET,
    '.xlsm': SHEET,
    '.xls': SHEET,
    '.csv': SHEET,
}

PDF_ONLY = ('.pdf',)
SCANNED = ('.pdf', '.png', '.jpg', '.jpeg')  # what a filled paper form comes back as
TABULAR = ('.xlsx', '.xlsm', '.xls', '.csv')
READABLE = SCANNED + TABULAR  # every extension a viewer shows (the old quote kind's list)
# Paperwork a person keeps but nothing reads: it downloads, and the viewer says it cannot show it (E30).
PAPERWORK = READABLE + ('.docx', '.doc', '.txt', '.eml', '.msg')
CENSUS_FILES = TABULAR + PDF_ONLY
ISSUED = ('.pdf', '.pptx', '.xlsx', '.docx')

BUCKETS = [
    ('proposal', 'Proposal'),
    ('census', 'Census'),
    ('intake', 'Intake'),
    ('questionnaire', 'Questionnaire'),
]

# key: (label, bucket, accept, file_as, asks_role, phi). `bucket` None: no tag (an issued proposal).
_KINDS = {
    'quote': ('Carrier quote', 'proposal', READABLE, True, True, False),
    'renewal': ('Renewal / rates', 'proposal', READABLE, False, True, False),
    'sbc': ('SBC / plan summary', 'proposal', READABLE, True, True, False),
    'census': ('Census', 'census', CENSUS_FILES, True, False, True),
    'invoice': ('Current invoice', 'intake', PAPERWORK, False, False, False),  # OQ27: invoices are not PHI
    'bor': ('BOR / signed authorization', 'intake', PAPERWORK, False, False, False),
    'carrier_auth': ('Carrier authorization', 'intake', PAPERWORK, False, False, False),
    'claims': ('Claims experience', 'intake', PAPERWORK, False, False, True),
    'plan_doc': ('Plan document / SPD', 'intake', PAPERWORK, False, False, False),
    'proposal': ('Proposal / presentation', None, ISSUED, False, False, False),
    'other': ('Other', 'intake', PAPERWORK, True, False, False),
    'form_5500': ('Prior 5500', 'intake', PAPERWORK, False, False, False),
    'questionnaire': ('Medical questionnaire', 'questionnaire', SCANNED, True, False, True),
    'stop_loss': ('Stop-loss disclosure', 'questionnaire', SCANNED, True, False, True),
    'stop_loss_quote': ('Stop-loss quote', 'proposal', READABLE, False, True, True),
    'tpa_proposal': ('TPA proposal', 'proposal', READABLE, False, True, False),
    'plan_template': ('Plan template', 'proposal', ('.xlsx',), False, False, False),
}

KINDS = [(key, entry[0]) for key, entry in _KINDS.items()]
KIND_KEYS = set(_KINDS)
BY_KEY = {
    key: {
        'key': key,
        'label': label,
        'bucket': bucket,
        'accept': list(accept),
        'file_as': file_as,
        'asks_role': asks_role,
        'phi': phi,
    }
    for key, (label, bucket, accept, file_as, asks_role, phi) in _KINDS.items()
}

# "What is this document?" — only for the kinds that ask (E13).
ROLES = [
    ('current', 'Current plans in force'),
    ('renewal', 'Renewal of the current plans'),
    ('alternates', 'Alternate quotes'),
]
ROLE_KEYS = {key for key, _ in ROLES}
ROLE_KINDS = {key for key, entry in BY_KEY.items() if entry['asks_role']}

# Downloads and views of these kinds are logged (§3.8, E99); so are files the member-data screen found people in.
PHI_KINDS = {key for key, entry in BY_KEY.items() if entry['phi']}

# Every extension some kind accepts.
ALLOWED_EXTENSIONS = {ext for entry in BY_KEY.values() for ext in entry['accept']}


def extension(filename):
    name = (filename or '').lower()
    dot = name.rfind('.')
    return name[dot:] if dot >= 0 else ''


def shape_of(filename):
    """'pdf' | 'image' | 'sheet' | None: which viewer shows the file (E21). None is an answer: no viewer (E30)."""
    return SHAPES.get(extension(filename))


def accepts(kind, filename):
    return kind in BY_KEY and extension(filename) in BY_KEY[kind]['accept']


def label(kind):
    return BY_KEY[kind]['label'] if kind in BY_KEY else kind


def bucket(kind):
    return BY_KEY[kind]['bucket'] if kind in BY_KEY else None


def meta():
    """For /api/meta/: the kinds in order with their flags, the buckets and the roles."""
    return {
        'document_kinds': [BY_KEY[key] for key in _KINDS],
        'document_buckets': [{'key': key, 'label': text} for key, text in BUCKETS],
        'document_roles': [{'key': key, 'label': text} for key, text in ROLES],
    }
