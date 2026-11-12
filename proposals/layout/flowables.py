"""Our own flowables (plan.md §9.5; J122; J.5 B14). reportlab's platypus flow drives them through its public API only:
`wrap` measures, `split` breaks, `drawOn` places. Drawing records: each flowable's `draw` puts its frames (`items`)
on the `record.Recorder` that platypus hands it as its canvas, so one layout pass gives the frames both painters draw.

- `Text`: measured runs (`text.paragraph`); splits between lines.
- `Block`: frames placed in a block of the body, y down from its own top (tiles, a chart, a team's cards).
- `FullPage`: a whole page of frames (the cover, the agenda, a divider, the thank-you page); it takes no room.
- `Title`, `Note`: a page's title (the slide's title placeholder) and its speaker notes; they take no room.
The plan table is `table.Table`.
"""

from reportlab.platypus import Flowable

from . import items, tokens
from . import text as words


class Text(Flowable):
    """A paragraph of runs. `space_before` is skipped at the top of a page, as platypus does."""

    def __init__(self, runs, leading=None, align='l', space_before=0.0, space_after=0.0, lines=None):
        super().__init__()
        self.runs = [dict(r) for r in runs]
        self.leading = leading
        self.align = align
        self.spaceBefore = space_before
        self.spaceAfter = space_after
        self._lines = lines  # set on a split part: its lines are already measured for its width
        self.para = None

    def wrap(self, avail_w, avail_h):
        if self._lines is not None:
            size = max((r['size'] for r in self.runs), default=10)
            leading = self.leading or round(size * 1.2, 2)
            self.para = {
                'runs': self.runs,
                'size': size,
                'leading': leading,
                'align': self.align,
                'lines': self._lines,
                'h': len(self._lines) * leading,
            }
        else:
            self.para = words.paragraph(self.runs, avail_w, leading=self.leading, align=self.align)
        self.width, self.height = avail_w, self.para['h']
        return self.width, self.height

    def split(self, avail_w, avail_h):
        self.wrap(avail_w, avail_h)
        lines, leading = self.para['lines'], self.para['leading']
        fit = int((avail_h + 0.01) // leading)
        if fit < 1 or fit >= len(lines):
            return []
        first = Text(_runs_of(lines[:fit]), self.leading, self.align, self.spaceBefore, 0, lines[:fit])
        rest = Text(_runs_of(lines[fit:]), self.leading, self.align, 0, self.spaceAfter, lines[fit:])
        return [first, rest]

    def draw(self):
        frame = {'t': 'text', 'x': 0, 'y': 0, 'w': self.width, 'h': self.height, 'title': False, 'wrap': True}
        frame['drop'] = tokens.PARAGRAPH_DROP
        self.canv.put(dict(frame, paragraphs=[self.para]), self.height)


def _runs_of(lines):
    """The runs a run of measured lines holds (a split part's own words), one line after another."""
    out = []
    for number, line in enumerate(lines):
        for seg in line:
            bold, italic = seg['font'].endswith('Bold'), seg['font'].endswith('Oblique')
            out.append(words.run(seg['text'], seg['size'], seg['color'], bold, italic, seg['link']))
        if number < len(lines) - 1 and out:
            out[-1] = dict(out[-1], text=out[-1]['text'] + ' ')
    return out or [words.run('', 10, items.INK)]


class Block(Flowable):
    """Frames in a block of the body, y down from the block's top; `height` is its room (measured when None)."""

    def __init__(self, placed, height=None, space_after=0.0):
        super().__init__()
        self.items = list(placed)
        self.height = height if height is not None else items.height_of(self.items)
        self.spaceAfter = space_after

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return avail_w, self.height

    def draw(self):
        for item in self.items:
            self.canv.put(item, self.height)


class _Marker(Flowable):
    _ZEROSIZE = True

    def wrap(self, *_args):
        return 0, 0

    def draw(self):
        self.canv.mark(self)


class FullPage(_Marker):
    """A whole page of frames: `ground` (the dark page's lift and mark) then `items`. Only a page with nothing else on
    it holds one; it wears no chrome and no page number."""

    kind = 'full'

    def __init__(self, placed, ground=(), title=''):
        super().__init__()
        self.items = list(placed)
        self.ground = list(ground)
        self.title = title


class Title(_Marker):
    """A content page's title. `line` and `fit` say whose plan set the page shows and how its table fitted (the
    Export viewer's fit report, slice 30); a page a table ran on to keeps the title, "(continued)"."""

    kind = 'title'

    def __init__(self, text, line=None, fit=None):
        super().__init__()
        self.text = text
        self.line = line
        self.fit = fit


class Note(_Marker):
    """Speaker notes for the page it lands on: only the producer's words and the page's own figures."""

    kind = 'note'

    def __init__(self, text):
        super().__init__()
        self.text = text
