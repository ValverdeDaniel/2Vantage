"""The fills a tab's conditional formats give its cells now (plan.md §9.4; J116; old
`workbook_preview._conditional_fills` at 891f1b3): the Compare tab lights the column whose pick is a base, amber for
the renewal, green for the current.

A condition is the closed grammar `grammar.check_condition` admits: AND of comparisons (= or <>) between references and
`""`, each reference relative to the range's top-left cell unless `$` pins it. It is read against the cells' stored
values, as Excel reads it: text compares without case, an empty cell equals "". The first rule that holds wins, as
the writer marks each `stop_if_true`. Pure.
"""

import re

from .workbook_checks import value_of

_TOKEN = re.compile(r'\s+|AND\(|(\$?)([A-Z]{1,3})(\$?)([0-9]+)|""|<>|=|,|\)')


def _col_number(letters):
    number = 0
    for ch in letters:
        number = number * 26 + ord(ch) - 64
    return number


def _tokens(condition):
    position, out = 0, []
    while position < len(condition):
        match = _TOKEN.match(condition, position)
        if match is None:
            raise ValueError(f'condition outside the grammar: {condition!r}')
        token = match.group()
        if match.group(2):
            col_fixed, letters, row_fixed, row = match.groups()
            out.append(('ref', bool(col_fixed), _col_number(letters), bool(row_fixed), int(row)))
        elif not token.isspace():
            out.append((token,))
        position = match.end()
    return out


def _comparisons(condition):
    """[(left operand, operator, right operand)], an operand a ('ref', …) token or ('""',)."""
    tokens = [token for token in _tokens(condition) if token[0] not in ('AND(', ',', ')')]
    if len(tokens) % 3:
        raise ValueError(f'condition outside the grammar: {condition!r}')
    return [tuple(tokens[i : i + 3]) for i in range(0, len(tokens), 3)]


def _plain(value):
    if value is None:
        return ''
    return value.casefold() if isinstance(value, str) else value


def _operand(sheet, token, offset):
    if token[0] != 'ref':
        return ''
    _kind, col_fixed, col, row_fixed, row = token
    row += 0 if row_fixed else offset[0]
    col += 0 if col_fixed else offset[1]
    return _plain(value_of(sheet.get(row, col)))


def _same(a, b):
    if isinstance(a, str) or isinstance(b, str):
        return isinstance(a, str) and isinstance(b, str) and a == b
    return a == b


def holds(sheet, condition, anchor, cell):
    """Whether `condition`, written for the range whose top-left is `anchor`, holds at `cell` ((row, col), 1-based)."""
    offset = (cell[0] - anchor[0], cell[1] - anchor[1])
    for left, operator, right in _comparisons(condition):
        a, b = _operand(sheet, left, offset), _operand(sheet, right, offset)
        if (operator[0] == '=') != _same(a, b):
            return False
    return True


def conditional_fills(sheet):
    """{(row, col): '#RRGGBB'} (1-based): each highlighted cell's fill now, the first rule that holds winning."""
    fills = {}
    for rule in sheet.highlights:
        r1, c1, r2, c2 = rule['cells']
        colour = rule['style'].get('bg_color')
        for row in range(r1, r2 + 1):
            for col in range(c1, c2 + 1):
                if (row, col) not in fills and colour and holds(sheet, rule['condition'], (r1, c1), (row, col)):
                    fills[(row, col)] = colour.upper()
    return fills
