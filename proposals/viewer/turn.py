"""What Work with Claude is told about the Export viewer (plan.md §10.6; J120; old Vantage 891f1b3
`ai/page_context._export_viewer` and `_fit_words`, D-193, D-196).

Simplify (J120): the browser sends the viewer's state with the message (`page['viewer']`, ai's turn context, slice 24):
the file on screen, the slide or tab, and on the deck how each plan set's table fitted. This module puts it in words;
nothing is rebuilt per turn (J.5 B21). What the browser sends is data, never trusted: only the keys below are read,
each cut to its size, and a state that does not parse says nothing.

    viewer: {file: excel | powerpoint | pdf | paper, tab?, slide?: {n, title}, slides?, draft?, paper?: {scale, sheet},
             fits?: [{n, title, outcome, size, floor, slides: [n], money_slide, tall_rows: [label]}]}

proposals registers `provide` as a context provider in its AppConfig.ready() (O.1's seam; ai never imports proposals).
"""

MAX_TITLE = 200
MAX_FITS = 40
MAX_TALL = 12
# Each page file in Claude's words: whose pages, what one is called, what builds it (old `_EXPORT_WHAT`).
WHAT = {
    'powerpoint': ("the client PowerPoint's", 'slide'),
    'pdf': ("the client PDF's", 'page'),
    'paper': ("the client PDF's", 'page'),
}
OUTCOMES = ('fits', 'notes_follow', 'runs_on')


def _text(value, limit=MAX_TITLE):
    return ' '.join(str(value).split())[:limit] if isinstance(value, (str, int, float)) else ''


def _number(value, low=0.0, high=10_000.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if low <= value <= high else None


def _pt(size):
    return f'{size:g} pt'


def fit_words(fit, noun='slide', printed=None):
    """How one plan set's table came out, in words (the viewer's fit report, J110)."""
    size, pages = _number(fit.get('size'), 1, 100), [n for n in fit.get('slides') or [] if _number(n, 1)]
    if size is None or fit.get('outcome') not in OUTCOMES:
        return 'no fit recorded'
    if fit['outcome'] == 'runs_on':
        words = f'runs onto {len(pages)} {noun}s even at {_pt(size)}'
    elif fit['outcome'] == 'notes_follow':
        words = f'the table fits one {noun} at {_pt(size)}, but the notes under it moved to the next {noun}'
    else:
        floor = _number(fit.get('floor'), 1, 100) or 0
        words = f'fits on one {noun} at {_pt(size)}' + (', the smallest type' if size <= floor else '')
    if printed:
        words += f', printed at {round(size * printed / 100, 1):g} pt'
    money = _number(fit.get('money_slide'), 1)
    if money and pages and money != pages[0]:
        words += f'; its rates and totals start on {noun} {money:g}, apart from the benefits'
    elif money:
        words += f'; its rates and totals are on the same {noun}'
    tall = [_text(label, 120) for label in (fit.get('tall_rows') or [])[:MAX_TALL] if _text(label, 120)]
    if tall:
        words += '; rows over two lines: ' + ', '.join(tall)
    return words


def _workbook(viewer):
    tab = _text(viewer.get('tab'))
    said = "The producer has the Advisor's Export viewer open on the client spreadsheet as it would download now"
    return said + (f', on the "{tab}" tab.' if tab else '.')


def _deck(viewer, file):
    whose, noun = WHAT[file]
    count = _number(viewer.get('slides'), 0)
    paper = viewer.get('paper') if isinstance(viewer.get('paper'), dict) else {}
    scale = _number(paper.get('scale'), 1, 100) if file == 'paper' else None
    shape = ", its pages the PowerPoint's slides one for one" if file != 'powerpoint' else ''
    counted = f'{count:g} {noun}{"s" if count != 1 else ""}' if count is not None else f'{noun}s'
    out = [
        f"The producer has the Advisor's Export viewer open on {whose} {counted}{shape}, as they would download now"
        + (' (a draft, not issued)' if viewer.get('draft') is True else '')
        + f'. Code builds the file from the plan table and the proposal builder; a {noun} changes when those do.'
    ]
    if scale:
        sheet = 'portrait' if paper.get('sheet') == 'portrait' else 'landscape'
        out.append(
            f'On screen: Paper, each page as it prints on a US Letter sheet: at {scale:g}% on Letter {sheet}, inside a '
            'half-inch margin, so its type prints that much smaller.'
        )
    slide = viewer.get('slide') if isinstance(viewer.get('slide'), dict) else {}
    shown = _number(slide.get('n'), 1)
    if shown:
        title = _text(slide.get('title'))
        out.append(f'On screen: {noun} {shown:g}' + (f', "{title}".' if title else '.'))
    fits = [fit for fit in (viewer.get('fits') or [])[:MAX_FITS] if isinstance(fit, dict) and _number(fit.get('n'), 1)]
    if fits:
        out.append(f'Each plan-set table, and how it fitted on the {noun}:')
        out += [f'- {noun} {fit["n"]:g} "{_text(fit.get("title"))}": {fit_words(fit, noun, scale)}.' for fit in fits]
    return '\n'.join(out)


def provide(deal, page):
    """The context provider: <export-viewer> when the browser sent the viewer's state, else nothing."""
    viewer = (page or {}).get('viewer')
    if not isinstance(viewer, dict):
        return ''
    file = viewer.get('file')
    if file == 'excel':
        return f'<export-viewer>\n{_workbook(viewer)}\n</export-viewer>'
    if file in WHAT:
        return f'<export-viewer>\n{_deck(viewer, file)}\n</export-viewer>'
    return ''
