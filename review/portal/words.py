"""The client portal's words that ride its payload (rule 1; L133: never twinned in JS). A data module: old Vantage's
words (891f1b3 `BenefitsClientPortal.jsx` CENSUS_GROUP_LABELS and COMPLIANCE_TYPES, `views/portal.py`
`_client_checklist`)."""

# The to-do list's rows (L81).
RAIL = {
    'intake': 'Company intake form',
    'people': 'Employee details',
    'census': 'Employee census file',
    'followups': 'Follow-ups',
}

# A person's census fields, under an employer's headings, not the producer's ("Enrollment — Dental").
GROUPS = {
    'identity': 'Who they are',
    'demographics': 'Personal details',
    'employment': 'Employment',
    'medical': 'Medical coverage',
    'dental': 'Dental coverage',
    'vision': 'Vision coverage',
    'life': 'Life insurance',
    'disability': 'Disability coverage',
}

# The compliance files the intake's `files` block asks for, as the old portal named them.
COMPLIANCE = {
    'bor': 'Signed Broker of Record letter',
    'carrier_auth': 'Carrier authorization',
    'claims': 'Claims experience report',
    'form_5500': 'Most recent 5500',
    'plan_doc': 'Plan / wrap documents',
}

FILE_DETAIL = 'PDF, image, or spreadsheet'
CENSUS_FILE_DETAIL = 'XLSX, CSV, or PDF'
