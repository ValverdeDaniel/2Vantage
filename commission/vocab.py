"""Commission's vocabulary (plan.md §4, §5.6, §6.9; H10–H24, H95–H101), served by /api/meta/ as `commission` (rule 1).

A data module: the roles a split row takes and the kinds of party each role accepts, the bases, the split's sources
and the scopes, in old Vantage's words (891f1b3 `overview/SplitsPanel.jsx`, `PartySelect.jsx`, `PartiesTab.jsx`,
`CommissionPanel.jsx`). The house is implicit: it is never a party (H.6).
"""

from decimal import Decimal

PRIMARY, SECONDARY, SPLIT, REFERRAL = 'primary', 'secondary', 'split', 'referral'
ROLES = [(PRIMARY, 'Primary'), (SECONDARY, 'Secondary'), (SPLIT, 'Split'), (REFERRAL, 'Referral')]
ROLE_KEYS = tuple(key for key, _ in ROLES)
OTHER_ROLES = (SECONDARY, SPLIT, REFERRAL)  # the rows under the primary, in the editor's order
ROLE_HINT = (
    'Secondary = one of our producers working the account · Split = anyone paid a split · '
    'Referral = the outside agent who brought the deal'
)
ADD_LABELS = {SECONDARY: '＋ Secondary producer', SPLIT: '＋ Split', REFERRAL: '＋ Referral agent'}

PRODUCER, PARTNER = 'producer', 'partner'
KINDS = [(PRODUCER, 'Producer'), (PARTNER, 'Partner')]
KIND_KEYS = tuple(key for key, _ in KINDS)
KIND_GROUPS = {PRODUCER: 'Producers', PARTNER: 'Partners'}
# Which kinds of party each role takes (H12, H19): the primary and secondaries are our producers; a referral agent
# is an outside partner; a split may be anyone.
ROLE_KINDS = {PRIMARY: [PRODUCER], SECONDARY: [PRODUCER], SPLIT: [PRODUCER, PARTNER], REFERRAL: [PARTNER]}

POOL, GROSS = 'pool', 'gross'
BASES = [(POOL, 'of the producer pool'), (GROSS, 'of gross revenue')]
BASIS_KEYS = tuple(key for key, _ in BASES)
BASIS_HINT = "Pool = a share of the producer's share · Gross = a share of agency revenue before the house"
RENEWAL_MODES = [('same', 'same amount'), ('different', 'different amount')]

# Where the split that applies came from (H10), in the resolver's order.
DEAL, CLIENT, DEAL_OWNER, CLIENT_OWNER, HOUSE = 'deal', 'client', 'deal_owner', 'client_owner', 'house'
SOURCES = {
    DEAL: 'set on this deal',
    CLIENT: 'set on the client — applies to every deal',
    DEAL_OWNER: 'default: the deal owner, 100 %',
    CLIENT_OWNER: 'default: the client owner, 100 %',
    HOUSE: 'no producer set — house keeps 100 %',
}
# The editor's "Applies to" choice (H20): the client split is the durable home, the deal's an override.
SCOPES = [(CLIENT, 'this client (all deals)'), (DEAL, 'this deal only')]
SCOPE_KEYS = tuple(key for key, _ in SCOPES)
SCOPE_HINT = 'Client = applies to this and every future deal for the client. Deal = an override for this one deal.'

# Where a line's effective rate came from (H5, H8).
RATE_DEAL, RATE_AGENCY = 'deal', 'agency'
RATE_SOURCES = {RATE_DEAL: '', RATE_AGENCY: 'agency default', '': 'not set'}

# The package a line's expected revenue is worked out on (H6, §5.6): Sold once the line has a sold plan, else
# Renewal, Current, then the first starred plan as an estimate.
BASIS_PACKAGES = {'sold': 'Sold', 'renewal': 'Renewal', 'current': 'Current', 'estimate': 'estimate'}

# The firm defaults (H100; the old placeholders from the 8/18 call): the producer's share of agency revenue.
DEFAULT_FIRST_YEAR_PCT = Decimal('40')
DEFAULT_RENEWAL_PCT = Decimal('30')

LIMITS = {'name': 200, 'email': 254, 'phone': 50, 'npn': 20, 'max_years': 99, 'notes': 2000, 'reason': 300}

# A booked record's status (H54; 891f1b3 `BookTab.jsx` STATUS_OPTIONS, plus `void`, H32). Expected counts booked and
# active records only (bug 5); a void record is hidden from the Book unless the status filter asks for it.
BOOKED, ACTIVE, RENEWED, TERMINATED, LOST_BOR, VOID = 'booked', 'active', 'renewed', 'terminated', 'lost_bor', 'void'
STATUSES = [
    (BOOKED, 'Booked'),
    (ACTIVE, 'Active'),
    (RENEWED, 'Renewed'),
    (TERMINATED, 'Terminated'),
    (LOST_BOR, 'Lost (BOR)'),
    (VOID, 'Void'),
]
STATUS_KEYS = tuple(key for key, _ in STATUSES)
STATUS_LABELS = dict(STATUSES)
LIVE = (BOOKED, ACTIVE)
ENDED = (RENEWED, TERMINATED, LOST_BOR, VOID)  # a hand move to one of these adds a term end (H54)

# What booking could not fill (H37), shown, never guessed: the Book's short word and the drawer's sentence
# (891f1b3 `BookingSummaryModal.jsx` HOLE_LABEL, `RecordDrawer.jsx` HOLE_LABEL).
HOLES = {
    'premium': ('premium', 'premium not known — enter the final premium as billed'),
    'rate': ('rate', 'rate not set for this deal'),
    'employees': ('enrolled count', 'enrolled count needed for PEPM'),
    'year': ('year unknown', 'year with us not known — booked at the renewal %'),
    'effective': ('effective date', 'no effective date'),
    'plan': ('no sold plan', 'no sold plan on this line'),
}
# Where a record's fact came from (`sources` origin; the old SOURCE_LABEL's words).
RECORD_SOURCES = {
    'sale': 'from the sale',
    'typed': 'entered by hand',
    'in_force': 'in force (Intake)',
    'agency': 'agency default',
}
BOOK_CAP = 500  # rows one Book answer carries; past it the screen asks to narrow the filter (H50, review 32)
NOT_BOOKED = 'Sold — not booked'
DISCLOSURE_HINT = 'Send it only inside the close-out packet.'


def _pairs(choices):
    return [{'key': key, 'label': label} for key, label in choices]


def meta():
    return {
        'roles': _pairs(ROLES),
        'other_roles': list(OTHER_ROLES),
        'role_hint': ROLE_HINT,
        'add_labels': ADD_LABELS,
        'kinds': _pairs(KINDS),
        'kind_groups': KIND_GROUPS,
        'role_kinds': ROLE_KINDS,
        'bases': _pairs(BASES),
        'basis_hint': BASIS_HINT,
        'renewal_modes': _pairs(RENEWAL_MODES),
        'sources': SOURCES,
        'scopes': _pairs(SCOPES),
        'scope_hint': SCOPE_HINT,
        'rate_sources': RATE_SOURCES,
        'limits': LIMITS,
        'statuses': _pairs(STATUSES),
        'live_statuses': list(LIVE),
        'holes': {key: {'short': short, 'long': long} for key, (short, long) in HOLES.items()},
        'record_sources': RECORD_SOURCES,
        'not_booked': NOT_BOOKED,
        'disclosure_hint': DISCLOSURE_HINT,
    }
