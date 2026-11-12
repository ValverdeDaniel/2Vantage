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


def row_positions(heights):
    """reportlab's `_rowpositions` (`_calc_height`): each row's top from the table's bottom, summed up from the last
    row with its compensated addition, so every figure is the float reportlab drew with (the last entry is 0)."""
    out, height, carry = [], 0, 0
    for row in reversed(heights):
        out.append(height)
        step = row - carry
        total = height + step
        carry = (total - height) - step
        height = total
    out.append(height)
    out.reverse()
    return out


def origin(colpos, positions, number, down, pad, content):
    """[x, y] of a cell's words from the table's bottom-left as reportlab's `_drawCell` worked them (ALIGN LEFT, VALIGN
    MIDDLE): the column's left plus the left padding, and the top of the words centred between the paddings. Its
    Paragraphs are drawn down from there, each one translated to its own bottom, as the old files drew them."""
    left, _right, top, bottom = pad
    rowpos = positions[min(number + down, len(positions) - 1)]
    rowheight = positions[number] - rowpos
    return [colpos + left, rowpos + (rowheight + bottom - top + content) / 2.0]
