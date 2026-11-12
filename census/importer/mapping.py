"""Proposing and checking a column mapping (plan.md §5.3.2 steps 4–5; C14, C15). Pure.

The offline mapper of old Vantage 891f1b3 `market/census_reader.py` (`heuristic_mapping`, `_positional_hint`), with
§4.8's addition that a column's label is an exact synonym too. Columns are read left to right, and each census key is
used by one column only, the first to claim it:
- a bare effective-date header takes its line from the column before it, at 0.70 (under 0.85 on purpose: checked);
- exact: the normalized header is the key's words, its label or a synonym, at 0.95;
- fuzzy: among unused keys (a line's key only when the header names the line), the synonym or key sharing the most
  words with the header, with at most one word beyond the overlap, at 0.60;
- else unmapped. `low` = mapped below 0.85; the dialog highlights it.
A mapping entry: {column, header, field ('' = ignore), confidence, low}. Sample values are never part of it.
"""

from .. import fields
from .words import (
    BARE_EFFECTIVE_HEADERS,
    EXACT,
    FUZZY,
    HEADER_SYNONYMS,
    LINE_TOKENS,
    LOW_BELOW,
    POSITIONAL,
    PRECEDING_LINE_EFFECTIVE,
    norm_header,
)

TWICE = '{label} is mapped to two columns. Map each census column once.'
UNKNOWN = 'Unknown census column.'


def _exact_words(key):
    return {key.replace('_', ' '), norm_header(fields.label(key)), *HEADER_SYNONYMS.get(key, [])}


_EXACT = {key: _exact_words(key) for key in HEADER_SYNONYMS}


def _line_token(key):
    return next((token for token in LINE_TOKENS if token in key), '')


def _positional(headers, column):
    """A bare 'Effective Date' takes its line from the column just before it (§4.8)."""
    if norm_header(headers[column]) not in BARE_EFFECTIVE_HEADERS:
        return ''
    for before in range(column - 1, -1, -1):
        words = norm_header(headers[before])
        if not words:
            continue
        return next((key for phrase, key in PRECEDING_LINE_EFFECTIVE if phrase in words), '')
    return ''


def _fuzzy(words, used):
    tokens = set(words.split())
    best, found = 0, ''
    for key, synonyms in HEADER_SYNONYMS.items():
        if key in used:
            continue
        token = _line_token(key)
        if token and token not in tokens:
            continue
        for synonym in [*synonyms, key.replace('_', ' ')]:
            overlap = len(tokens & set(synonym.split()))
            if overlap > best and len(synonym.split()) <= overlap + 1:
                best, found = overlap, key
    return found


def entry(column, header, field, confidence):
    return {
        'column': column,
        'header': header,
        'field': field,
        'confidence': confidence if field else 0.0,
        'low': bool(field) and confidence < LOW_BELOW,
    }


def propose(headers):
    """The proposed mapping of every column, left to right."""
    used, mapping = set(), []
    for column, header in enumerate(headers):
        words = norm_header(header)
        field, confidence = '', 0.0
        if words:
            hinted = _positional(headers, column)
            if hinted and hinted not in used:
                field, confidence = hinted, POSITIONAL
            if not field:
                field = next((key for key in HEADER_SYNONYMS if key not in used and words in _EXACT[key]), '')
                confidence = EXACT if field else 0.0
            if not field:
                field = _fuzzy(words, used)
                confidence = FUZZY if field else 0.0
        if field:
            used.add(field)
        mapping.append(entry(column, header, field, confidence))
    return mapping


def confirm(current, changes):
    """The mapping after the member's choices `changes` ([{column, field}]; '' ignores a column). A changed column is
    the member's choice: confidence 1, not low. Returns (mapping, errors) — errors {column: [sentence]} for an unknown
    key or a key on two columns (§5.3.2 step 5)."""
    mapping = [dict(item) for item in current]
    errors = {}
    for change in changes:
        column, field = change['column'], change['field']
        if field and field not in fields.BY_KEY:
            errors.setdefault(str(column), []).append(UNKNOWN)
            continue
        if mapping[column]['field'] != field:
            mapping[column] = entry(column, mapping[column]['header'], field, 1.0)
    seen = {}
    for item in mapping:
        if item['field'] and item['field'] in seen:
            errors.setdefault(str(item['column']), []).append(TWICE.format(label=fields.label(item['field'])))
        seen.setdefault(item['field'], item['column'])
    return mapping, errors
