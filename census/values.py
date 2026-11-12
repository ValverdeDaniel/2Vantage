"""Storing a census value (plan.md §5.3.1; C16). Pure.

Every value is stored as text after `clean`; an empty value removes the key. What cannot be read is kept as typed, so
validation (§5.3.4) can say why. The same cleaning serves an import, a hand edit (slice 41) and a client's answer.
"""

import re
from datetime import date

from intake.values import parse_date as _parse_date

from . import fields
from .importer.words import is_waiver, tier_code

LIMIT = 300  # a value longer than this is cut: a cell, not a document
SSN_MASK = re.compile(r'^\s*[•*xX#]{3}[\s-]?[•*xX#]{2}[\s-]?(\d{4})\s*$')
_TIME = re.compile(r'\s+\d{1,2}:\d{2}(:\d{2})?$')
_NUMBER = re.compile(r'^-?\d+(\.\d+)?$')


def digits(value):
    return re.sub(r'\D', '', str(value or ''))


def parse_date(value):
    """A date from common written forms, month-first when ambiguous, else None. A trailing time is ignored."""
    return _parse_date(_TIME.sub('', str(value or '').strip()))


def masked_last4(value):
    """The last four digits of a masked SSN ('***-**-1234', 'XXX-XX-1234', '•••-••-1234'), else None."""
    match = SSN_MASK.match(str(value or ''))
    return match.group(1) if match else None


def mask_ssn(value):
    """What a screen shows instead of an SSN: its last four (OQ16). Blank stays blank."""
    text = str(value or '').strip()
    if not text:
        return ''
    found = digits(text)
    return '***-**-' + (found[-4:] if found else '****')


def _tier(text):
    code = tier_code(text)
    if code:
        return code
    return fields.WAIVED if is_waiver(text) else text


def _date(text):
    parsed = parse_date(text)
    return parsed.isoformat() if parsed else text


def _ssn(text):
    found = digits(text)
    return f'{found[:3]}-{found[3:5]}-{found[5:]}' if len(found) == 9 else text


def _number(text):
    plain = text.replace('$', '').replace(',', '').strip()
    return plain if _NUMBER.match(plain) else text


def _gender(text):
    first = text[:1].upper()
    return first if first in ('M', 'F') else text


def _zip(text):
    if re.fullmatch(r'\d{4}', text):
        return '0' + text
    if re.fullmatch(r'\d{5}', text):
        return text
    if re.fullmatch(r'\d{5}-?\d{4}', text):
        found = digits(text)
        return f'{found[:5]}-{found[5:]}'
    return text


_BY_TYPE = {'tier': _tier, 'date': _date, 'ssn': _ssn, 'money': _number, 'number': _number}
_BY_KEY = {'gender': _gender, 'zip': _zip, 'state': str.upper, 'work_state': str.upper}


def clean(key, raw):
    """The stored text of `raw` for census column `key` (§5.3.1); '' means no value."""
    text = str(raw if raw is not None else '').strip()[:LIMIT].strip()
    if not text:
        return ''
    if key in _BY_KEY:
        return _BY_KEY[key](text)
    cleaner = _BY_TYPE.get(fields.BY_KEY[key]['type'])
    return cleaner(text) if cleaner else text


def age_on(born, on):
    """Whole years from `born` to `on` (dates), or None when either is missing."""
    if not isinstance(born, date) or not isinstance(on, date):
        return None
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))
