"""The sheet model (plan.md §9.4; J.6.3; O.3.6): a pure picture of the client spreadsheet, written once by
`write.py` with XlsxWriter and read by the tests (and, from slice 28, the Export viewer) without opening a file.

A `Book` holds its `Sheet`s in tab order, the author and the tab it opens on. A `Sheet` holds, 1-based like Excel's
own addresses: cells, merges, column widths, row heights, frozen panes, an AutoFilter, drop-downs, conditional fills,
images, the zoom and the print setup. A cell is text, a number, a blank that only carries a style, or a formula with
its stored result: the result is the app's figure (quotes' math), so a viewer that does not calculate shows it too.
"""

from dataclasses import dataclass, field

TEXT, NUMBER, BLANK, FORMULA = 'text', 'number', 'blank', 'formula'


@dataclass
class Cell:
    kind: str
    value: object = None  # the text or number; for a formula, its template ("=…")
    result: object = None  # a formula's stored result: a number, a text, or '' for a blank
    style: dict = field(default_factory=dict)


@dataclass
class Sheet:
    title: str
    cells: dict = field(default_factory=dict)  # {(row, col): Cell}
    merges: list = field(default_factory=list)  # [(first row, first col, last row, last col)]
    widths: dict = field(default_factory=dict)  # {col: characters}
    heights: dict = field(default_factory=dict)  # {row: points}
    freeze: tuple | None = None  # (row, col) of the first cell that scrolls, as 'B7' is (7, 2)
    autofilter: tuple | None = None  # (first row, first col, last row, last col)
    validations: list = field(default_factory=list)  # [{'cells': (r1, c1, r2, c2), 'source', 'prompt'}]
    highlights: list = field(default_factory=list)  # [{'cells': (r1, c1, r2, c2), 'condition', 'style'}]
    images: list = field(default_factory=list)  # [{'row', 'col', 'data': bytes, 'width', 'height'}]
    zoom: int = 130
    print: dict = field(default_factory=dict)  # the print setup (print_plan.py)

    def put(self, row, col, cell):
        self.cells[(int(row), int(col))] = cell
        return cell

    def get(self, row, col):
        return self.cells.get((row, col))

    def merge(self, first_row, first_col, last_row, last_col):
        self.merges.append((first_row, first_col, last_row, last_col))

    def height(self, row):
        """The row's height in points: its own, else Excel's default."""
        return self.heights.get(row)

    def last_row(self):
        rows = [row for row, _col in self.cells] + list(self.heights)
        return max(rows) if rows else 1


@dataclass
class Book:
    sheets: list = field(default_factory=list)
    author: str = ''
    opens_on: int = 0  # the index of the tab the file opens on (the only one selected)

    def sheet(self, title):
        sheet = Sheet(title)
        self.sheets.append(sheet)
        return sheet

    def titles(self):
        return [sheet.title for sheet in self.sheets]

    def by_title(self, title):
        return next((sheet for sheet in self.sheets if sheet.title == title), None)


def column_letter(col):
    """1 → 'A', 27 → 'AA'."""
    letters = ''
    col = int(col)
    while col > 0:
        col, rest = divmod(col - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def ref(row, col, *, absolute_col=False, absolute_row=False):
    return f'{"$" if absolute_col else ""}{column_letter(col)}{"$" if absolute_row else ""}{row}'
