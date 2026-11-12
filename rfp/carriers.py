"""What an RFP needs to know about each carrier (plan.md §4.7; K23, K24, K105). A data module.

Generated on 2026-11-12 from old Vantage at commit 891f1b3, `benefits/market/rfp_carriers.py` (its literals read, never
imported), under the keys of `deals/carriers.py`, which holds each carrier's name, group and aliases and the matcher.
A test proves the two lists hold the same carriers (K105). Here: the Warner form columns offered at each size band
(`small`, `large`; an empty tuple means the form does not list the carrier at that size), the carrier's own census
format ('' = it takes Warner's universal census; the formats themselves arrive with slice 45), `on_form` (Trustmark
rides the form's "Additional carriers" line) and the old note, shown as the chip's tooltip.

Reps: each carrier's rep, who would fill a direct draft's To line, is not known (OQ59, default: the 25 carriers on
Warner's forms, the To line left blank). Eligibility here advises and never gates: Warner's own documents disagree
about sizes (K23, K24).
"""

from deals import lines

# Where a deal shopped through Warner goes: one email to their quoting inbox, which forwards the request (§4.7).
WARNER_QUOTING_EMAIL = 'FLQuoting@WarnerPacific.com'

# A Warner form column → the lines of ours it covers (§4.7). The only place that translation lives.
COLUMN_LINES = {
    'medical': ('medical',),
    'dental': ('dental',),
    'vision': ('vision',),
    'life_add': ('basic_life_add', 'voluntary_life'),
    'std': ('std', 'voluntary_std'),
    'ltd': ('ltd', 'voluntary_ltd'),
    'std_ltd': ('std', 'ltd', 'voluntary_std', 'voluntary_ltd'),  # the ancillary grid pairs disability in one box
    'acc_ci_hi': ('accident', 'critical_illness', 'hospital'),
    'gap': ('gap',),
}

_MED_ALL = ('medical', 'dental', 'vision', 'life_add', 'std', 'ltd')
_MED_MDV = ('medical', 'dental', 'vision')
_ANC_FULL = ('dental', 'vision', 'life_add', 'std_ltd', 'acc_ci_hi')
_MED = ('medical',)
_GAP = ('gap',)


def _carrier(small, large, census_format='', note='', on_form=True):
    return {'small': small, 'large': large, 'census_format': census_format, 'note': note, 'on_form': on_form}


ATTRIBUTES = {
    'aetna': _carrier(_MED_MDV, _MED_MDV, 'aetna_gateway', 'Its own census file (Aetna Gateway, 2–300 per Warner).'),
    'angle_health': _carrier(_MED, _MED, 'angle', 'Its own census file, uploaded to their portal as a CSV.'),
    'avmed': _carrier(_MED, _MED, note='Needs a signed 51+ questionnaire; accepts the Warner form.'),
    'cigna': _carrier(_MED_MDV, _MED_MDV, note="Wants each member's current plan election on the census."),
    'curative': _carrier((), _MED, note='51+ only.'),
    'florida_blue': _carrier(
        ('medical', 'dental', 'vision', 'life_add'),
        ('medical', 'dental', 'vision', 'life_add'),
        note='The one carrier that requires its OWN medical questionnaire.',
    ),
    'gravie': _carrier(_MED, _MED, note="Wants each member's current plan election on the census."),
    'nationwide': _carrier(_MED_ALL, _MED_ALL),
    'optimyl': _carrier(_MED, _MED),
    'sidecar_health': _carrier((), _MED, note='51+ only.'),
    'trustmark': _carrier(
        _MED, _MED, note='Not printed on the Warner matrix — rides the "Additional Carriers" line.', on_form=False
    ),
    'unitedhealthcare': _carrier(_MED_ALL, _MED_ALL, 'uhc', 'Its own census file (group info tab + quote columns).'),
    'guardian': _carrier(_ANC_FULL, _ANC_FULL),
    'the_hartford': _carrier(('life_add', 'std_ltd', 'acc_ci_hi'), ('life_add', 'std_ltd', 'acc_ci_hi')),
    'humana': _carrier(('dental', 'vision', 'life_add', 'std_ltd'), ('dental', 'vision', 'life_add', 'std_ltd')),
    'metlife': _carrier(_ANC_FULL, _ANC_FULL),
    'mutual_of_omaha': _carrier(_ANC_FULL, _ANC_FULL),
    'principal': _carrier(_ANC_FULL, _ANC_FULL),
    'sun_life': _carrier(_ANC_FULL, _ANC_FULL),
    'united_concordia': _carrier(('dental', 'vision'), ('dental', 'vision')),
    'unum': _carrier(_ANC_FULL, _ANC_FULL),
    'apl': _carrier(_GAP, _GAP),
    'morgan_white_group': _carrier(_GAP, _GAP),
    'transamerica': _carrier(_GAP, _GAP),
    'wellfleet': _carrier(_GAP, _GAP),
}


def columns_for(key, band):
    """The Warner form columns a carrier is offered at a size band ('small' or 'large')."""
    return ATTRIBUTES[key]['large' if band == 'large' else 'small']


def lines_for(key, band):
    """Our line keys, in `deals/lines.py` order, a carrier can quote at a band."""
    covered = {line for column in columns_for(key, band) for line in COLUMN_LINES[column]}
    return [line for line in lines.LINE_KEYS if line in covered]


def meta():
    """/api/meta/ `rfp.carriers`: what a chip needs beyond deals' name and group, keyed like `deals/carriers.py`."""
    return [
        {
            'key': key,
            'census_format': found['census_format'],
            'on_form': found['on_form'],
            'note': found['note'],
            'small': list(found['small']),
            'large': list(found['large']),
        }
        for key, found in ATTRIBUTES.items()
    ]
