"""Does any formula on a patched sheet read a column we wrote into? (old `xlsx_fill.formulas_touch` 891f1b3; K90.)

The recalculation flag is set only then: UHC's 14,350 enrollment formulas cache an empty value and would read blank
until a recalculation. Shared-formula masters are read (their children carry no body) and a master's relative column
references are widened across the span it is shared over. Only this sheet's own formulas count: Aetna's five hidden
output sheets reference Census Input thousands of times and are already `#REF!` in Warner's copy, so waking them
would only add a save prompt.
"""

import re

from .refs import col_index

_F_RE = re.compile(r'<f\b([^>]*)>(.*?)</f>', re.S)
_STRING_LIT_RE = re.compile(r'"[^"]*"')
_ERROR_LIT_RE = re.compile(r'#[A-Z0-9/]+[!?]?')
_SHEET_REF_RE = re.compile(r"(?:'((?:[^']|'')+)'|([A-Za-z0-9_.]+))!")
_CELL_TOKEN_RE = re.compile(
    r'(?<![A-Za-z0-9_.$#])(\$?)([A-Z]{1,3})(\$?\d+)?(?::(\$?)([A-Z]{1,3})\$?\d*)?(?![A-Za-z0-9_(])'
)


def _own_references(body, sheet_name):
    """The formula text with string and error literals gone, references into other sheets dropped and this sheet's
    qualifier removed."""
    text = _ERROR_LIT_RE.sub('', _STRING_LIT_RE.sub('""', body))

    def qualify(found):
        name = found.group(1) or found.group(2) or ''
        return '' if name.replace("''", "'") == sheet_name else '\x00'

    text = _SHEET_REF_RE.sub(qualify, text)
    return re.sub(r'\x00\$?[A-Z]{1,3}\$?\d*(?::\$?[A-Z]{1,3}\$?\d*)?', '', text)


def touches(sheet_xml, sheet_name, written_cols):
    """True when a formula on this sheet reads one of `written_cols` (column indexes)."""
    if not written_cols:
        return False
    written = set(written_cols)
    for match in _F_RE.finditer(sheet_xml):
        attrs, body = match.group(1), match.group(2)
        if not body.strip():
            continue
        if '[' in _STRING_LIT_RE.sub('""', body):
            return True  # a structured or external reference: assume yes
        text = _own_references(body, sheet_name)
        span = re.search(r'\bref="([A-Z]+)\d*(?::([A-Z]+)\d*)?"', attrs)
        width = col_index(span.group(2)) - col_index(span.group(1)) if span and span.group(2) else 0
        for token in _CELL_TOKEN_RE.finditer(text):
            absolute, start, end = token.group(1), token.group(2), token.group(5)
            lo = col_index(start)
            hi = col_index(end) if end else lo
            if not absolute and width:
                hi += width
            if written & set(range(min(lo, hi), max(lo, hi) + 1)):
                return True
    return False
