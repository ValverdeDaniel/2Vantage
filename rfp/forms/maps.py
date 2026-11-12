"""Warner Pacific's quote request forms: where each value goes (plan.md §9.9; K46, K99, K100). A data module.

`VARIANTS` is copied as is from old Vantage 891f1b3 `benefits/pipeline/quote_request_form.py` (plan.md Appendix A):
every input cell is paired with the LABEL cell beside it, so the drift guard (`forms.fill.verify`) proves the map still
matches the bundled workbook before a value is written. The three workbooks are Warner's own, bundled byte for byte in
`assets/forms/` and hash-checked against the SHA-256s of the old `templates_xlsx/README.md`.

- **Simplified** (12.9.25) is Warner's standard for every group size: the group header and the commission box only
  (K100: deliberate fidelity, no notes box is added).
- **Small group 2–50 / Large group 51+** (rev8.20.26) add the funding boxes (2–50 has no ASO box), the carrier × line
  matrix (a box only where the form has one), the Notes cell (wrap on, as Alt+Enter leaves it) and Additional Carriers.
- Each form carries Warner's census sheet; the "form + census" downloads print the roster inline (K42, K99), up to
  Warner's own 500-row counter.
"""

from pathlib import Path

FOLDER = Path(__file__).resolve().parents[2] / 'assets' / 'forms'
SHA256 = {
    'warner_qrf_simplified.xlsx': 'fb1d5b1c2499b5b325cc1bb431d9abe9c064675732e71c10c8ecb9a643d8b3ce',
    'warner_qrf_small_group.xlsx': '1d06a25c6c81f492bdbdd9137e14c171399389c03488c6193aad8a23110386cb',
    'warner_qrf_large_group.xlsx': '0a1d25d5716cf7cafcad04213cdf253852f6bdd1448f3f7645d18d4c395c704f',
}

SIMPLIFIED, SMALL_GROUP, LARGE_GROUP = 'simplified', 'small_group', 'large_group'

# Warner's medical grid, left to right; the ancillary grid pairs disability and bundles accident/CI/hospital.
MED_COLS = {'medical': 'D', 'dental': 'E', 'vision': 'F', 'life_add': 'G', 'std': 'H', 'ltd': 'I'}
ANC_COLS = {'dental': 'D', 'vision': 'E', 'life_add': 'F', 'std_ltd': 'G', 'acc_ci_hi': 'H', 'gap': 'I'}

# Warner's own row counter runs 1–500 beside the census grid (A7:A506 on the forms' census sheet, A32:A531 on the
# Simplified): a member past it would sit in an unnumbered row.
CENSUS_ROWS = 500

# The wrap a person's Alt+Enter turns on: the cell's own xf plus wrapText, nothing else changed.
WRAPPED = {'horizontal': 'left', 'vertical': 'top', 'wrapText': '1'}


def _header(sic, fein, years, carrier, funding, agency, commission):
    """(label cell, expected label prefix, input cell, fact key): the header the three forms share."""
    return [
        ('C6', 'Due Date', 'D6', 'deal.due_date'),
        ('C9', 'Group Name', 'D9', 'group.legal_name'),
        ('C10', 'Group Address', 'D10', 'group.address_street'),
        ('C11', 'City, State & Zip', 'D11', 'group.city_state_zip'),
        ('C12', 'Additional Locations', 'D12', 'group.locations'),
        ('C13', 'ATNE', 'D13', 'group.atne'),
        ('F13', 'Nature of Business', sic, 'group.sic'),
        ('C14', 'FTE', 'D14', 'group.fte'),
        ('F14', 'Tax ID', fein, 'group.fein'),
        ('C15', 'Number of', 'D15', 'group.enrolled'),
        ('F15', 'No. of Years in Business', years, 'group.years_in_business'),
        ('C16', 'Number of', 'D16', 'group.waiving'),
        ('F16', 'Current Carrier', carrier, 'group.current_carrier'),
        ('F17', 'Current Funding Type', funding, 'group.current_funding'),
        ('C20', 'Agent / Broker Name', 'D20', 'broker.agent'),
        ('F20', 'Agency Name', agency, 'broker.agency'),
        ('C21', 'Broker Email Address', 'D21', 'broker.email'),
        ('C22', 'Address', 'D22', 'broker.address'),
        ('C23', 'City, State & Zip', 'D23', 'broker.city_state_zip'),
        ('C24', 'Broker of Record', 'D24', 'broker.is_bor'),
        ('F24', 'Commission Request', commission, 'broker.commission'),
    ]


_FORM_CENSUS = {
    'sheet': 'Census Template',
    'header_row': 3,
    'data_row': 7,
    'origin_col': 'B',
    'clear': ['A5:X6'],
    'max_rows': CENSUS_ROWS,
}

VARIANTS = {
    SIMPLIFIED: {
        'label': 'Quote request form',
        'file': 'warner_qrf_simplified.xlsx',
        'sheet': 'Sheet1',
        'version': '12.9.25',
        'size_band': '',
        # H6 is the effective date on this form (F6:G6 is the label).
        'header': _header('I13', 'I14', 'I15', 'I16', 'I17', 'I20', 'I24')
        + [('F6', 'Effective Date', 'H6', 'deal.effective_date')],
        'funding_cells': {},
        'matrix': {},
        # This revision has no notes box, and none is added: the request summary rides the packet and the email.
        'notes': None,
        'additional_cell': '',
        'census': {
            'sheet': 'Sheet1',
            'header_row': 28,
            'data_row': 32,
            'origin_col': 'B',
            'clear': ['A30:X31'],
            'max_rows': CENSUS_ROWS,
        },
    },  # fmt: skip
    SMALL_GROUP: {
        'label': 'Small group quote request form (2–50)',
        'file': 'warner_qrf_small_group.xlsx',
        'sheet': 'RFP ',  # the trailing space is Warner's own sheet name
        'version': 'rev8.20.26',
        'size_band': 'small',
        'header': _header('H13', 'H14', 'H15', 'H16', 'H17', 'G20', 'H24')
        + [('G6', 'Effective Date', 'H6', 'deal.effective_date')],
        'funding_cells': {'fully_insured': 'E40', 'level_funded': 'G40'},
        'matrix': {
            'medical': {
                'rows': {
                    'aetna': 31,
                    'angle_health': 32,
                    'avmed': 33,
                    'cigna': 34,
                    'florida_blue': 35,
                    'gravie': 36,
                    'nationwide': 37,
                    'optimyl': 38,
                    'unitedhealthcare': 39,
                },
                'cols': MED_COLS,
            },
            'ancillary': {
                'rows': {
                    'guardian': 46,
                    'the_hartford': 47,
                    'humana': 48,
                    'metlife': 49,
                    'mutual_of_omaha': 50,
                    'principal': 51,
                    'sun_life': 52,
                    'united_concordia': 53,
                    'unum': 54,
                    'apl': 55,
                    'morgan_white_group': 56,
                    'transamerica': 57,
                    'wellfleet': 58,
                },
                'cols': ANC_COLS,
            },
        },
        # The label lives in the merge's own top-left cell, so the value carries it ("Notes: …").
        'notes': {'cell': 'C41', 'prefix': 'Notes: '},
        'additional_cell': 'C60',
        'additional_prefix': 'Additional Carriers: ',
        'census': _FORM_CENSUS,
    },  # fmt: skip
    LARGE_GROUP: {
        'label': 'Large group quote request form (51+)',
        'file': 'warner_qrf_large_group.xlsx',
        'sheet': 'RFP ',
        'version': 'rev8.20.26',
        'size_band': 'large',
        'header': _header('H13', 'H14', 'H15', 'H16', 'H17', 'G20', 'H24')
        + [
            ('G6', 'Effective Date', 'H6', 'deal.effective_date'),
            ('C17', 'Waiting Period', 'D17', 'group.waiting_period'),  # the one field the 51+ form adds
        ],
        # Not in column order: the caption text boxes pair F42 with ASO and G42 with Level Funded.
        'funding_cells': {'fully_insured': 'E42', 'aso': 'F42', 'level_funded': 'G42'},
        'matrix': {
            'medical': {
                'rows': {
                    'aetna': 31,
                    'angle_health': 32,
                    'avmed': 33,
                    'cigna': 34,
                    'curative': 35,
                    'florida_blue': 36,
                    'gravie': 37,
                    'nationwide': 38,
                    'optimyl': 39,
                    'sidecar_health': 40,
                    'unitedhealthcare': 41,
                },
                'cols': MED_COLS,
            },
            'ancillary': {
                'rows': {
                    'guardian': 48,
                    'the_hartford': 49,
                    'humana': 50,
                    'metlife': 51,
                    'mutual_of_omaha': 52,
                    'principal': 53,
                    'sun_life': 54,
                    'united_concordia': 55,
                    'unum': 56,
                    'apl': 57,
                    'morgan_white_group': 58,
                    'transamerica': 59,
                    'wellfleet': 60,
                },
                'cols': ANC_COLS,
            },
        },
        'notes': {'cell': 'C43', 'prefix': 'Notes: '},
        'additional_cell': 'C62',
        'additional_prefix': 'Additional Carriers: ',
        'census': _FORM_CENSUS,
    },  # fmt: skip
}

KEYS = tuple(VARIANTS)
# What `RfpRequest.form` stores for each variant: blank is the Simplified form, the default for every size.
STORED = {SIMPLIFIED: '', SMALL_GROUP: SMALL_GROUP, LARGE_GROUP: LARGE_GROUP}
# The file names the downloads take (`<Client> - Quote request form….xlsx`); no person's name ever.
NAME_PART = {SIMPLIFIED: '', SMALL_GROUP: ' - small group', LARGE_GROUP: ' - large group'}


def variant_of(stored):
    """The variant key a stored `form` value names ('' is the Simplified form)."""
    return stored if stored in VARIANTS else SIMPLIFIED


def options(band):
    """The packet's variant chips (K46): Simplified is the standard at every size; the size forms are dimmed where the
    band does not fit them, and stay pickable."""
    return [
        {
            'key': key,
            'label': spec['label'],
            'version': spec['version'],
            'recommended': key == SIMPLIFIED,
            'applicable': not spec['size_band'] or spec['size_band'] == band,
            'size': '2–50' if spec['size_band'] == 'small' else ('51+' if spec['size_band'] else ''),
        }
        for key, spec in VARIANTS.items()
    ]
