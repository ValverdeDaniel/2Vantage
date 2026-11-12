"""What may differ by design on both sides, hidden before comparing (Q.5): dates, version and Draft stamps, ids and
authors. Applied to old and new alike, so a masked word still has to sit in the same place on both.

- Dates: "January 1, 2027", "Jan 1, 2027", "1/1/2027", "2027-01-01", "November 2026" read <date>. A year alone is
  kept: "2027 Benefits Proposal" is the plan year, not a stamp.
- Draft and version stamps: "Draft for review, not for clients", "DRAFT", "-DRAFT", "Draft" and "Version 2" are taken
  out, with the " · " before them (OQ35: every file not issued is a draft, where the old app marked only some and
  numbered versions; B9), so a stamp one file has and the other has not is no difference.
- Ids: "case 14", "#135", "deal 90" read <id>.
- Authors: document properties (creator, last modified by, company) are not compared at all.
"""

import re

_MONTHS = (
    'January|February|March|April|May|June|July|August|September|October|November|December'
    '|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec'
)
_DATES = (
    re.compile(rf'\b(?:{_MONTHS})\.? \d{{1,2}}(?:st|nd|rd|th)?,? \d{{4}}\b'),
    re.compile(rf'\b\d{{1,2}} (?:{_MONTHS}) \d{{4}}\b'),
    re.compile(rf'\b(?:{_MONTHS}) \d{{4}}\b'),
    re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'),
    re.compile(r'\b\d{4}-\d{2}-\d{2}(?:[T ][\d:.]+(?:Z|[+-]\d{2}:?\d{2})?)?\b'),
)
# A stamp is taken out with the " · " that joins it to the words before it ("… · Prepared <date> · Version 1").
_SEP = r'(?:\s*·)?\s*'
_STAMPS = (
    re.compile(_SEP + r'Draft for review, not for clients', re.I),
    re.compile(_SEP + r'\bVersion \d+\b', re.I),
    re.compile(r'-?\bDRAFT\b'),
    re.compile(_SEP + r'\bDraft\b'),
)
_IDS = re.compile(r'\b(?:case|deal) #?\d+\b|#\d{2,}\b', re.I)


def text(value):
    """`value` with its dates, stamps and ids masked; non-text comes back as it was."""
    if not isinstance(value, str):
        return value
    out = value
    for pattern in _DATES:
        out = pattern.sub('<date>', out)
    for pattern in _STAMPS:
        out = pattern.sub('', out)
    out = _IDS.sub('<id>', out)
    return out


def line(value):
    """One line of text, masked, with its spaces collapsed."""
    return ' '.join(text(str(value or '')).split())
