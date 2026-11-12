"""The fit report (plan.md §8.14; J110; old Vantage 891f1b3 `proposal_preview.PageLog._fit_of`, D-193 slice 3): how each
plan set's table came out on the client deck, from the recorder's fit log (`page['fit']`, `layout.fit.exhibit`) and the
table frames the layout recorded. What the team checked by eye on the 2026-11-05 call: does the table sit on one slide,
at what size, did its notes move on, do the rates and totals sit with the benefits (Stephanie's rule), and which benefit
rows run past two lines of type. Pure: recorded pages in, words' facts out; nothing is laid out again.

`runs(pages)` → [(first, [indexes])]: each plan set's first page and every page it ran on to (its "(continued)" pages
carry its line). `of(pages, run)` → the first page's fit plus {slides: [n], money_slide: n | None, tall_rows: [{label,
lines}]}, or None where the layout logged no fit.
"""

from ..layout import tokens

MONEY_KINDS = ('cost', 'total')  # a plan set's cost and totals rows (`story.exhibit.build`)
RATES_BAND = 'Rates'  # the rates band's label (`story.exhibit_rows.items`): where a plan set's money starts
TALL_LINES = tokens.MAX_ROW_LINES  # the fitter's own cap: a benefit row past it is "tall"


def runs(pages):
    """Each plan set's pages: its titled first page (it has a fit) and the "(continued)" pages after it."""
    out, current = [], None
    for index, page in enumerate(pages):
        if page['line'] and page['continued'] and current is not None and pages[current[0]]['line'] == page['line']:
            current[1].append(index)
            continue
        current = (index, [index]) if page['line'] and page['fit'] and not page['continued'] else None
        if current is not None:
            out.append(current)
    return out


def _words(text):
    """A recorded text frame's words, as one line (a measured line's segments carry their own spaces)."""
    lines = [''.join(seg['text'] for seg in line) for para in text.get('paragraphs') or [] for line in para['lines']]
    return ' '.join(' '.join(lines).split())


def _line_count(text):
    return sum(len(para.get('lines') or []) for para in text.get('paragraphs') or [])


def _tables(page):
    return [frame for frame in page['frames'] if frame.get('t') == 'table']


def _has_money(page):
    for table in _tables(page):
        for cell in table['cells']:
            if cell['kind'] in MONEY_KINDS:
                return True
            if cell['kind'] == 'band' and _words(cell['text']) == RATES_BAND:
                return True
    return False


def _tall_rows(page):
    """The benefit rows on this page whose cells run past `TALL_LINES` lines: [{label, lines}]."""
    out = []
    for table in _tables(page):
        rows = {}
        for cell in table['cells']:
            if cell['kind'] == 'row':
                rows.setdefault(cell['row'], []).append(cell)
        for _number, cells in sorted(rows.items()):
            lines = max(_line_count(cell['text']) for cell in cells)
            if lines > TALL_LINES:
                label = next((cell for cell in cells if cell['col'] == 0), cells[0])
                out.append({'label': _words(label['text']), 'lines': lines})
    return out


def of(pages, run):
    """How one plan set's table came out over the pages it took (`run`, from `runs`)."""
    first, indexes = run
    fit = pages[first]['fit']
    if not fit:
        return None
    taken = [pages[index] for index in indexes]
    money = next((page['n'] for page in taken if _has_money(page)), None)
    tall = [row for page in taken for row in _tall_rows(page)]
    return dict(fit, slides=[page['n'] for page in taken], money_slide=money, tall_rows=tall)
