"""A test-only evaluator for the client spreadsheet's formulas (plan.md §9.4 "Correctness requirement", J.6.10; J119:
no evaluator ships, the sheet model holds each formula with its stored result).

`evaluate(book)` works out every formula cell of a `proposals.workbook.model.Book` from the written cell values, with
Excel's semantics for the closed list the grammar allows (IF, OR, AND, SUM, ROUND, INDEX, MATCH, IFERROR, MIN, MAX,
HYPERLINK; = <> < > <= >= + - * /; numbers; ""). A blank cell equals "" and 0 in a comparison and is 0 in arithmetic;
a number is less than any text; text compares case-insensitively; SUM, MIN and MAX skip text and blanks in references;
arithmetic on text is #VALUE!; INDEX returns the cell (a blank one still equals ""; as a formula's final value it
shows 0); MATCH(x, range, 0) is exact and case-insensitive (#N/A when absent); ROUND is half away from zero after
reading the float at 15 significant digits, as Excel's. Anything else raises: the evaluator is as closed as the grammar.
"""

import re

from proposals.workbook.model import BLANK as BLANK_KIND
from proposals.workbook.model import FORMULA, NUMBER, TEXT

from .sheet_functions import FUNCTIONS
from .sheet_values import BLANK, Err, Raise, Ref, arith, compare, number, round_excel, same, shown

__all__ = ['BLANK', 'Err', 'disagreements', 'evaluate', 'results', 'round_excel', 'same']

_TOKEN = re.compile(
    r"\s*(?:(?P<sheet>'(?:[^']|'')+'!)?(?P<ref>\$?[A-Z]{1,3}\$?[0-9]+(?::\$?[A-Z]{1,3}\$?[0-9]+)?)(?![A-Z0-9(])"
    r'|(?P<func>[A-Z]+)\('
    r'|(?P<num>[0-9]+(?:\.[0-9]+)?)'
    r'|(?P<str>"")'
    r'|(?P<op><>|<=|>=|[=<>+\-*/,()]))'
)
_CELL = re.compile(r'\$?([A-Z]{1,3})\$?([0-9]+)')


def _col(letters):
    out = 0
    for ch in letters:
        out = out * 26 + ord(ch) - 64
    return out


def _tokens(text):
    position, out = 0, []
    while position < len(text):
        if text[position:].strip() == '':
            break
        match = _TOKEN.match(text, position)
        if match is None:
            raise ValueError(f'cannot read {text[position : position + 24]!r} in {text!r}')
        kind = match.lastgroup if match.lastgroup != 'sheet' else 'ref'
        out.append((kind, match.group(kind), match.group('sheet')))
        position = match.end()
    return out


class Evaluator:
    def __init__(self, book):
        self.sheets = {sheet.title: sheet for sheet in book.sheets}
        self.memo, self.busy = {}, set()

    # -- cells ----------------------------------------------------------------------------------------------------
    def cell(self, title, row, col):
        key = (title, row, col)
        if key in self.memo:
            return self.memo[key]
        cell = self.sheets[title].get(row, col)
        if cell is None or cell.kind == BLANK_KIND:
            return BLANK
        if cell.kind == TEXT:
            return str(cell.value)
        if cell.kind == NUMBER:
            return float(cell.value)
        if cell.kind != FORMULA:
            raise ValueError(f'unknown cell kind {cell.kind}')
        if key in self.busy:
            raise ValueError(f'circular reference at {key}')
        self.busy.add(key)
        saved = (getattr(self, 'title', None), getattr(self, 'toks', None), getattr(self, 'pos', 0))
        try:
            value = self.formula(title, cell.value)
        finally:
            self.busy.discard(key)
            self.title, self.toks, self.pos = saved
        # Another cell reads a formula's shown value: a reference to a blank cell shows 0.
        self.memo[key] = 0.0 if value is BLANK else value
        return self.memo[key]

    def formula(self, title, text):
        self.title, self.toks, self.pos = title, _tokens(text[1:] if text.startswith('=') else text), 0
        try:
            value = self.value(self.expr())
        except Raise as raised:
            return raised.err
        if self.pos != len(self.toks):
            raise ValueError(f'trailing tokens in {text!r}')
        return value

    def value(self, item):
        """A reference read as one value (a blank stays BLANK)."""
        if isinstance(item, Ref):
            if not item.single():
                return Err('#VALUE!')
            return self.cell(item.sheet, item.r1, item.c1)
        return item

    # -- parsing (Excel's precedence: comparison < + - < * / < unary -) -------------------------------------------
    def peek(self):
        return self.toks[self.pos] if self.pos < len(self.toks) else (None, None, None)

    def take(self, expected=None):
        tok = self.peek()
        if expected is not None and tok[1] != expected:
            raise ValueError(f'expected {expected!r}, got {tok[1]!r}')
        self.pos += 1
        return tok

    def expr(self):
        left = self.additive()
        while self.peek()[0] == 'op' and self.peek()[1] in ('=', '<>', '<', '>', '<=', '>='):
            op = self.take()[1]
            left = compare(op, self.value(left), self.value(self.additive()))
        return left

    def additive(self):
        left = self.term()
        while self.peek()[1] in ('+', '-'):
            op = self.take()[1]
            left = arith(op, self.value(left), self.value(self.term()))
        return left

    def term(self):
        left = self.unary()
        while self.peek()[1] in ('*', '/'):
            op = self.take()[1]
            left = arith(op, self.value(left), self.value(self.unary()))
        return left

    def unary(self):
        if self.peek()[1] == '-':
            self.take()
            return arith('-', 0.0, self.value(self.unary()))
        return self.primary()

    def primary(self):
        kind, text, sheet = self.take()
        if kind == 'num':
            return float(text)
        if kind == 'str':
            return ''
        if kind == 'ref':
            title = sheet[1:-2].replace("''", "'") if sheet else self.title
            parts = [_CELL.fullmatch(part).groups() for part in text.split(':')]
            (c1, r1), (c2, r2) = parts[0], parts[-1]
            return Ref(title, int(r1), _col(c1), int(r2), _col(c2))
        if kind == 'func':
            return self.call(text)
        if text == '(':
            inner = self.expr()
            self.take(')')
            return inner
        raise ValueError(f'unexpected token {text!r}')

    def args(self):
        """Each argument as an unevaluated slice of tokens: IF and IFERROR evaluate only what they need."""
        spans, depth, start = [], 0, self.pos
        while True:
            tok = self.peek()
            if tok[0] is None:
                raise ValueError('unclosed call')
            if tok[1] == '(' or tok[0] == 'func':
                depth += 1
            elif tok[1] == ')':
                if depth == 0:
                    if self.pos > start:
                        spans.append((start, self.pos))
                    self.take()
                    return spans
                depth -= 1
            elif tok[1] == ',' and depth == 0:
                spans.append((start, self.pos))
                start = self.pos + 1
            self.pos += 1

    def run(self, span):
        saved = (self.toks, self.pos)
        self.pos = span[0]
        sub = self.toks[: span[1]]
        self.toks = sub
        try:
            result = self.expr()
        finally:
            self.toks, self.pos = saved
        return result

    def call(self, name):
        if name not in FUNCTIONS:
            raise ValueError(f'{name} is outside the closed list')
        return FUNCTIONS[name](self, self.args())

    def items(self, span):
        """An argument as the values a SUM, MIN or MAX reads: a reference's numbers only, or the value itself."""
        found = self.run(span)
        if isinstance(found, Ref):
            out = []
            for row, col in found.coords():
                value = self.cell(found.sheet, row, col)
                if isinstance(value, Err):
                    raise Raise(value)
                if isinstance(value, float):
                    out.append(value)
            return out
        found = self.value(found)
        if isinstance(found, Err):
            raise Raise(found)
        figure = number(found)
        if isinstance(figure, Err):
            raise Raise(figure)
        return [figure]


def evaluate(book):
    """{(sheet title, row, col): value} for every formula cell of `book`."""
    ev = Evaluator(book)
    out = {}
    for sheet in book.sheets:
        for (row, col), cell in sorted(sheet.cells.items()):
            if cell.kind == FORMULA:
                out[(sheet.title, row, col)] = shown(ev.cell(sheet.title, row, col))
    return out


def results(book):
    """{(sheet title, row, col): the stored result} for every formula cell of `book`."""
    return {
        (sheet.title, row, col): cell.result
        for sheet in book.sheets
        for (row, col), cell in sheet.cells.items()
        if cell.kind == FORMULA
    }


def disagreements(book):
    """[(sheet title, row, col, stored, evaluated)] where a stored result differs from the evaluated formula."""
    stored, found = results(book), evaluate(book)
    return [(*key, stored[key], found[key]) for key in sorted(stored) if not same(stored[key], found[key])]
