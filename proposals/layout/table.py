"""The plan table (plan.md §9.5; J133, J140; J.5 B14): our own flowable holding its cells as runs, measured with the
one measure (`text`), split between rows with its header repeated, and recorded as a `table` frame. Ported from the
old look's table style (old Vantage 891f1b3 `proposal_pdf._look_style`): a brand header, striped rows, current
columns grey, recommended columns blue with a blue header, band rows across the table, a hairline under every row.
A later fill wins: stripe, then current column, then recommended column, then band, then the row's own.

A row: {kind: head | band | row | cost | total | plain, cells: [cell], fill?, rule_above?, keep_with_next?}; a
cell: {runs, align: l | c, span?}. `mark` rows (kind `row`) are the benefit rows `rows_over` counts.
"""

from reportlab.platypus import Flowable

from . import items, tokens
from . import text as words

SIDE_PAD = 6.0


class Table(Flowable):
    def __init__(self, rows, widths, colours, *, head=1, pad=3.5, current=(), picked=(), zebra=True, h_align='LEFT'):
        super().__init__()
        self.rows = [dict(row) for row in rows]
        self.widths = list(widths)
        self.colours = colours
        self.head = head
        self.pad = pad
        self.current = tuple(current)
        self.picked = tuple(picked)
        self.zebra = zebra
        self.hAlign = h_align
        self.measured = None
        self.fit = None

    # --- measuring ---------------------------------------------------------------------------------------------------
    def _spans(self, row):
        """[(column, span, cell)] for a row's cells."""
        out, col = [], 0
        for cell in row['cells']:
            span = cell.get('span') or 1
            out.append((col, span, cell))
            col += span
        return out

    def _measure(self):
        measured = []
        for row in self.rows:
            cells, tallest = [], 0.0
            for col, span, cell in self._spans(row):
                room = sum(self.widths[col : col + span]) - 2 * SIDE_PAD
                para = words.paragraph(cell['runs'], max(room, 4), align=cell.get('align', 'l'))
                cells.append((col, span, para))
                tallest = max(tallest, para['h'])
            measured.append((tallest + 2 * self.pad, cells))
        self.measured = measured
        return measured

    def wrap(self, avail_w, avail_h):
        measured = self._measure()
        self.width = sum(self.widths)
        self.height = sum(height for height, _cells in measured)
        return self.width, self.height

    def rows_over(self, cap=tokens.MAX_ROW_LINES):
        """How many benefit rows take more than `cap` lines of type in any cell, label included."""
        measured = self.measured or self._measure()
        return sum(
            1
            for row, (_h, cells) in zip(self.rows, measured, strict=True)
            if row['kind'] == 'row' and max(len(para['lines']) for _c, _s, para in cells) > cap
        )

    def heights(self):
        return [height for height, _cells in (self.measured or self._measure())]

    # --- splitting ---------------------------------------------------------------------------------------------------
    def _part(self, rows):
        part = Table(
            rows,
            self.widths,
            self.colours,
            head=self.head,
            pad=self.pad,
            current=self.current,
            picked=self.picked,
            zebra=self.zebra,
            h_align=self.hAlign,
        )
        part.fit = self.fit
        return part

    def split(self, avail_w, avail_h):
        heights = self.heights()
        head = sum(heights[: self.head])
        used, last = head, None
        for number in range(self.head, len(self.rows)):
            if used + heights[number] > avail_h + 0.01:
                break
            used += heights[number]
            if not self.rows[number].get('keep_with_next') or number == len(self.rows) - 1:
                last = number
        if last is None or last >= len(self.rows) - 1:
            return []
        header = self.rows[: self.head]
        return [self._part(self.rows[: last + 1]), self._part(header + self.rows[last + 1 :])]

    # --- recording ---------------------------------------------------------------------------------------------------
    def _fill(self, number, row, col):
        colours = self.colours
        fill = None
        if row['kind'] == 'head':
            fill = colours['blue'] if col in self.picked else colours['navy']
            return row.get('fill') or fill
        if self.zebra and number >= 2 and number % 2 == 0 and row['kind'] != 'band':
            fill = colours['zebra']
        if col in self.current:
            fill = colours['current']
        if col in self.picked:
            fill = colours['blue_bg']
        if row['kind'] == 'band':
            fill = colours['footer']
        return row.get('fill') or fill

    def draw(self):
        cells, rules = [], []
        measured = self.measured or self._measure()
        lefts = [sum(self.widths[:n]) for n in range(len(self.widths) + 1)]
        y = 0.0
        for number, (row, (height, paras)) in enumerate(zip(self.rows, measured, strict=True)):
            for col, span, para in paras:
                x, w = lefts[col], lefts[col + span] - lefts[col]
                room = w - 2 * SIDE_PAD
                text = {
                    't': 'text',
                    'x': x + SIDE_PAD,
                    'y': y + (height - para['h']) / 2,
                    'w': room,
                    'h': para['h'],
                    'title': False,
                    'wrap': True,
                    'paragraphs': [para],
                }
                fill = self._fill(number, row, col)
                cells.append(
                    {
                        't': 'cell',
                        'x': x,
                        'y': y,
                        'w': w,
                        'h': height,
                        'row': number,
                        'col': col,
                        'span': span,
                        'fill': fill,
                        'kind': row['kind'],
                        'text': text,
                    }
                )
            if row.get('rule_above'):
                rules.append(items.line(0, y, self.width, y, row['rule_above'], 1))
            rules.append(items.line(0, y + height, self.width, y + height, self.colours['hairline'], 0.4))
            y += height
        frame = {
            't': 'table',
            'x': 0,
            'y': 0,
            'w': self.width,
            'h': self.height,
            'cols': list(self.widths),
            'row_h': [height for height, _p in measured],
            'head': self.head,
            'cells': cells,
            'rules': rules,
        }
        self.canv.put(frame, self.height)


def cell(text, size, color, bold=False, align='l', span=1, link=None):
    """A cell of one run."""
    return {'runs': [words.run(text, size, color, bold, link=link)], 'align': align, 'span': span}


def rich(runs, align='l', span=1):
    return {'runs': runs, 'align': align, 'span': span}
