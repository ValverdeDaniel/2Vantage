"""Find a value in its own file, in code: no AI, no cost (plan.md §10.7; E81–E84, D-122; the old docscan/locate.py).

Given a file's bytes and the values said to come from it, the locator answers where each is printed, or that it is
not (`query.py` names the five states). It reads a PDF's text layer through pypdf (form answers included, D-209) and
a workbook's visible cells only (E82); it never OCRs, approves anything or changes what was recorded. An answer names
a page, a sheet and a cell, a count and a reason code, never the file's text.

    index, why = open_index(filename, raw, page_count, on_page)   # once per file
    results = locate_all(index, why, queries)                     # one Located per Query (or Located passed through)

`ai/check.py` runs it in the `locate` job; owners build the queries (their fields' rules) and store each answer as
`loc` on the value (O.3.1). Pure, apart from `kinds`, `pages` and `sheets` in this app.
"""

from .. import kinds
from ..sheets import SheetError
from .pdf_index import PdfIndex, guard_text_layer
from .pdf_text import Unreadable, page_texts
from .query import (
    ABSENT,
    DERIVED,
    FILE_REASONS,
    FOUND,
    MAX_PAGES,
    NOCHECK,
    STATES,
    VERSION,
    WEAK,
    Located,
    Query,
    reader_line,
)
from .sheet_cells import TooLarge, visible_sheets
from .sheet_index import SheetIndex


def open_index(filename, raw, page_count=None, on_page=None):
    """(index, '') for a file the locator can search, else (None, why): image, format, too_large or unreadable.
    `on_page(number, total)` runs after each PDF page is read; whatever it raises ends the read."""
    shape = kinds.shape_of(filename)
    if shape == kinds.IMAGE:
        return None, 'image'
    if shape not in (kinds.PDF, kinds.SHEET):
        return None, 'format'
    if shape == kinds.PDF:
        if page_count and page_count > MAX_PAGES:
            return None, 'too_large'
        try:
            return PdfIndex(page_texts(raw, on_page)), ''
        except Unreadable:
            return None, 'unreadable'
    try:
        return SheetIndex(visible_sheets(filename, raw)), ''
    except TooLarge:
        return None, 'too_large'
    except SheetError:
        return None, 'unreadable'


def locate_all(index, why, queries):
    """One Located per entry of `queries`: a Query is searched in `index`, a Located (an owner's "nothing to find")
    passes through; with no index every query is NOCHECK `why`. A PDF's absences pass the text-layer guard."""
    results = []
    for query in queries:
        if isinstance(query, Located):
            results.append(query)
        elif index is None:
            results.append(Located(NOCHECK, why=why))
        else:
            results.append(index.locate(query))
    if isinstance(index, PdfIndex):
        guard_text_layer(results)
    return results


__all__ = [
    'ABSENT',
    'DERIVED',
    'FILE_REASONS',
    'FOUND',
    'MAX_PAGES',
    'NOCHECK',
    'STATES',
    'VERSION',
    'WEAK',
    'Located',
    'PdfIndex',
    'Query',
    'SheetIndex',
    'guard_text_layer',
    'locate_all',
    'open_index',
    'reader_line',
]
