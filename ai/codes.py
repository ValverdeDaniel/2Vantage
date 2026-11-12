"""A plan's carrier codes, folded to one set: part of its identity for re-reads and SBCs (F143, D-149; the old
benefits/pipeline/plan_codes.py at 891f1b3). Pure; it lives left of quotes so every reader, the finder and the SBC
match share one rule.

Carriers print the same plan under different names on different pages, and only its group number ties them:
"108114-00, 01" and "108114-00 / 108114-01" are one set {108114-00, 108114-01}. A short code never names a plan on
its own (Blue Cross reissues a plan under the same four digits, D-049): only strong codes match.
"""

import re

_LABEL_WORDS = re.compile(
    r'\b(?:group|grp|number|numbers|no|nos|plan|plans|id|ids|code|codes|active|cobra|lead|product|contract|benefit'
    r'|option|s)\b\.?',
    re.IGNORECASE,
)
_SEPARATORS = re.compile(r'[,;/&\n]|\band\b', re.IGNORECASE)
_CODE = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9.\-]*[A-Za-z0-9])?')
_SUFFIX = re.compile(r'^-?(\d{1,3})$')
NOT_A_NUMBER = {'tbd', 'tba', 'pending', 'none', 'null', 'unknown', 'na', 'nan', 'varies', 'n/a'}


def _clean(token):
    return _LABEL_WORDS.sub(' ', token or '').replace('(', ' ').replace(')', ' ')


def parse(text):
    """Every code in `text`, in order, upper case. A bare short suffix after a full code continues it: in
    "108114-00, 01" the "01" replaces the last dash segment. A token with no digit, or under 3 characters, is none."""
    out = []
    for part in _SEPARATORS.split(str(text or '')):
        part = _clean(part).strip()
        if not part:
            continue
        suffix = _SUFFIX.match(part.replace(' ', ''))
        if suffix and out:
            previous, digits = out[-1], suffix.group(1)
            if '-' in previous:
                head, tail = previous.rsplit('-', 1)
                code = f'{head}-{digits.zfill(len(tail))}'
            elif previous[-len(digits) :].isdigit() and len(previous) > len(digits):
                code = previous[: -len(digits)] + digits
            else:
                code = ''
            if code and code not in out:
                out.append(code)
            continue
        for match in _CODE.finditer(part):
            code = match.group(0).upper()
            if re.search(r'\d', code) and len(code) >= 3 and code not in out:
                out.append(code)
    return out


def as_list(values):
    """Codes from a list of printed texts (or one text), canonical and sorted: what `Plan.codes` stores."""
    if isinstance(values, str):
        values = [values]
    found = set()
    for value in values or ():
        found.update(parse(value))
    return sorted(found)


def is_strong(code):
    """Letters and digits together and six or more characters; a dashed group code with six or more digits; or eight
    or more digits. '5906' never is."""
    code = str(code or '').upper()
    digits = sum(c.isdigit() for c in code)
    letters = sum(c.isalpha() for c in code)
    if letters and digits and len(code) >= 6:
        return True
    if '-' in code and digits >= 6:
        return True
    return digits >= 8


def key(code):
    """A code without punctuation: "108114-06" and "10811406" are one code."""
    return re.sub(r'[^A-Z0-9]', '', str(code or '').upper())


def strong(codes):
    if isinstance(codes, str):
        codes = parse(codes)
    return frozenset(key(code) for code in codes if is_strong(code))


def overlap(a, b):
    """Whether two code collections name the same plan: they share a strong code."""
    return bool(strong(a) & strong(b))


def number_parts(plan_number):
    """A plan number's halves ("05182 / 05183" -> {'05182', '05183'}), compacted; '' and "TBD" give none (D116)."""
    parts = set()
    for part in re.split(r'\s*/\s*|\s*,\s*', str(plan_number or '')):
        compact = re.sub(r'[^a-z0-9]', '', part.lower())
        if len(compact) >= 3 and compact not in NOT_A_NUMBER:
            parts.add(compact)
    return parts
