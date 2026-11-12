"""Carriers: who they are and how a carrier name is matched (plan.md §4.7; F14, K104, K105). A data module.

CARRIERS was generated on 2026-11-11 from old Vantage at commit 891f1b3, `benefits/market/rfp_carriers.py`: its
module-level literals were parsed with `ast` (names such as MEDICAL resolved to their constants) and never imported
(OQ108's default). Only key, name, group and aliases are kept here; the census format, the Warner form columns,
`on_form`, the note and the Warner inbox go to `rfp/carriers.py` under the same keys (slice 44), with a test that every
rfp key exists here. The matcher below is the old one (`match`, `carrier_identity`, `display_name`, and
`norm_carrier` and `split_other_carriers` from `implementation/carrier_change.py` and `pipeline/rfp_email.py`).
`/api/meta/` serves `meta()`, so the Advisor's finder and Find on Documents match "UHC" to UnitedHealthcare (OQ14).
"""

import re
from functools import lru_cache

MEDICAL = 'medical'
ANCILLARY = 'ancillary'

CARRIERS = (
    {'key': 'aetna', 'name': 'Aetna', 'group': MEDICAL, 'aliases': ('Aetna Funding Advantage', 'Aetna AFA', 'AFA')},
    {'key': 'angle_health', 'name': 'Angle Health', 'group': MEDICAL, 'aliases': ('Angle',)},
    {'key': 'avmed', 'name': 'AvMed', 'group': MEDICAL, 'aliases': ('Amed',)},
    {'key': 'cigna', 'name': 'Cigna', 'group': MEDICAL, 'aliases': ()},
    {'key': 'curative', 'name': 'Curative', 'group': MEDICAL, 'aliases': ()},
    {'key': 'florida_blue', 'name': 'Florida Blue', 'group': MEDICAL,
     'aliases': ('FL Blue', 'BCBS', 'BlueCross BlueShield', 'BCBS FL', 'Blue Cross Blue Shield of Florida',
                 'BCBS of Florida')},
    {'key': 'gravie', 'name': 'Gravie', 'group': MEDICAL, 'aliases': ('Gravie Level Funded',)},
    {'key': 'nationwide', 'name': 'Nationwide', 'group': MEDICAL, 'aliases': ('Nationwide Level Funded',)},
    {'key': 'optimyl', 'name': 'Optimyl Benefits', 'group': MEDICAL, 'aliases': ('Optimyl',)},
    {'key': 'sidecar_health', 'name': 'Sidecar Health', 'group': MEDICAL, 'aliases': ('Sidecar',)},
    {'key': 'trustmark', 'name': 'Trustmark', 'group': MEDICAL, 'aliases': ()},
    {'key': 'unitedhealthcare', 'name': 'UnitedHealthcare', 'group': MEDICAL,
     'aliases': ('UHC', 'United Healthcare', 'United')},
    {'key': 'guardian', 'name': 'Guardian', 'group': ANCILLARY, 'aliases': ('Guardian Life',)},
    {'key': 'the_hartford', 'name': 'The Hartford', 'group': ANCILLARY, 'aliases': ('Hartford',)},
    {'key': 'humana', 'name': 'Humana', 'group': ANCILLARY, 'aliases': ()},
    {'key': 'metlife', 'name': 'MetLife', 'group': ANCILLARY, 'aliases': ()},
    {'key': 'mutual_of_omaha', 'name': 'Mutual of Omaha', 'group': ANCILLARY, 'aliases': ()},
    {'key': 'principal', 'name': 'Principal', 'group': ANCILLARY, 'aliases': ()},
    {'key': 'sun_life', 'name': 'Sun Life', 'group': ANCILLARY, 'aliases': ('SunLife',)},
    {'key': 'united_concordia', 'name': 'United Concordia', 'group': ANCILLARY, 'aliases': ()},
    {'key': 'unum', 'name': 'Unum', 'group': ANCILLARY, 'aliases': ()},
    {'key': 'apl', 'name': 'APL', 'group': ANCILLARY, 'aliases': ()},
    {'key': 'morgan_white_group', 'name': 'Morgan White Group', 'group': ANCILLARY, 'aliases': ('Morgan White',)},
    {'key': 'transamerica', 'name': 'Transamerica', 'group': ANCILLARY, 'aliases': ()},
    {'key': 'wellfleet', 'name': 'Wellfleet', 'group': ANCILLARY, 'aliases': ()},
)

BY_KEY = {carrier['key']: carrier for carrier in CARRIERS}
KEYS = tuple(BY_KEY)


def meta():
    """/api/meta/ `carriers` (§7.1)."""
    return [{**carrier, 'aliases': list(carrier['aliases'])} for carrier in CARRIERS]


# ---- matching a carrier name (K105) ----------------------------------------------------------------------------
# A wrong match puts a false "quoted" on a client file, so the tiers loosen one step at a time and the generic aliases
# take part only in the exact tier: "United" opens United Concordia and United of Omaha, "BCBS" every Blue plan.

EXACT_ONLY = frozenset({'united', 'bcbs', 'bluecrossblueshield', 'afa', 'amed'})
UNKNOWN_CARRIER = 'Unknown carrier'
# The corporate words `norm` drops ("Aetna Life Insurance Co." is Aetna).
SUFFIXES = (
    'incorporated', 'inc', 'llc', 'lp', 'llp', 'corporation', 'corp', 'company', 'co', 'the', 'insurance', 'life',
    'health', 'plan', 'plans', 'group', 'of', 'america', 'usa',
)  # fmt: skip
NAME_LIMIT = 60
IDENTITY_LIMIT = 120

_NON_WORD = re.compile(r'[^a-z0-9]+')
_SPLIT = re.compile(r'[,;/\n]+')
_AND = re.compile(r'\s+(?:and|&)\s+', re.IGNORECASE)


def _squash(text):
    return _NON_WORD.sub('', str(text or '').lower())


def _words(text):
    return [word for word in _NON_WORD.split(str(text or '').lower()) if word]


def norm(name):
    """A carrier name reduced to its comparable words, corporate words dropped; '' when blank. A name made only of
    corporate words ("The Insurance Company") is kept whole rather than read as unknown."""
    words = _words(name)
    kept = [word for word in words if word not in SUFFIXES]
    return ' '.join(kept or words)


def _normed(text):
    return ''.join(word for word in norm(text).split() if word != 'and')


@lru_cache(maxsize=1)
def _index():
    """(exact, normalised, loose): squashed form -> key. No form is shared by two carriers (a test pins it)."""
    exact, normalised, loose = {}, {}, {}
    for carrier in CARRIERS:
        for form in (carrier['key'], carrier['name'], *carrier['aliases']):
            squashed = _squash(form)
            if not squashed:
                continue
            exact.setdefault(squashed, carrier['key'])
            if squashed not in EXACT_ONLY:
                loose.setdefault(squashed, carrier['key'])
            normed = _normed(form)
            if normed and normed not in EXACT_ONLY:
                normalised.setdefault(normed, carrier['key'])
    return exact, normalised, loose


def match(name):
    """The key a carrier name means, or None. Exact ("UHC", "SunLife", "BCBS FL"); then after `norm` ("Aetna Life
    Insurance Co."); then the longest run of leading words ("UHC Level-Funded", "United Concordia (Dental)")."""
    squashed = _squash(name)
    if not squashed or squashed == _squash(UNKNOWN_CARRIER):
        return None
    exact, normalised, loose = _index()
    if squashed in exact:
        return exact[squashed]
    normed = _normed(name)
    if normed in normalised:
        return normalised[normed]
    words = _words(name)
    for end in range(len(words) - 1, 0, -1):
        key = loose.get(''.join(words[:end]))
        if key:
            return key
    return None


def identity(name):
    """One token per carrier, for grouping quotes and rows: the key when the name matches, else 'n:' and the normalised
    squashed name, so "VSP" and "VSP Inc." are one carrier; '' for a blank name or "Unknown carrier"."""
    key = match(name)
    if key:
        return key
    squashed = _squash(norm(name)) or _squash(name)
    if not squashed or squashed == _squash(UNKNOWN_CARRIER):
        return ''
    return f'n:{squashed}'[:IDENTITY_LIMIT]


def display_name(name):
    """The registry's spelling for a matched carrier, else the name as given."""
    key = match(name)
    return BY_KEY[key]['name'] if key else str(name or '').strip()


def _and_pieces(piece):
    """"Delta Dental and VSP" is two names; "Morgan White Group & Co." is one (a part made only of corporate words
    means the "and" belonged to the name)."""

    def is_name(part):
        return any(word not in SUFFIXES for word in _words(part))

    parts = [part.strip() for part in _AND.split(piece)]
    return parts if len(parts) > 1 and all(is_name(part) for part in parts) else [piece]


def split_names(text):
    """A free-text box of carriers ("Also please quote") as names (K104): split on commas, semicolons, slashes and new
    lines, and on a spaced "and" or "&" between names; each name at most 60 characters; repeats of one carrier go."""
    names, seen = [], set()
    for chunk in _SPLIT.split(str(text or '')):
        for piece in _and_pieces(chunk.strip()):
            name = piece.strip()[:NAME_LIMIT]
            token = identity(name)
            if name and token and token not in seen:
                seen.add(token)
                names.append(name)
    return names
