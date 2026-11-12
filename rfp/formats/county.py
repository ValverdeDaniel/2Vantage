"""Where a member lives, from the ZIP we already hold (plan.md §9.8 derived values; K92). Ported from old Vantage
891f1b3 `benefits/pipeline/geo.py`. Two questions, two mechanisms on purpose:

- **Inside the contiguous 48?** A prefix table, no data file: the first three digits already tell the lower 48 from
  Alaska, Hawaii, the territories and the military post offices. Used for UHC's "Out of Area" (`IN_AREA` or blank).
- **Which county?** The bundled crosswalk `assets/zip_county.csv.gz` (US Census Bureau 2020 ZCTA-to-county
  relationship file, public domain; 33,791 ZCTAs, each with its dominant county by land area; names verbatim, so
  "Orleans Parish"). A PO-box-only ZIP has no ZCTA and answers ''.
Both answer ''/None rather than a guess: a blank a producer can fill beats a wrong one nobody checks.
"""

import csv
import functools
import gzip
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / 'assets' / 'zip_county.csv.gz'

_DIGITS = re.compile(r'\d')
_EXACT = {'96799': 'AS'}  # American Samoa, inside Hawaii's 967 band: the only exact exception
# (first prefix, last prefix, what it is), inclusive, as text so a leading zero is never lost.
_NON_CONTINENTAL = (
    ('995', '999', 'AK'),
    ('967', '968', 'HI'),
    ('006', '007', 'PR'),
    ('008', '008', 'VI'),
    ('009', '009', 'PR'),
    ('969', '969', 'GU/MP'),
    ('090', '098', 'AE'),
    ('340', '340', 'AA'),
    ('962', '966', 'AP'),
)
TERRITORY_NAMES = {
    'AK': 'Alaska',
    'HI': 'Hawaii',
    'PR': 'Puerto Rico',
    'VI': 'the US Virgin Islands',
    'GU/MP': 'Guam or the Northern Marianas',
    'AS': 'American Samoa',
    'AE': 'a military address (AE)',
    'AA': 'a military address (AA)',
    'AP': 'a military address (AP)',
}


def territory_name(code):
    return TERRITORY_NAMES.get(code, code or '')


def zip5(value):
    """The first five digits of what was typed, or '' (a short value is not a ZIP we can reason about)."""
    digits = ''.join(_DIGITS.findall(str(value or '')))
    return digits[:5] if len(digits) >= 5 else ''


def territory_of(value):
    """'' for the contiguous 48 and DC, else what it is ('AK', 'HI', 'PR', …); None when the value is not a ZIP."""
    code = zip5(value)
    if not code:
        return None
    if code in _EXACT:
        return _EXACT[code]
    prefix = code[:3]
    for low, high, what in _NON_CONTINENTAL:
        if low <= prefix <= high:
            return what
    return ''


def in_area(value):
    """'IN_AREA' for the contiguous 48, else '': never an assertion about Alaska, Hawaii or a territory."""
    return 'IN_AREA' if territory_of(value) == '' else ''


@functools.lru_cache(maxsize=1)
def _crosswalk():
    """{zip5: (county, state)}, read once per process. A missing file answers '' for everything."""
    if not DATA.exists():
        return {}
    try:
        with gzip.open(DATA, 'rt', encoding='utf-8', newline='') as fh:
            return {row['zip5']: (row['county'], row['state']) for row in csv.DictReader(fh) if row.get('zip5')}
    except (OSError, csv.Error, KeyError):
        return {}


def county_for(value):
    """The county the Census records for this ZIP, or ''."""
    found = _crosswalk().get(zip5(value))
    return found[0] if found else ''
