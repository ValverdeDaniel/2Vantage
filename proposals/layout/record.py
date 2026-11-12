"""The one layout pass and its recorder (plan.md §9.5; J122, J139, J140). Pure: flowables in, recorded pages out.

`lay_out(story, chrome)` flows each page of the story into the body frame (BODY_X, BODY_TOP, BODY_W × BODY_H)
through platypus's public API: `wrap` to measure, `split` when a flowable runs past the frame, `drawOn` to place,
with a `Recorder` as the canvas, so each flowable records its frames where it lands. A flowable too tall for what is
left of a page splits there, and the rest goes on to a new page that keeps the title, "(continued)"; a flowable that
cannot split starts the new page whole. Nothing is drawn here.

A recorded page: {n, kind: content | full, title, continued, line, fit, notes, frames, chrome}. `frames` are the
page's own; `chrome` what every content page wears (`chrome.chrome_items`: the title, the rule, the footer bar, the
stamp, the rates note, the firm, the page number, Draft), which the PowerPoint lifts onto its master (slice 31). A full
page (the cover, the agenda, a divider, the thank-you page) wears no chrome and no number. The PDF (`paint/pdf.py`)
draws chrome then frames; the PowerPoint replays the same frames (J141).
"""

from . import chrome as chrome_
from . import items, tokens
from .flowables import FullPage, Note, Title

CONTINUED = ' (continued)'


class Recorder:
    """A canvas for `Flowable.drawOn`: it follows the origin platypus translates to and keeps the frames the
    flowables put, moved from the flowable's own top-left to the page's (y down from the top)."""

    def __init__(self, page):
        self.page = page
        self.ox = 0.0
        self.oy = 0.0
        self._saved = []

    def saveState(self):  # noqa: N802 - reportlab's canvas API
        self._saved.append((self.ox, self.oy))

    def restoreState(self):  # noqa: N802
        self.ox, self.oy = self._saved.pop()

    def translate(self, dx, dy):
        self.ox += dx
        self.oy += dy

    def put(self, item, height):
        top = tokens.PAGE_H - (self.oy + height)
        self.page['frames'].append(items.shifted(item, self.ox, top))

    def mark(self, flowable):
        """A zero-size flowable's word for the page: its title, a speaker note, or a whole page."""
        page = self.page
        if flowable.kind == 'title':
            page.update(title=flowable.text, line=flowable.line, fit=flowable.fit)
        elif flowable.kind == 'note':
            page['notes'].append(flowable.text)
        else:
            page.update(kind='full', title=flowable.title)
            page['frames'].extend(flowable.ground + flowable.items)


def _page(continued_from=None):
    page = {'kind': 'content', 'title': '', 'continued': False, 'line': None, 'fit': None, 'notes': [], 'frames': []}
    if continued_from is not None:
        title = continued_from['title']
        page.update(
            title=title if title.endswith(CONTINUED) or not title else f'{title}{CONTINUED}',
            continued=True,
            line=continued_from['line'],
        )
    return page


class _Flow:
    """The body frame as reportlab's Frame fills it: a flowable's space before is skipped at the top of a page and
    overlaps the space the one above left under it (the larger of the two, `overlapAttachedSpace`); a zero-size
    flowable (a title, a note) leaves none."""

    def __init__(self):
        self.pages = []
        self.page = None
        self.used = 0.0
        self.filled = False
        self.after = 0.0  # the space the last flowable left under it

    def start(self, continued_from=None):
        self.page = _page(continued_from)
        self.pages.append(self.page)
        self.used, self.filled, self.after = 0.0, False, 0.0

    def room(self):
        return tokens.BODY_H - self.used

    def place(self, flowable, before):
        width, height = flowable.wrap(tokens.BODY_W, max(self.room() - before, 0))
        top = tokens.BODY_TOP + self.used + before
        bottom = tokens.PAGE_H - top - height
        flowable.drawOn(Recorder(self.page), tokens.BODY_X, bottom, _sW=tokens.BODY_W - width)
        self.after = flowable.getSpaceAfter()
        self.used += before + height + self.after
        self.filled = True

    def flow(self, chunk):
        self.start()
        queue = list(chunk)
        while queue:
            flowable = queue.pop(0)
            if isinstance(flowable, (Title, Note, FullPage)):
                flowable.drawOn(Recorder(self.page), 0, 0)
                self.after = 0.0
                continue
            before = max(flowable.getSpaceBefore() - self.after, 0.0) if self.filled else 0.0
            room = self.room() - before
            _width, height = flowable.wrap(tokens.BODY_W, max(room, 0))
            if height <= room + 0.01:
                self.place(flowable, before)
                continue
            parts = flowable.split(tokens.BODY_W, room) if room > 0 else []
            if len(parts) > 1:
                self.place(parts[0], before)
                queue = parts[1:] + queue
                continue
            if self.filled:
                self.start(continued_from=self.page)
                queue.insert(0, flowable)
                continue
            self.page['overflow'] = True  # taller than an empty page and it cannot split: placed as it is
            self.place(flowable, 0.0)


def lay_out(story, chrome):
    """`story`: [[flowable]], one list a page (a list that runs on makes more pages). `chrome`: the footer's facts for
    `chrome.chrome_items` ({stamp, note, firm, logo, draft, colours}). → [recorded page], numbered from 1."""
    flow = _Flow()
    for chunk in story:
        if chunk:
            flow.flow(chunk)
    pages = [page for page in flow.pages if page['frames'] or page['title']]
    for number, page in enumerate(pages, start=1):
        page['n'] = number
        page['chrome'] = [] if page['kind'] == 'full' else chrome_.chrome_items(page['title'], number, chrome)
    return pages
