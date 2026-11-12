"""What a formula in the client spreadsheet may say (plan.md §9.4; J147, J153; old `presentation_styles` at 891f1b3).

A formula is ours only: a template built in code, held to a closed grammar, never text a person or a carrier typed.
- The line, Cover and Markets Checked tabs: IF, OR, AND, SUM and ROUND, references on the same sheet, numbers, the
  empty string `""` and `= <> < > <= >= + - * /`. That refuses a string literal, `&`, `!`, a quote, any sheet
  reference and any other function by construction.
- With `sheets` (the file's own tab titles: the Compare, Composite Rates and All Plans tabs) it also takes INDEX,
  MATCH, IFERROR, MIN, MAX and HYPERLINK (whose address and words are always cells), N and COUNT (the stop-loss
  workbook's blank-as-zero and "any laser typed" guards, slice 36), and a quoted reference to one of those tabs. A tab
  outside `sheets` is refused.
- A conditional fill's condition: references, AND, the comparisons and `""`, nothing else.
There is no SUMPRODUCT: a what-if count on an unrated tier falls back to the stated premium or blank (J.5 B33).
"""

import re

_FORMULA_TOKEN = re.compile(
    r'\s+'
    r'|(?:IF|OR|AND|SUM|ROUND)\('
    r'|\$?[A-Z]{1,3}\$?[0-9]+(?::\$?[A-Z]{1,3}\$?[0-9]+)?(?![A-Z0-9(])'
    r'|[0-9]+(?:\.[0-9]+)?'
    r'|(?<!")""(?!")'
    r'|<>|<=|>=|[=<>+\-*/,()]'
)
_LOOKUP_FUNCTION = re.compile(r'(?:INDEX|MATCH|IFERROR|MIN|MAX|HYPERLINK|N|COUNT)\(')
_SHEET_PREFIX = re.compile(r"'((?:[^']|'')+)'!(?=\$?[A-Z]{1,3}\$?[0-9]+)")
_CONDITION_TOKEN = re.compile(r'\s+|AND\(|\$?[A-Z]{1,3}\$?[0-9]+(?![A-Z0-9(])|(?<!")""(?!")|<>|[=,()]')
_VALIDATION_SOURCE = re.compile(r"'((?:[^']|'')+)'!\$([A-Z]{1,3})\$([0-9]+):\$([A-Z]{1,3})\$([0-9]+)")
MAX_LENGTH = 8192
FUNCTIONS = ('IF', 'OR', 'AND', 'SUM', 'ROUND', 'INDEX', 'MATCH', 'IFERROR', 'MIN', 'MAX', 'HYPERLINK', 'N', 'COUNT')


class Refused(ValueError):
    """A formula, condition or drop-down source outside the closed grammar: a bug in the caller, never a client's."""


def sheet_ref(title):
    """The prefix that names a tab in a formula: `'Medical All Plans'!`, a quote in the title doubled."""
    return "'" + str(title).replace("'", "''") + "'!"


def check(template, sheets=None):
    """Raise `Refused` unless `template` is a formula of ours (the module docstring)."""
    if not isinstance(template, str) or not template.startswith('=') or len(template) < 2:
        raise Refused(f'a formula template starts with "=": {template!r}')
    if len(template) >= MAX_LENGTH:
        raise Refused('formula template too long')
    allowed = frozenset(sheets or ())
    depth, position = 0, 1
    while position < len(template):
        match = _FORMULA_TOKEN.match(template, position)
        if match is None and allowed:
            match = _LOOKUP_FUNCTION.match(template, position)
            if match is None:
                match = _SHEET_PREFIX.match(template, position)
                if match is not None and match.group(1).replace("''", "'") not in allowed:
                    raise Refused(f'formula names a tab outside the workbook: {template!r}')
        if match is None:
            raise Refused(f'formula template refused at {position}: {template[position : position + 24]!r}')
        token = match.group()
        if token.endswith('('):
            depth += 1
        elif token == ')':
            depth -= 1
            if depth < 0:
                raise Refused(f'unbalanced ")" in {template!r}')
        position = match.end()
    if depth:
        raise Refused(f'unbalanced "(" in {template!r}')


def check_condition(condition):
    position = 0
    while position < len(condition):
        match = _CONDITION_TOKEN.match(condition, position)
        if match is None:
            raise Refused(f'condition refused at {position}: {condition!r}')
        position = match.end()


def validation_source(sheet, column, first_row, last_row):
    """A drop-down's list: one column of one tab of this workbook, a direct range (never OFFSET or a name)."""
    source = f'{sheet_ref(sheet)}${column}${int(first_row)}:${column}${int(last_row)}'
    match = _VALIDATION_SOURCE.fullmatch(source)
    if match is None or match.group(2) != match.group(4) or int(first_row) > int(last_row):
        raise Refused(f'a drop-down reads one column of one tab: {source!r}')
    return source
