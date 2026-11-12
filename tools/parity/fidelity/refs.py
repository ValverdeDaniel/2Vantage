"""Cell references read through a row and column alignment, so an old formula, merge or print setting can be held
against the new one after rows or columns were added: old `=SUM(D14:D17)` reads `=SUM(D16:D19)` when two rows were
inserted above row 14. A reference to a row or column the new file does not have is left as it was.

`maps` is {sheet title: (row map, column map)}, each {old 1-based: new 1-based}.
"""

import re

from openpyxl.utils import column_index_from_string, get_column_letter

_REF = re.compile(
    r"(?P<sheet>'(?:[^']|'')+'!|[A-Za-z_][A-Za-z0-9_.]*!)?"
    r'(?P<c1>\$?)(?P<col>[A-Z]{1,3})(?P<r1>\$?)(?P<row>[0-9]+)(?![A-Za-z0-9(])'
    r'(?::(?P<c2>\$?)(?P<col2>[A-Z]{1,3})(?P<r2>\$?)(?P<row2>[0-9]+))?'
)
_STRING = re.compile(r'"(?:[^"]|"")*"')


def _sheet_of(prefix, here):
    if not prefix:
        return here
    name = prefix[:-1]
    return name[1:-1].replace("''", "'") if name.startswith("'") else name


def _cell(col, row, cmap, rmap):
    index = column_index_from_string(col)
    return get_column_letter(cmap.get(index, index)), rmap.get(int(row), int(row))


def translate(text, here, maps):
    """`text` (a formula, a range or a list of ranges) with each reference moved through `maps`."""
    if not isinstance(text, str):
        return text

    def one(match):
        sheet = _sheet_of(match.group('sheet'), here)
        rmap, cmap = maps.get(sheet, ({}, {}))
        col, row = _cell(match.group('col'), match.group('row'), cmap, rmap)
        out = f'{match.group("sheet") or ""}{match.group("c1")}{col}{match.group("r1")}{row}'
        if match.group('col2'):
            col2, row2 = _cell(match.group('col2'), match.group('row2'), cmap, rmap)
            out += f':{match.group("c2")}{col2}{match.group("r2")}{row2}'
        return out

    # Leave quoted strings alone: "EE Only" is no reference.
    pieces, last = [], 0
    for quoted in _STRING.finditer(text):
        pieces.append(_REF.sub(one, text[last : quoted.start()]))
        pieces.append(quoted.group())
        last = quoted.end()
    pieces.append(_REF.sub(one, text[last:]))
    return ''.join(pieces)


def rows_span(text, rmap):
    """'$4:$6' with its rows moved."""
    if not text:
        return text

    def one(match):
        return f'${rmap.get(int(match.group(1)), int(match.group(1)))}'

    return re.sub(r'\$([0-9]+)', one, str(text))


def cols_span(text, cmap):
    """'$A:$G' with its columns moved."""
    if not text:
        return text

    def one(match):
        index = column_index_from_string(match.group(1))
        return f'${get_column_letter(cmap.get(index, index))}'

    return re.sub(r'\$([A-Z]{1,3})', one, str(text))
