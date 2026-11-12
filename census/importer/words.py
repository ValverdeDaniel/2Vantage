"""The importer's words (plan.md §4.2, §4.8; C12, C14, C16). A data module, exempt from the 300-line rule.

Generated from old Vantage 891f1b3 `market/census_reader.py` (`HEADER_SYNONYMS`, the line tokens, the bare
effective-date headers and their preceding phrases, the employee relationship words) and `market/validation.py`
(`TIER_ALIASES`, `WAIVE_WORDS`), unchanged: this table feeds the offline mapper (C14). Claude's mapping assist
(slice 51) sees column shapes only and never replaces it (D109).
"""

import re

# Census key -> accepted header spellings, normalized (`norm_header`). A key's own words and its label (§4.4) are
# exact synonyms too. Order matters: the exact pass takes the first key that matches.
HEADER_SYNONYMS = {
    'ext_emp_id': ['emp id', 'employee id', 'emp no', 'employee number', 'eid', 'id'],
    'first_name': ['first name', 'fname', 'first', 'employee first name', 'member first name', 'given name'],
    'last_name': ['last name', 'lname', 'last', 'employee last name', 'member last name', 'surname'],
    'relationship': ['relationship', 'rel', 'relation', 'rel code', 'relationship code', 'member type'],
    'dob': ['dob', 'date of birth', 'birth date', 'birthdate', 'birthday'],
    'ssn': [
        'ssn', 'social', 'social security', 'social security number', 'ss', 'ssn no dashes', 'emp ssn',
        'dependent ssn', 'member ssn',
    ],
    'gender': ['gender', 'sex', 'm f'],
    'address1': ['address', 'street address', 'address 1', 'addr', 'home address', 'street'],
    'city': ['city', 'home city'],
    'state': ['state', 'st', 'home state'],
    'zip': [
        'zip', 'zip code', 'postal code', 'postal', 'home zip', 'home zip code', 'home postal code', 'zipcode',
        'residence zip',
    ],
    'division': ['division', 'div', 'location', 'department', 'dept'],
    'emp_class': ['class', 'emp class', 'employee class', 'occupation class', 'job class'],
    'hire_date': ['hire date', 'date of hire', 'doh', 'start date', 'employment date'],
    'medical_plan': [
        'medical plan', 'plan', 'plan name', 'plan selection', 'med plan', 'plan election', 'current medical plan',
        'current plan', 'current plan election', 'current medical', 'medical plan name',
    ],
    'medical_tier': [
        'tier', 'coverage tier', 'coverage', 'med tier', 'coverage level', 'election', 'coverage election',
    ],
    'effective_date': [
        'medical effective date', 'medical eff date', 'effective date', 'eff date', 'coverage effective date',
        'coverage start', 'benefit start date',
    ],
    'subscriber_ssn': ['employee ssn', 'subscriber ssn', 'ee ssn', 'primary ssn', 'employee social security number'],
    'middle_name': ['middle name', 'middle', 'mi', 'middle initial'],
    'address2': ['address 2', 'address2', 'address line 2', 'apt', 'suite', 'unit'],
    'phone': ['phone', 'phone number', 'telephone', 'cell', 'mobile', 'home phone'],
    'annual_salary': ['annual salary', 'annual base salary', 'base salary', 'salary', 'annual income', 'wages'],
    'job_title': ['job title', 'title', 'occupation', 'position'],
    'work_state': ['benefit work state', 'work state', 'work location state', 'employment state'],
    'term_date': ['termination date', 'term date', 'termination', 'separation date', 'end date'],
    'rehire_date': ['rehire date', 'rehire', 're hire date'],
    'dental_plan': ['dental plan', 'dental', 'dental plan name', 'dental election'],
    'dental_tier': ['dental tier', 'dental coverage', 'dental coverage tier', 'dental level', 'dental coverage level'],
    'dental_effective_date': ['dental effective date', 'dental eff date', 'dental effective'],
    'vision_plan': ['vision plan', 'vision', 'vision plan name', 'vision election'],
    'vision_tier': ['vision tier', 'vision coverage', 'vision coverage tier', 'vision level', 'vision coverage level'],
    'vision_effective_date': ['vision effective date', 'vision eff date', 'vision effective'],
    'basic_life_amount': [
        'basic life amount', 'basic life', 'basic life benefit', 'basic life volume', 'life amount',
        'life insurance amount',
    ],
    'basic_life_effective_date': ['basic life effective date', 'basic life eff date', 'life effective date'],
    'vol_life_amount': [
        'voluntary life insurance', 'voluntary life amount', 'voluntary life', 'vol life amount', 'vol life',
        'supplemental life',
    ],
    'vol_life_effective_date': ['vol life effective date', 'voluntary life effective date', 'vol life eff date'],
    'std_amount': ['std benefit amount', 'std amount', 'std', 'short term disability', 'short term disability amount'],
    'std_effective_date': ['std effective date', 'std eff date', 'short term disability effective date'],
    'ltd_amount': ['ltd benefit amount', 'ltd amount', 'ltd', 'long term disability', 'long term disability amount'],
    'ltd_effective_date': ['ltd effective date', 'ltd eff date', 'long term disability effective date'],
    'employment_status': [
        'employment status', 'employee status', 'employment type', 'ft pt', 'full time part time', 'fte status',
        'work status',
    ],
    'hours_per_week': [
        'hours per week', 'hours week', 'hrs per week', 'hrs week', 'weekly hours', 'hrs wk', 'hours wk', 'hours',
        'hrs', 'scheduled hours', 'avg hours per week', 'average hours per week',
    ],
    'email': ['email', 'email address', 'e mail', 'employee email', 'work email', 'email addr'],
    'county': ['county', 'home county', 'county of residence', 'county name'],
    'waiver_reason': [
        'waiver reason', 'waive reason', 'valid waiver', 'medical waiver reason', 'reason for waiving',
        'reason waived', 'waiver', 'decline reason', 'reason for declining',
    ],
}  # fmt: skip

# A key holding one of these words may be claimed by the fuzzy pass only when the header names that word.
LINE_TOKENS = ('medical', 'dental', 'vision', 'life', 'std', 'ltd')

# Headers that name an effective date without saying whose; the column before them decides (§4.8).
BARE_EFFECTIVE_HEADERS = ('effective date', 'eff date', 'effective')
PRECEDING_LINE_EFFECTIVE = [
    ('basic life', 'basic_life_effective_date'),
    ('vol life', 'vol_life_effective_date'),
    ('voluntary life', 'vol_life_effective_date'),
    ('supplemental life', 'vol_life_effective_date'),
    ('life', 'basic_life_effective_date'),
    ('short term disability', 'std_effective_date'),
    ('long term disability', 'ltd_effective_date'),
    ('std', 'std_effective_date'),
    ('ltd', 'ltd_effective_date'),
    ('dental', 'dental_effective_date'),
    ('vision', 'vision_effective_date'),
    ('medical', 'effective_date'),
]

# A row whose relationship is blank or one of these is an employee (§4.8).
EMPLOYEE_RELATIONSHIPS = frozenset({'ee', 'emp', 'employee', 'self', 'subscriber', 'primary', 'e'})

# Mapping confidence (§5.3.2 step 4).
EXACT, POSITIONAL, FUZZY = 0.95, 0.70, 0.60
LOW_BELOW = 0.85

# Tier spellings (case-insensitive, trimmed) and the waiver words (§4.2).
TIER_SPELLINGS = {
    'EE': 'EE', 'EMP': 'EE', 'EMPLOYEE': 'EE', 'EMPLOYEE ONLY': 'EE', 'SINGLE': 'EE',
    'ES': 'ES', 'E+S': 'ES', 'EMPLOYEE + SPOUSE': 'ES', 'EMPLOYEE+SPOUSE': 'ES', 'EMP+SP': 'ES',
    'EC': 'EC', 'E+C': 'EC', 'EMPLOYEE + CHILD': 'EC', 'EMPLOYEE + CHILDREN': 'EC', 'EMPLOYEE + CHILD(REN)': 'EC',
    'EMP+CH': 'EC',
    'FAM': 'FAM', 'F': 'FAM', 'FAMILY': 'FAM', 'EF': 'FAM', 'E+F': 'FAM',
}  # fmt: skip
WAIVE_WORDS = frozenset({'WAIVE', 'WAIVED', 'WAIVER', 'W', 'DECLINE', 'DECLINED', 'NONE', 'N/A', 'NA'})

# The words a dependent's relationship is read by (validation's tier checks, §5.3.4).
SPOUSE_WORDS = ('spouse', 'wife', 'husband', 'partner', 'dp')
CHILD_WORDS = ('child', 'son', 'daughter', 'dependent child', 'stepchild')


def norm_header(text):
    """Lower-case; every character outside a–z 0–9 space becomes a space; runs of spaces collapse (§4.8)."""
    return ' '.join(re.sub(r'[^a-z0-9 ]+', ' ', str(text or '').lower()).split())


def tier_code(value):
    """EE, ES, EC or FAM for a tier spelling, else ''. A waiver word is not a tier."""
    return TIER_SPELLINGS.get(str(value or '').strip().upper(), '')


def is_waiver(value):
    return str(value or '').strip().upper() in WAIVE_WORDS


def is_employee_relationship(value):
    text = str(value or '').strip().lower()
    return text == '' or text in EMPLOYEE_RELATIONSHIPS
