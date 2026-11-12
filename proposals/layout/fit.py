"""Fitting a table to its page (plan.md §9.5; J140; old Vantage 891f1b3 `proposal_presentation._fitted_table`,
`_short_rows_size`, `_exhibit`). Pure.

- The type steps down from the table's largest size (12 pt) by half points to the floor (8 pt): the largest at which
  the real table fits, measured, never guessed from character counts. Then the most air that size allows.
- A plan set's table also keeps its benefit rows to two lines where it can (`MAX_ROW_LINES`): it steps down further
  to the largest type at which no more rows run past two lines than at the floor; a table no smaller type would help
  keeps the largest type that fits.
- A plan set's page fits one of three ways (the fit report's `outcome`): the table and its notes share the page
  (`fits`); the table stays whole and its notes follow on (`notes_follow`); or, too long even at the floor, it runs on
  with its header repeated (`runs_on`), each later page titled "(continued)".
- A benefit value longer than `LONG_VALUE` moves to a numbered note under its table (`noted`), so one sentence never
  stretches a row across a page; a sentence several plans share is one note.
"""

from . import tokens


def sizes(largest, floor=tokens.TABLE_TYPE['floor']):
    out = [largest]
    while out[-1] - tokens.TYPE_STEP >= floor:
        out.append(out[-1] - tokens.TYPE_STEP)
    return out


def _short_rows(fits, steps, best):
    def over(size):
        table = fits(size, tokens.TIGHTEST_PAD)
        return None if table is None else table.rows_over()

    at_best = over(best)
    if not at_best:
        return best
    smaller = steps[steps.index(best) + 1 :]
    floor_over = over(smaller[-1]) if smaller else None
    if floor_over is None or floor_over >= at_best:
        return best
    for size in smaller:
        found = over(size)
        if found is not None and found <= floor_over:
            return size
    return best


def fitted(build, room, largest=tokens.TABLE_TYPE['cell'], short_rows=False):
    """(table, size, pad) for the largest type at which `build(size, pad)` fits `room`, or None when it does not fit
    even at the floor."""

    def fits(size, pad):
        table = build(size, pad)
        return table if table.wrap(tokens.BODY_W, 10**6)[1] <= room else None

    steps = sizes(largest)
    low, high, best = 0, len(steps) - 1, None
    while low <= high:  # the type gets smaller along the list, and the table shorter
        middle = (low + high) // 2
        if fits(steps[middle], tokens.TIGHTEST_PAD):
            best, high = steps[middle], middle - 1
        else:
            low = middle + 1
    if best is None:
        return None
    if short_rows:
        best = _short_rows(fits, steps, best)
    for pad in tokens.PADS:
        table = fits(best, pad)
        if table is not None:
            return table, best, pad
    return build(best, tokens.TIGHTEST_PAD), best, tokens.TIGHTEST_PAD


def exhibit(build, under, body=tokens.BODY_H):
    """A plan set's table and how it fitted: (table, fit). `under` is the height of what must sit under it (its notes
    and the page's own lines). `fit`: {outcome, size, pad, floor, room, height, spare, rows_over}."""
    outcome, room = 'fits', body - under - 2
    found = fitted(build, room, short_rows=True)
    if found is None:
        outcome, room = 'notes_follow', body - 2
        found = fitted(build, room, short_rows=True)
    if found is None:
        outcome = 'runs_on'
        floor = tokens.TABLE_TYPE['floor']
        found = (build(floor, tokens.TIGHTEST_PAD), floor, tokens.TIGHTEST_PAD)
    table, size, pad = found
    height = table.wrap(tokens.BODY_W, 10**6)[1]
    table.fit = {
        'outcome': outcome,
        'size': size,
        'pad': pad,
        'floor': tokens.TABLE_TYPE['floor'],
        'room': round(room, 1),
        'height': round(height, 1),
        'spare': round(room - height, 1) if outcome != 'runs_on' else None,
        'rows_over': table.rows_over(),
    }
    return table, table.fit


def noted(value, label, carrier, shared):
    """A cell's text, or "See note n" when it is longer than `LONG_VALUE`; `shared` ({(label, value): {number,
    carriers}}) collects the notes, one per sentence however many columns point at it."""
    if len(value) <= tokens.LONG_VALUE:
        return value
    note = shared.setdefault((label, value), {'number': len(shared) + 1, 'carriers': []})
    if carrier not in note['carriers']:
        note['carriers'].append(carrier)
    return f'See note {note["number"]}'


def notes_of(shared):
    """The notes' lines, numbered: "1. Aetna, Cigna, Specialty Visits: …"."""
    return [
        f'{note["number"]}. {", ".join(c for c in note["carriers"] if c)}, {label}: {value}'
        for (label, value), note in shared.items()
    ]


def height_under(flowables, width=tokens.BODY_W):
    """How tall a page's lines under its table really are."""
    return sum(f.wrap(width, 10**6)[1] + f.getSpaceBefore() + f.getSpaceAfter() for f in flowables)
