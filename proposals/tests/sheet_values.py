"""The values the test-only evaluator works with (sheet_eval.py): a blank cell, an error, a reference, and Excel's
rules for comparing, adding and rounding them (plan.md §9.4, J.6.10). A blank equals "" and 0 in a comparison and is 0
in arithmetic; a number is less than any text; text compares case-insensitively; arithmetic on text is #VALUE!; ROUND
is half away from zero after reading the float at 15 significant digits, as Excel's (and quotes' round_decimal)."""

import math
from decimal import ROUND_HALF_UP, Decimal


class _Blank:
    def __repr__(self):
        return 'BLANK'


BLANK = _Blank()


class Err:
    def __init__(self, code):
        self.code = code

    def __repr__(self):
        return self.code

    def __eq__(self, other):
        return isinstance(other, Err) and other.code == self.code

    def __hash__(self):
        return hash(self.code)


class Raise(Exception):
    def __init__(self, err):
        self.err = err


class Ref:
    def __init__(self, sheet, r1, c1, r2, c2):
        self.sheet, self.r1, self.c1, self.r2, self.c2 = sheet, r1, c1, r2, c2

    def single(self):
        return self.r1 == self.r2 and self.c1 == self.c2

    def coords(self):
        return [(r, c) for r in range(self.r1, self.r2 + 1) for c in range(self.c1, self.c2 + 1)]


def number(value):
    if value is BLANK:
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, float | int):
        return float(value)
    if isinstance(value, Err):
        return value
    return Err('#VALUE!')


def arith(op, a, b):
    for side in (a, b):
        if isinstance(side, Err):
            raise Raise(side)
    x, y = number(a), number(b)
    for side in (x, y):
        if isinstance(side, Err):
            raise Raise(side)
    if op == '+':
        return x + y
    if op == '-':
        return x - y
    if op == '*':
        return x * y
    if y == 0:
        raise Raise(Err('#DIV/0!'))
    return x / y


def rank(value):
    """(type order, comparable): numbers < text < booleans; a blank reads as 0 or "" beside the other side."""
    if isinstance(value, bool):
        return (2, value)
    if isinstance(value, float | int):
        return (0, float(value))
    return (1, str(value).lower())


def compare(op, a, b):
    for side in (a, b):
        if isinstance(side, Err):
            raise Raise(side)
    if a is BLANK and b is BLANK:
        a = b = 0.0
    elif a is BLANK:
        a = '' if isinstance(b, str) else (False if isinstance(b, bool) else 0.0)
    elif b is BLANK:
        b = '' if isinstance(a, str) else (False if isinstance(a, bool) else 0.0)
    x, y = rank(a), rank(b)
    return {'=': x == y, '<>': x != y, '<': x < y, '>': x > y, '<=': x <= y, '>=': x >= y}[op]


def truth(value):
    if isinstance(value, Err):
        raise Raise(value)
    if value is BLANK:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, float | int):
        return value != 0
    raise Raise(Err('#VALUE!'))


def round_excel(number, places):
    """Half away from zero after reading the float at 15 significant digits (quotes.math.round_decimal's rule)."""
    if not math.isfinite(number):
        raise Raise(Err('#NUM!'))
    exact = Decimal(format(number, '.15g'))
    return float(exact.quantize(Decimal(1).scaleb(-int(places)), rounding=ROUND_HALF_UP))


def shown(value):
    """A formula's final value as a cell shows it: a blank reference is 0, an error its code."""
    if value is BLANK:
        return 0.0
    if isinstance(value, Err):
        return value.code
    return value


def _blank(value):
    return value is None or value == '' or value is BLANK


def same(a, b):
    """Whether two cell values agree: numbers within 1e-9, '' ≡ None ≡ blank, text exactly."""
    if _blank(a) or _blank(b):
        return _blank(a) and _blank(b)
    numeric = (int, float, Decimal)
    if isinstance(a, numeric) and isinstance(b, numeric) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(float(a) - float(b)) <= 1e-9
    return a == b
