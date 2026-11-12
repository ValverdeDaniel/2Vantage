"""The closed list of functions the test-only evaluator knows (sheet_eval.py; plan.md §9.4): IF, OR, AND, SUM, ROUND,
INDEX, MATCH, IFERROR, MIN, MAX, HYPERLINK, N and COUNT (the stop-loss workbook's, slice 36), as Excel reads them. N is
a number as itself and anything else as 0; COUNT counts the numbers in its references. INDEX returns the cell (a
blank one still equals ""); MATCH(x, range, 0) is exact and case-insensitive (#N/A when absent); SUM, MIN and MAX
skip text and blanks in a reference; IF and IFERROR evaluate only the branch they need. Each takes the evaluator
and its arguments' token spans.
"""

from .sheet_values import BLANK, Err, Raise, Ref, number, rank, round_excel, truth


def if_(ev, spans):
    if truth(ev.value(ev.run(spans[0]))):
        return ev.run(spans[1]) if len(spans) > 1 else True
    return ev.run(spans[2]) if len(spans) > 2 else False


def _logical(ev, spans, combine):
    found = []
    for span in spans:
        item = ev.run(span)
        if isinstance(item, Ref):
            for row, col in item.coords():
                value = ev.cell(item.sheet, row, col)
                if isinstance(value, Err):
                    raise Raise(value)
                if isinstance(value, bool | float):
                    found.append(truth(value))
        else:
            found.append(truth(ev.value(item)))
    if not found:
        raise Raise(Err('#VALUE!'))
    return combine(found)


def _round(ev, spans):
    figure, places = (number(ev.value(ev.run(span))) for span in spans)
    for side in (figure, places):
        if isinstance(side, Err):
            raise Raise(side)
    return round_excel(figure, places)


def _index(ev, spans):
    area = ev.run(spans[0])
    position = number(ev.value(ev.run(spans[1])))
    if isinstance(position, Err):
        raise Raise(position)
    if not isinstance(area, Ref):
        raise ValueError('INDEX reads a range')
    cells = area.coords()
    n = int(position)
    if n < 1 or n > len(cells):
        raise Raise(Err('#REF!'))
    row, col = cells[n - 1]
    return Ref(area.sheet, row, col, row, col)


def _match(ev, spans):
    wanted = ev.value(ev.run(spans[0]))
    if isinstance(wanted, Err):
        raise Raise(wanted)
    area = ev.run(spans[1])
    if len(spans) < 3 or number(ev.value(ev.run(spans[2]))) != 0:
        raise ValueError('MATCH is used exact (0) only')
    if wanted is BLANK:
        raise Raise(Err('#N/A'))
    for index, (row, col) in enumerate(area.coords(), 1):
        value = ev.cell(area.sheet, row, col)
        if value is BLANK or isinstance(value, Err):
            continue
        if rank(value) == rank(wanted):
            return float(index)
    raise Raise(Err('#N/A'))


def _iferror(ev, spans):
    try:
        found = ev.value(ev.run(spans[0]))
    except Raise:
        return ev.run(spans[1])
    return ev.run(spans[1]) if isinstance(found, Err) else found


def _extreme(pick):
    def run(ev, spans):
        numbers = [number for span in spans for number in ev.items(span)]
        return pick(numbers) if numbers else 0.0

    return run


def _hyperlink(ev, spans):
    shown = ev.value(ev.run(spans[-1]))
    if isinstance(shown, Err):
        raise Raise(shown)
    return shown


def _n(ev, spans):
    found = ev.value(ev.run(spans[0]))
    if isinstance(found, Err):
        raise Raise(found)
    if isinstance(found, bool):
        return 1.0 if found else 0.0
    return float(found) if isinstance(found, float | int) else 0.0


FUNCTIONS = {
    'IF': if_,
    'OR': lambda ev, spans: _logical(ev, spans, any),
    'AND': lambda ev, spans: _logical(ev, spans, all),
    'SUM': lambda ev, spans: sum((n for span in spans for n in ev.items(span)), 0.0),
    'ROUND': _round,
    'INDEX': _index,
    'MATCH': _match,
    'IFERROR': _iferror,
    'MIN': _extreme(min),
    'MAX': _extreme(max),
    'HYPERLINK': _hyperlink,
    'N': _n,
    'COUNT': lambda ev, spans: float(sum(1 for span in spans for _ in ev.items(span))),
}
