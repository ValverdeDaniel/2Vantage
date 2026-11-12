"""A PDF's pages as searchable figures and text, built once per file (E81; the old docscan/locate.PdfIndex). Pure.

The recorded page is searched first, then the others nearest first. A common figure needs a plan or label word on its
line; the reader's own line, printed on the page it cited, outranks any other page (D-164). A scanned page cannot say
(NOCHECK), and a file whose text layer reads as nonsense turns its absences into NOCHECK (`guard_text_layer`).
"""

import bisect
import re
from dataclasses import dataclass, field

from .fold import as_float, as_number, compact, figures_in, fold, is_common, words
from .query import (
    ABSENT,
    DERIVED,
    FOUND,
    MAX_PAGES,
    NOCHECK,
    WEAK,
    Located,
    figures,
    first_strong,
    missing,
    reader_line,
    text_forms,
)

# Fewer characters than this and a page is an image as far as text goes (screening.MIN_SCREENABLE_TEXT).
MIN_PAGE_TEXT = 25
# More than this share of a file's checkable values absent, over at least GUARD_MIN_VALUES of them, and the text layer
# itself is suspect (custom font encodings extract as plausible-looking nonsense).
GUARD_SHARE = 0.5
GUARD_MIN_VALUES = 8


@dataclass
class _Page:
    number: int
    text: str  # folded
    lines: list  # folded lines
    figures: dict = field(default_factory=dict)  # canonical -> [line index]
    sorted_values: list = field(default_factory=list)  # [(float, line index)]
    compact_text: str = ''


def _index_lines(lines):
    found, values = {}, []
    for i, line in enumerate(lines):
        for figure in figures_in(line):
            found.setdefault(figure, []).append(i)
            number = as_float(figure)
            if number is not None:
                values.append((number, i))
    values.sort()
    return found, values


def _located(state_for, page, hits, via, figure):
    return Located(state_for, page=page, hits=hits, via=via, printed='' if via == 'number' else figure)


class PdfIndex:
    def __init__(self, texts):
        self.pages = []
        for number, raw in enumerate(texts, start=1):
            lines = [line for line in (fold(text) for text in str(raw or '').splitlines()) if line]
            text = ' '.join(lines)
            found, values = _index_lines(lines)
            self.pages.append(_Page(number, text, lines, found, values, re.sub(r'[^a-z0-9]', '', text)))
        self.no_text = {page.number for page in self.pages if len(page.text) < MIN_PAGE_TEXT}
        self._orders = {}

    @property
    def page_count(self):
        return len(self.pages)

    def _order(self, recorded):
        """The recorded page first, then the rest nearest first (kept per recorded page)."""
        cached = self._orders.get(recorded)
        if cached is None:
            pages = [page for page in self.pages if page.number not in self.no_text]
            if recorded:
                pages.sort(key=lambda page: (abs(page.number - recorded), page.number))
            cached = self._orders[recorded] = pages
        return cached

    def _figure_lines(self, page, figure, tolerance):
        if not tolerance:
            return page.figures.get(figure, [])
        target = as_float(figure)
        if target is None:
            return []
        lo = bisect.bisect_left(page.sorted_values, (target - tolerance, -1))
        hi = bisect.bisect_right(page.sorted_values, (target + tolerance, 1 << 30))
        return [line for _value, line in page.sorted_values[lo:hi]]

    def _find_figure(self, query, figure, via):
        anchors = {word for anchor in query.anchors for word in words(anchor)}
        weak = None
        for page in self._order(query.page):
            lines = self._figure_lines(page, figure, query.tolerance)
            if not lines:
                continue
            state = FOUND if via == 'number' else DERIVED
            if not is_common(figure):
                return _located(state, page.number, len(lines), via, figure)
            pinned = [i for i in lines if anchors & words(page.lines[i])]
            if pinned:
                return _located(state, page.number, len(pinned), via, figure)
            weak = weak or Located(WEAK, page=page.number, hits=len(lines), via=via)
        return weak

    def _snippet_page(self, query):
        """The cited page, when it prints the reader's own line, else None."""
        line = compact(reader_line(query.snippet))
        if len(line) < 6 or not query.page or query.page in self.no_text or not 1 <= query.page <= self.page_count:
            return None
        page = self.pages[query.page - 1]
        return page if line in page.compact_text else None

    def _snippet_pin(self, query):
        """A figure on the reader's own line, printed on the page it cited: FOUND there (DERIVED for a rule's figure
        or wording), common figure or not (D-164)."""
        page = self._snippet_page(query)
        if page is None:
            return None
        folded = fold(reader_line(query.snippet))
        printed = set(figures_in(folded))
        for figure, via in figures(query):
            if figure and figure in printed:
                lines = self._figure_lines(page, figure, query.tolerance)
                if lines:
                    return _located(FOUND if via == 'number' else DERIVED, page.number, len(lines), via, figure)
        for wording, via in query.wordings:
            if fold(wording) in folded:
                return Located(DERIVED, page=page.number, hits=1, via=via, printed=fold(wording))
        return None

    def _find_text(self, query, target, via):
        if len(target) < 3:
            return None
        pattern = re.compile(r'(?<![a-z0-9])' + re.escape(target) + r'(?![a-z0-9])')
        for page in self._order(query.page):
            hits = len(pattern.findall(page.text))
            if hits:
                return Located(FOUND, page=page.number, hits=hits, via=via)
        return None

    def _find_words(self, query, wording, via):
        """A figure the reader wrote for printed words ("No charge" records 0): DERIVED beside an anchor, else WEAK."""
        target = fold(wording)
        anchors = {word for anchor in query.anchors for word in words(anchor)}
        weak = None
        for page in self._order(query.page):
            lines = [i for i, line in enumerate(page.lines) if target in line]
            if not lines:
                continue
            pinned = [i for i in lines if anchors & words(page.lines[i])]
            if pinned:
                return Located(DERIVED, page=page.number, hits=len(pinned), via=via, printed=target)
            weak = weak or Located(WEAK, page=page.number, hits=len(lines), via=via)
        return weak

    def _find_code(self, query):
        target = compact(query.value)
        if len(target) < 4:
            return None
        for page in self._order(query.page):
            hits = page.compact_text.count(target)
            if hits:
                return Located(FOUND, page=page.number, hits=hits, via='code')
        return None

    def _find_numbers_in_text(self, query):
        """A worded value holding figures ("$20 copay after deductible"): found when every figure is on one page."""
        wanted = figures_in(fold(query.value))
        if not wanted:
            return None
        for page in self._order(query.page):
            if all(figure in page.figures for figure in wanted):
                hits = min(len(page.figures[figure]) for figure in wanted)
                return Located(FOUND, page=page.number, hits=hits, via='figures')
        return None

    def _find_number(self, query):
        pinned = self._snippet_pin(query)
        if pinned:
            return pinned
        found = first_strong(self._find_figure(query, figure, via) for figure, via in figures(query))
        if found is None or found.state == WEAK:
            worded = first_strong(self._find_words(query, wording, via) for wording, via in query.wordings)
            found = first_strong([worded, found])
        if found and found.page and found.page != query.page and self._snippet_page(query) is not None:
            # The reader's line is on the page it cited but does not hold the figure (it read "None" as 0): the same
            # figure on another page is not this value. Weak, on the reader's page, so a person looks (D-164).
            return Located(WEAK, page=query.page, why='reworded')
        return found

    def locate(self, query):
        if self.page_count > MAX_PAGES:
            return Located(NOCHECK, why='too_large')
        if len(self.no_text) == self.page_count:
            return Located(NOCHECK, why='no_text')
        if query.page and query.page in self.no_text:
            return Located(NOCHECK, page=query.page, why='no_text')  # a scanned page: only the eye (or OCR) can look
        if query.kind == 'code':
            found = self._find_code(query)
        elif as_number(query.value) is not None:
            found = self._find_number(query)
        elif len(fold(query.value)) < 3:
            return Located(NOCHECK, why='short')
        else:
            found = None
            for form in text_forms(query.value):
                found = self._find_text(query, form, 'text')
                if found:
                    break
            found = found or self._find_numbers_in_text(query)
        if found:
            return found
        absent = missing(query)
        if absent.state == ABSENT and self.no_text and not query.page:
            # No page cited and some pages are images: still ABSENT, but the caller can tell (D-151).
            return Located(ABSENT, why='image_pages')
        return absent


def guard_text_layer(results):
    """A file whose text layer reads as nonsense makes every value look absent. Past GUARD_SHARE of its checkable
    values (and at least GUARD_MIN_VALUES of them), the absences become NOCHECK 'text_layer'. Changes `results` (a
    list of Located) in place and returns it."""
    checkable = [result for result in results if result.state != NOCHECK]
    absent = [result for result in checkable if result.state == ABSENT]
    if len(checkable) >= GUARD_MIN_VALUES and len(absent) > GUARD_SHARE * len(checkable):
        for result in absent:
            result.state, result.why = NOCHECK, 'text_layer'
    return results
