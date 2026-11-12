"""The plan table and every other table the deck prints (plan.md §9.5; J133, J136, J140; J.5 B14): our own flowable
holding its cells as runs, measured with the one measure (`text`), split between rows with its header repeated, and
recorded as a `table` frame. Ported from the old look's table style (old Vantage 891f1b3 `proposal_pdf._look_style`)
and from the geometry of reportlab's own Table, which drew the old files (`grid`): each cell's paragraphs centred
between its padding, a row as tall as its tallest cell, a cell spanning rows sharing out what it needs beyond them.

The look: a brand header, striped rows, current columns grey, recommended columns blue with a blue header, band rows
across the table, a hairline under every row (from `rule`'s column on). A later fill wins: stripe, then current column,
then recommended column, then band, then the row's own, then the cell's own.

A row: {kind: head | band | row | cost | total | plain, cells: [cell], fill?, rule_above?, keep_with_next?, blanks?};
`blanks` says the row also holds empty cells under its spans (the old files' '' cells, `grid.EMPTY_LINE` tall each).
A cell: {runs, align: l | c | r, span?, rowspan?, leading?, paras?, pad?, fill?}: `paras` ([{runs, align, leading}])
is a cell of several paragraphs, `pad` its own (left, right, top, bottom); a cell of no runs (`blank`) is the old
tables' empty '' cell, one 12 pt line. Rows of kind `row` are the benefit rows `rows_over` counts.
"""

from reportlab.platypus import Flowable

from . import grid, items, tokens
from . import text as words

SIDE_PAD = 6.0


class Table(Flowable):
    def __init__(
        self, rows, widths, colours, *, head=1, pad=3.5, current=(), picked=(), zebra=True, h_align='LEFT', rule=None
    ):
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
        # The hairline under each row: its colour, width and the column it starts at.
        self.rule = rule or {'color': colours['hairline'], 'lw': 0.4, 'col': 0}
        self.measured = None
        self.fit = None

    # --- measuring ---------------------------------------------------------------------------------------------------
    def _pads(self, cell):
        return tuple(cell.get('pad') or (SIDE_PAD, SIDE_PAD, self.pad, self.pad))

    def _paragraphs(self, cell, room):
        specs = cell['paras'] if 'paras' in cell else [cell]
        return [
            words.paragraph(spec['runs'], max(room, 4), leading=spec.get('leading'), align=spec.get('align', 'l'))
            for spec in specs
        ]

    def _measure(self):
        """[(height, [placed cell])]: each placed cell {col, span, rowspan, paras, content, pad, cell}."""
        heights, placed_rows, spanned = [], [], {}
        for number, (row, spots) in enumerate(zip(self.rows, grid.placed(self.rows), strict=True)):
            placed, tallest = [], (grid.EMPTY_LINE + 2 * self.pad) if row.get('blanks') else 0.0
            for col, span, cell in spots:
                pads = self._pads(cell)
                paras = self._paragraphs(cell, sum(self.widths[col : col + span]) - pads[0] - pads[1])
                content = sum(para['h'] for para in paras)
                down = cell.get('rowspan') or 1
                need = content + pads[2] + pads[3]
                placed.append(
                    {'col': col, 'span': span, 'rowspan': down, 'paras': paras, 'content': content, 'pad': pads}
                )
                if down > 1:
                    key = (number, number + down - 1)
                    spanned[key] = max(spanned.get(key, need), need)
                else:
                    tallest = max(tallest, need)
            heights.append(tallest)
            placed_rows.append(placed)
        grid.share(heights, spanned)
        self.measured = list(zip(heights, placed_rows, strict=True))
        return self.measured

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
            if row['kind'] == 'row' and max((len(p['lines']) for c in cells for p in c['paras']), default=1) > cap
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
            rule=self.rule,
        )
        part.fit = self.fit
        return part

    def split(self, avail_w, avail_h):
        heights = self.heights()
        held = grid.held(self.rows)  # rows a cell above spans into: never the first of a part
        used, last = sum(heights[: self.head]), None
        for number in range(self.head, len(self.rows)):
            if used + heights[number] > avail_h + 0.01:
                break
            used += heights[number]
            ends = number == len(self.rows) - 1
            if ends or (not self.rows[number].get('keep_with_next') and number + 1 not in held):
                last = number
        if last is None or last >= len(self.rows) - 1:
            return []
        header = self.rows[: self.head]
        return [self._part(self.rows[: last + 1]), self._part(header + self.rows[last + 1 :])]

    # --- recording ---------------------------------------------------------------------------------------------------
    def _fill(self, number, row, col, cell):
        colours = self.colours
        fill = None
        if row['kind'] == 'head':
            fill = colours['blue'] if col in self.picked else colours['navy']
            return cell.get('fill') or row.get('fill') or fill
        if self.zebra and number >= 2 and number % 2 == 0 and row['kind'] != 'band':
            fill = colours['zebra']
        if col in self.current:
            fill = colours['current']
        if col in self.picked:
            fill = colours['blue_bg']
        if row['kind'] == 'band':
            fill = colours['footer']
        return cell.get('fill') or row.get('fill') or fill

    def draw(self):
        cells, rules = [], []
        measured = self.measured or self._measure()
        heights = [height for height, _cells in measured]
        lefts = [sum(self.widths[:n]) for n in range(len(self.widths) + 1)]
        tops = [sum(heights[:n]) for n in range(len(heights) + 1)]
        rule_x = lefts[self.rule['col']]
        for number, (row, (_height, placed)) in enumerate(zip(self.rows, measured, strict=True)):
            y = tops[number]
            for spot, cell in zip(placed, row['cells'], strict=True):
                col, span, down = spot['col'], spot['span'], spot['rowspan']
                x, w = lefts[col], lefts[col + span] - lefts[col]
                h = tops[min(number + down, len(heights))] - y
                left, right, top, bottom = spot['pad']
                text = {
                    't': 'text',
                    'x': x + left,
                    'y': y + grid.middle(h, spot['content'], top, bottom),
                    'w': w - left - right,
                    'h': spot['content'],
                    'title': False,
                    'wrap': True,
                    'paragraphs': spot['paras'],
                    'drop': tokens.PARAGRAPH_DROP,
                }
                found = {
                    't': 'cell',
                    'x': x,
                    'y': y,
                    'w': w,
                    'h': h,
                    'row': number,
                    'col': col,
                    'span': span,
                    'fill': self._fill(number, row, col, cell),
                    'kind': row['kind'],
                    'pad': list(spot['pad']),
                    'text': text,
                }
                if down > 1:
                    found['rowspan'] = down
                cells.append(found)
            if row.get('rule_above'):
                rules.append(items.line(0, y, self.width, y, row['rule_above'], 1))
            bottom = tops[number + 1]
            rules.append(items.line(rule_x, bottom, self.width, bottom, self.rule['color'], self.rule['lw']))
        frame = {
            't': 'table',
            'x': 0,
            'y': 0,
            'w': self.width,
            'h': self.height,
            'cols': list(self.widths),
            'row_h': heights,
            'head': self.head,
            'cells': cells,
            'rules': rules,
        }
        self.canv.put(frame, self.height)


def cell(text, size, color, bold=False, align='l', span=1, link=None, leading=None):
    """A cell of one run; `leading` as the old style gave it (1.2 × the size when left out)."""
    found = {'runs': [words.run(text, size, color, bold, link=link)], 'align': align, 'span': span}
    if leading:
        found['leading'] = leading
    return found


def rich(runs, align='l', span=1, leading=None):
    found = {'runs': runs, 'align': align, 'span': span}
    if leading:
        found['leading'] = leading
    return found


def blank(span=1):
    """An empty cell, as the old tables' '' cells were: no words, one line of 10 pt type at reportlab's 12 pt leading
    (`text.paragraph` of no runs)."""
    return {'runs': [], 'align': 'l', 'span': span}
