"""A table's geometry as reportlab's own Table works it out, which drew the old files (old Vantage 891f1b3 through
reportlab 4.2.5 `platypus.tables`): where a row's cells sit when a cell above spans down into it, how a cell spanning
rows shares what it needs beyond their own heights (`spanFixDim`), where a cell's words sit between its padding
(VALIGN MIDDLE), and how tall an empty cell is. Pure; `table.Table` measures and records with it.
"""

# reportlab's default cell leading: an empty '' cell of the old tables was one line of it, whatever its type size.
EMPTY_LINE = 12.0


def placed(rows):
    """For each row, [(column, span, cell)]: a column a cell above spans down into is skipped."""
    below = {}  # column → the last row a cell above reaches down to
    out = []
    for number, row in enumerate(rows):
        found, col = [], 0
        for cell in row['cells']:
            while below.get(col, -1) >= number:
                col += 1
            span, down = cell.get('span') or 1, cell.get('rowspan') or 1
            found.append((col, span, cell))
            if down > 1:
                for spanned in range(col, col + span):
                    below[spanned] = number + down - 1
            col += span
        out.append(found)
    return out


def held(rows):
    """The rows a cell above spans into: a table never splits just above one."""
    out = set()
    for number, row in enumerate(rows):
        for cell in row['cells']:
            out.update(range(number + 1, number + (cell.get('rowspan') or 1)))
    return out


def share(heights, spanned, fuzz=1e-6):
    """reportlab's `spanFixDim`: `spanned` {(first row, last row): height needed}; a span its rows do not already hold
    shares what is missing equally among them, the largest need first. `heights` changes in place."""
    extra = {}
    for need, (first, last) in sorted(((need, rows) for rows, need in spanned.items()), reverse=True):
        rows = range(first, last + 1)
        have = sum(heights[row] + extra.get(row, 0.0) for row in rows)
        if have >= need - fuzz:
            continue
        each = (need - have) / len(rows)
        for row in rows:
            extra[row] = extra.get(row, 0.0) + each
    for row, more in extra.items():
        heights[row] += more


def middle(height, content, top, bottom):
    """How far below its cell's top a cell's words start: centred between its top and bottom padding."""
    return (height - content + top - bottom) / 2
