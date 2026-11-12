"""What each cell of a tab shows, and the checks a person makes by eye (plan.md §9.4; J116, J118; old
`workbook_preview._Tab` at 891f1b3, D-194): a formula error, a number Excel shows as "####", text cut off, and text so
tight it may be cut on another screen.

Read from the sheet model, never from a file: a formula's value is its stored result (quotes' math; no evaluator,
J119), drawn through its number format by `workbook.text`; sizes are the file's (`sizes`). Pure. A cell is
`[r, c, text, flags, extra?]`, 0-based, as the grid draws it; `extra` holds `pad` (the `_)` a format keeps clear) and
`real` (the number a "####" hides).
"""

from ..workbook import text as t
from ..workbook.model import BLANK, FORMULA, column_letter
from ..workbook.model import NUMBER as NUMBER_KIND
from . import sizes

NUMBER, ERROR, HASHED, LINK, LOGICAL = 1, 2, 4, 8, 16  # a cell's flags
MAX_CHECKS = 40  # a check names at most this many cells of one kind on one tab
CHECK_KINDS = ('error', 'hash', 'cut', 'tight')  # worst first
H_ALIGN = {'center': 'center', 'center_across': 'center', 'right': 'right', 'justify': 'justify'}


def align_of(style):
    """The cell's horizontal alignment as the look names it (left unless the style says otherwise), or None."""
    align = style.get('align')
    return H_ALIGN.get(align, 'left') if align else None


def value_of(cell):
    """What the cell holds as Excel shows it: a formula's stored result, a text, a number; None for a blank."""
    if cell is None or cell.kind == BLANK:
        return None
    return cell.result if cell.kind == FORMULA else cell.value


class TabCells:
    """One tab's cells worked out: `run()` → (cells, checks {kind: [check]}, counts {kind: n}, unknown formats);
    `colours` then holds the colour each number format gives its value."""

    def __init__(self, sheet, shown_rows=None):
        self.sheet = sheet
        self.rows, self.cols = sizes.extent(sheet)
        self.shown = self.rows if shown_rows is None else min(self.rows, shown_rows)
        self.col_px = [sizes.col_px(sheet, col) for col in range(1, self.cols + 1)]
        self.row_pt = [sizes.row_pt(sheet, row) for row in range(1, self.rows + 1)]
        self.merged = {(r1, c1): (r2 - r1 + 1, c2 - c1 + 1) for r1, c1, r2, c2 in sheet.merges}
        self.covered = {
            (r, c)
            for r1, c1, r2, c2 in sheet.merges
            for r in range(r1, r2 + 1)
            for c in range(c1, c2 + 1)
            if (r, c) != (r1, c1)
        }
        self.filled = {key for key, cell in sheet.cells.items() if cell.kind != BLANK and key not in self.covered}
        self.checks = {kind: [] for kind in CHECK_KINDS}
        self.counts = dict.fromkeys(CHECK_KINDS, 0)
        self.unknown = 0
        self.colours = {}  # {(r, c): '#RRGGBB'} 0-based: the colour a number format gives the value it shows
        self._result = None

    def run(self):
        """Works the tab out once; later calls answer the same."""
        if self._result is None:
            self._result = self._work()
        return self._result

    def _work(self):
        cells = []
        for (row, col), cell in sorted(self.sheet.cells.items()):
            if (row, col) not in self.filled:
                continue
            item = self._cell(row, col, cell)
            if item is not None and row <= self.shown:
                cells.append(item)
        return cells, self.checks, self.counts, self.unknown

    def _label(self, row):
        """What a row is called: column A's text, or B's (Compare merges its labels A:B)."""
        for col in (1, 2):
            cell = self.sheet.get(row, col)
            value = value_of(cell)
            if isinstance(value, str) and value.strip():
                return ' '.join(value.split())[:80]
        return ''

    def _check(self, kind, row, col, sentence, value):
        self.counts[kind] += 1
        if len(self.checks[kind]) < MAX_CHECKS:
            self.checks[kind].append(
                {
                    'cell': f'{column_letter(col)}{row}',
                    'r': row - 1,
                    'c': col - 1,
                    'label': self._label(row),
                    'text': sentence,
                    'value': value,
                }
            )

    def _cell(self, row, col, cell):
        style = cell.style or {}
        fmt = style.get('num_format') or 'General'
        if fmt not in t.KNOWN_FORMATS:
            self.unknown += 1
        value = value_of(cell)
        shown, colour, pad = t.display(value, fmt)
        if colour:
            self.colours[(row - 1, col - 1)] = colour
        flags, extra = 0, {}
        is_number = cell.kind == NUMBER_KIND or (cell.kind == FORMULA and isinstance(value, int | float))
        if cell.kind == FORMULA and isinstance(value, str) and value in t.ERRORS:
            flags |= ERROR
            self._check('error', row, col, f'{value}: Excel shows an error here, not a value.', value)
        elif isinstance(value, bool):
            flags |= LOGICAL
        elif is_number:
            flags |= NUMBER
        if cell.kind == FORMULA and 'HYPERLINK(' in str(cell.value):
            flags |= LINK
        if pad:
            extra['pad'] = pad
        if not shown:
            return None
        span = self.merged.get((row, col), (1, 1))
        width = sum(self.col_px[col - 1 : col - 1 + span[1]]) - t.INDENT_PX * int(style.get('indent') or 0)
        size, bold = style.get('font_size') or 11, bool(style.get('bold'))
        if flags & NUMBER and fmt in ('General', '@'):
            chars = t.GENERAL_CHARS  # General gives up decimals before it gives up the number
            while chars > 1 and not t.number_fits(shown, pad, width, size, bold):
                chars -= 1
                shown = t.general(value, chars)
        if flags & NUMBER and not t.number_fits(shown, pad, width, size, bold):
            extra['real'] = shown
            self._check('hash', row, col, f'Shows "####": {shown} is wider than its column.', shown)
            shown = t.hashes(width, size, bold)
            flags |= HASHED
        elif flags & NUMBER and not t.number_fits(shown, pad, width, size, bold, t.STRICT):
            sentence = f'Tight: {shown} only just fits its column, and may show "####" on a screen at 100%.'
            self._check('tight', row, col, sentence, shown)
        elif not flags & (NUMBER | ERROR | LOGICAL):
            self._cut_check(row, col, shown, style, span, width)
        item = [row - 1, col - 1, shown, flags]
        if extra:
            item.append(extra)
        return item

    def _cut_check(self, row, col, shown, style, span, width):
        """Text Excel cannot show whole: wrapped onto more lines than its row is tall, or one line wider than the room
        it may run on into. Measured twice (SURE, then STRICT): failing the first is cut off, only the second tight."""
        size, bold = style.get('font_size') or 11, bool(style.get('bold'))
        if style.get('text_wrap'):
            height = sum(self.row_pt[row - 1 : row - 1 + span[0]])
            line = t.line_pt(size)
            fits = max(1, int((height + 0.5) // line))
            for kind, geometry in (('cut', t.SURE), ('tight', t.STRICT)):
                lines = t.wrapped_lines(shown, width, size, bold, geometry)
                if lines * line > height + 0.5:
                    sentence = (
                        f'Cut off: {lines} lines of text in a row tall enough for {fits}.'
                        if kind == 'cut'
                        else f'Tight: wraps to {lines} lines on a screen at 100%, where the row holds {fits}.'
                    )
                    self._check(kind, row, col, sentence, shown[:120])
                    return
            return
        need = t.text_px(shown, size, bold)
        for kind, geometry in (('cut', t.SURE), ('tight', t.STRICT)):
            room = t.room(width, geometry)
            if need <= room:
                return
            if span == (1, 1):
                room += self._spill_room(row, col, align_of(style), need - room)
            if need > room:
                sentence = (
                    'Cut off: the text runs past its cell into one that is not empty.'
                    if kind == 'cut'
                    else 'Tight: the text only just fits, and may be cut off on a screen at 100%.'
                )
                self._check(kind, row, col, sentence, shown[:120])
                return

    def _spill_room(self, row, col, align, wanted):
        """How far a line of text may run on, in pixels: over the empty cells beside it (to the right, to the left for
        right-aligned text, both ways for centred), stopping at a cell with a value or a merge."""

        def free(c):
            # Past the last column in use every cell is empty, at Excel's default width.
            key = (row, c)
            return c >= 1 and key not in self.filled and key not in self.covered and key not in self.merged

        room = 0
        for step in {'right': (-1,), 'center': (1, -1)}.get(align, (1,)):
            c = col + step
            while free(c) and room < wanted and c < self.cols + 64:
                room += self.col_px[c - 1] if c <= len(self.col_px) else sizes.DEFAULT_COL_PX
                c += step
        return room
