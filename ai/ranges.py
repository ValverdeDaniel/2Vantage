"""How a file is cut into the parts one call reads (plan.md §10.4, §10.8; D49, D50, D52, O.3.3). Pure.

A PDF is read in page ranges, a workbook sheet by sheet as A1 grids, an image whole. Files are read whole (D-225,
OQ22), except that:
- a page carrying only the running header and footer (the lines printed on most pages, page numbers, nothing else)
  is always left out: it has nothing to read;
- the pages the member-data screen flagged are left out only while `AI_MEMBER_DATA_SCREEN` is on (the caller passes
  them as `screened`).
A range is sized by the output it should need: about 18 tokens a printed figure (the old page planner's rule), under a
quarter of `max_tokens`, at most 600 pages and 24 MB. A range whose answer is still cut off halves (`halve`); a single
page that is still cut off is a failed part. A page with no text layer (scanned) cannot be counted: it is estimated
at a fixed size and is never left out.
"""

import re
from dataclasses import dataclass, field

from .budget import (
    BASE_OUTPUT_TOKENS,
    CHARS_PER_TOKEN,
    IMAGE_INPUT_TOKENS,
    IMAGE_OUTPUT_TOKENS,
    PAGE_INPUT_TOKENS,
    TOKENS_PER_NUMBER,
)

PDF, SHEET, IMAGE = 'pdf', 'sheet', 'image'
MAX_PAGES = 600
MAX_BYTES = 24 * 1024 * 1024
SHEET_ROWS = 400  # a sheet longer than this is read in windows of rows
RUNNING_SHARE = 0.6  # a short line on this share of the pages (at least 3) is a running header or footer
RUNNING_LENGTH = 160  # a running line is never longer than this
RUNNING_LINES = 8  # a header-only page carries at most this many lines
HEADER_ONLY = 'header'
SCREENED = 'member_data'
LEFT_OUT_WORDS = {  # served on /api/meta/ (ai.left_out_words): why a page was not read
    HEADER_ONLY: 'only the running header and footer',
    SCREENED: 'member data (the screen is on)',
}

_FIGURE = re.compile(r'\d[\d,]*(?:\.\d+)?')
_PAGE_NUMBER = re.compile(r'^(?:page\s*)?\d+(?:\s*(?:of|/)\s*\d+)?$', re.I)


@dataclass(frozen=True)
class Range:
    """One call's part of a file. `pages` are 1-based file pages; `rows` a sheet's (first, last) 1-based rows."""

    kind: str
    pages: tuple = ()
    sheet: str = ''
    rows: tuple = ()
    est_input: int = 0
    est_output: int = 0
    extras: dict = field(default_factory=dict, compare=False, hash=False)

    @property
    def label(self):
        """For the fake client's key and the job's lines: 'p1-3', 'p2,5', 'sheet:Medical:1-200', 'image'."""
        if self.kind == SHEET:
            return f'sheet:{self.sheet}:{self.rows[0]}-{self.rows[1]}'
        if self.kind == IMAGE:
            return 'image'
        first, last = self.pages[0], self.pages[-1]
        if list(self.pages) == list(range(first, last + 1)):
            return f'p{first}-{last}' if last > first else f'p{first}'
        return 'p' + ','.join(str(page) for page in self.pages)

    def where(self):
        """In words for the job's lines and failed parts: 'pages 1–3', 'page 2', 'sheet 2, rows 1–200', 'the image'."""
        if self.kind == SHEET:
            return f'a sheet, rows {self.rows[0]}–{self.rows[1]}'
        if self.kind == IMAGE:
            return 'the image'
        if len(self.pages) == 1:
            return f'page {self.pages[0]}'
        return f'pages {self.pages[0]}–{self.pages[-1]}'


def _lines(text):
    return [' '.join(line.split()) for line in str(text or '').splitlines() if line.strip()]


def running_lines(texts):
    """Lines printed on most pages: the running header and footer."""
    readable = [set(_lines(text)) for text in texts if str(text or '').strip()]
    if len(readable) < 3:
        return set()
    counts = {}
    for lines in readable:
        for line in lines:
            counts[line] = counts.get(line, 0) + 1
    return {
        line for line, count in counts.items() if count >= RUNNING_SHARE * len(readable) and len(line) <= RUNNING_LENGTH
    }


def header_only(text, running):
    """A page with a text layer whose every line is a running line or a page number."""
    lines = _lines(text)
    return 0 < len(lines) <= RUNNING_LINES and all(line in running or _PAGE_NUMBER.match(line) for line in lines)


def output_tokens(text):
    """What reading this text should write: its figures, and a base for the structure."""
    if not str(text or '').strip():
        return IMAGE_OUTPUT_TOKENS
    return BASE_OUTPUT_TOKENS + TOKENS_PER_NUMBER * len(_FIGURE.findall(text))


def left_out(texts, screened=()):
    """{page: why} for the pages a read leaves out: header-only pages always, `screened` pages as given."""
    running = running_lines(texts)
    out = {page: SCREENED for page in screened}
    for number, text in enumerate(texts, start=1):
        if number not in out and header_only(text, running):
            out[number] = HEADER_ONLY
    return out


def pdf_ranges(texts, *, size=0, screened=(), max_tokens=128_000):
    """(ranges, {page: why left out}) for a PDF whose page texts are `texts` ('' for a page with no text layer).
    `size` is the file's bytes, shared out evenly to keep a range under 24 MB."""
    out = left_out(texts, screened)
    budget = max_tokens // 4
    page_bytes = size / max(len(texts), 1)
    ranges, pages, tokens = [], [], 0

    def close():
        if pages:
            ranges.append(_pdf_range(pages, texts))

    for number, text in enumerate(texts, start=1):
        if number in out:
            continue
        need = output_tokens(text)
        if pages and (
            tokens + need > budget
            or len(pages) >= MAX_PAGES
            or (len(pages) + 1) * page_bytes > MAX_BYTES
            or number != pages[-1] + 1
        ):
            close()
            pages, tokens = [], 0
        pages.append(number)
        tokens += need
    close()
    return ranges, out


def _pdf_range(pages, texts):
    output = sum(output_tokens(texts[page - 1]) for page in pages)
    return Range(PDF, pages=tuple(pages), est_input=PAGE_INPUT_TOKENS * len(pages), est_output=output)


def sheet_ranges(sheets, *, max_tokens=128_000):
    """One range per visible sheet with cells, in windows of rows: `sheets` is [{name, rows, hidden}] as
    documents.sheets.load_sheets gives them. Hidden sheets are never read (E82)."""
    ranges = []
    budget = max_tokens // 4
    for sheet in sheets:
        if sheet.get('hidden') or not sheet.get('rows'):
            continue
        rows = sheet['rows']
        start = 0
        while start < len(rows):
            end, tokens, chars = start, 0, 0
            while end < len(rows) and end - start < SHEET_ROWS:
                text = ' '.join(str(cell) for cell in rows[end] if cell not in (None, ''))
                need = output_tokens(text) - BASE_OUTPUT_TOKENS if text else 0
                if end > start and tokens + need > budget:
                    break
                tokens += need
                chars += len(text) + 8 * len(rows[end])
                end += 1
            ranges.append(
                Range(
                    SHEET,
                    sheet=sheet['name'],
                    rows=(start + 1, end),
                    est_input=int(chars / CHARS_PER_TOKEN) + 50,
                    est_output=tokens + BASE_OUTPUT_TOKENS,
                )
            )
            start = end
    return ranges


def image_range():
    return Range(IMAGE, est_input=IMAGE_INPUT_TOKENS, est_output=IMAGE_OUTPUT_TOKENS)


def halve(part):
    """Two ranges for one whose answer was cut off, or None when it cannot be split (one page, one row, an image)."""
    if part.kind == PDF and len(part.pages) > 1:
        middle = len(part.pages) // 2
        first, second = part.pages[:middle], part.pages[middle:]
        return [
            Range(
                PDF,
                pages=first,
                est_input=part.est_input * len(first) // len(part.pages),
                est_output=part.est_output // 2,
            ),
            Range(
                PDF,
                pages=second,
                est_input=part.est_input * len(second) // len(part.pages),
                est_output=part.est_output // 2,
            ),
        ]
    if part.kind == SHEET and part.rows[1] > part.rows[0]:
        first, last = part.rows
        middle = (first + last) // 2
        return [
            Range(
                SHEET,
                sheet=part.sheet,
                rows=(first, middle),
                est_input=part.est_input // 2,
                est_output=part.est_output // 2,
            ),
            Range(
                SHEET,
                sheet=part.sheet,
                rows=(middle + 1, last),
                est_input=part.est_input // 2,
                est_output=part.est_output // 2,
            ),
        ]
    return None
