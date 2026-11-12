"""The Export viewer's deck view: the client PowerPoint's slides, the PDF's pages and Paper, as they would download now
(plan.md §7.12, §8.14, §9.7; J107–J111, J114; J.6.3 `viewer/deck.py`, J.6.5; old Vantage 891f1b3
`pipeline/proposal_preview.py`, D-193, D-196).

One build serves all three files: the deck laid out once (`story.build.deck`, the downloads' own pass) and the PDF
drawn from it (`paint.pdf.draw`, the download's own bytes), sent whole as base64 for pdf.js to draw (J.6.12 ch21: one
build, one request), with the page log beside it saying what each page is. The PDF's pages are the PowerPoint's slides
one for one (J122), so the PowerPoint, PDF and Paper views page through the same copy and switching never builds again.
`paper` says how a page prints on US Letter (`paint.paper.summary`, J114).

A slide: {n, title, kind, line, continued, notes, chart, fit}. `kind` is `table` for a plan set's page (its title
names the line; its "(continued)" pages keep the line), `cover` for a whole page (the cover, a divider, the thank-you
page) and `page` for the rest; `notes` are its speaker notes (J111, the page log); `chart` marks a page whose premium
chart the PowerPoint draws as a native chart and the PDF as bars (J.5 B22); `fit` is the fit report on a plan set's
first slide (J110, `fit_report.of`).

Writes nothing (Q.3 #2), not even a `downloaded` row: a preview is not a download.
"""

import base64

from deals import clock

from ..layout import tokens
from ..paint import paper, pdf
from ..story import build
from . import fit_report

FILE = 'deck'
STYLE = 'presentation'  # the 16:9 Presentation format; Classic waits (J113, OQ8)


def _kind(page):
    if page['kind'] == 'full':
        return 'cover'
    return 'table' if page['line'] else 'page'


def slides(pages):
    """The page log: one row a recorded page, in order, a plan set's fit on its first slide."""
    out = []
    for page in pages:
        kind = _kind(page)
        out.append(
            {
                'n': page['n'],
                'title': page['title'],
                'kind': kind,
                'line': page['line'] if kind == 'table' else None,
                'continued': bool(page['continued']),
                'notes': list(page['notes']),
                'chart': any(frame.get('t') == 'bars' for frame in page['frames']),
                'fit': None,
            }
        )
    for run in fit_report.runs(pages):
        out[run[0]]['fit'] = fit_report.of(pages, run)
    return out


def preview(deal):
    """The deck view's copy of `deal`'s client deck as it would download now."""
    found = build.deck(deal)
    data = pdf.draw(found['pages'], found['title'], found['sources'])
    return {
        'file': FILE,
        'built_at': clock.now().isoformat(),
        'style': STYLE,
        # The viewer previews the draft downloads, and every file not issued carries Draft (OQ35; `story.facts`).
        'draft': True,
        'slides': slides(found['pages']),
        'paper': paper.summary(*tokens.DECK_SIZE),
        'pdf': base64.b64encode(data).decode('ascii'),
    }
