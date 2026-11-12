"""The files a read takes, and the ranges each is cut into (plan.md §10.4, §10.8; D48, D49, D52, D65; slice 18).

`FileIn` is one file as a read holds it: its bytes and what the person said it is (kind, role, carrier, lines), never
its name, which no step, error, note or result carries. `from_documents` loads a deal's files in upload order (D.6);
the Eval lane builds FileIns from its corpus. `plan(file)` cuts one file into ranges (`ranges.py`) and says which
pages it leaves out and why, or why it cannot be read at all (a failed part).
"""

import hashlib
from dataclasses import dataclass, field

from documents import kinds as document_kinds
from documents import pages, screening
from documents.locate.sheet_cells import visible_sheets
from documents.sheets import SheetError

from . import ranges


@dataclass
class FileIn:
    id: object  # the Document's id, or the corpus case's file name in the Eval lane
    raw: bytes
    extension: str
    kind: str = ''
    role: str = ''
    carrier: str = ''
    lines: list = field(default_factory=list)
    screened: tuple = ()  # pages the member-data screen flagged, when AI_MEMBER_DATA_SCREEN is on
    order: int = 0  # upload order: a later file's value wins a conflict (D57)
    document: object = None  # the Document, when there is one
    texts: list = None  # a PDF's page texts
    sheets: dict = None  # a workbook's visible sheets {name: rows}

    @property
    def hash(self):
        return hashlib.sha256(self.raw).hexdigest()[:16]

    @property
    def shape(self):
        return document_kinds.SHAPES.get(self.extension)

    @property
    def page_count(self):
        return len(self.texts or []) or 1


def _bytes(document):
    try:
        with document.file.open('rb') as handle:
            return handle.read()
    except (FileNotFoundError, OSError, ValueError):
        return None


def from_documents(documents):
    """[FileIn] for these Documents in upload order, and [failed part] for those whose bytes are gone."""
    files, failed = [], []
    ordered = sorted(documents, key=lambda doc: doc.id)  # upload order by id, never the clock, which steps back (D57)
    for order, document in enumerate(ordered):
        raw = _bytes(document)
        if raw is None:
            failed.append({'doc': document.id, 'where': 'the file', 'reason': 'missing'})
            continue
        files.append(
            FileIn(
                id=document.id,
                raw=raw,
                extension=document_kinds.extension(document.original_name),
                kind=document.kind,
                role=document.role or '',
                carrier=document.carrier or '',
                lines=list(document.lines or []),
                screened=tuple(screening.pages_left_out(document)),
                order=order,
                document=document,
            )
        )
    return files, failed


def plan(file, *, max_tokens, only_pages=None):
    """(ranges, left out {page: why}, failed part or None) for one file. `only_pages` scopes a PDF read (D65)."""
    shape = file.shape
    if shape == document_kinds.PDF:
        file.texts = pages.page_texts(file.raw)
        if not file.texts:
            return [], {}, {'doc': file.id, 'where': 'the file', 'reason': 'unreadable'}
        screened = set(file.screened)
        if only_pages:
            screened |= {page for page in range(1, len(file.texts) + 1) if page not in set(only_pages)}
        parts, out = ranges.pdf_ranges(file.texts, size=len(file.raw), screened=sorted(screened), max_tokens=max_tokens)
        if only_pages:
            out = {page: why for page, why in out.items() if page in set(only_pages)}  # scoped: not "left out"
        return parts, out, None
    if shape == document_kinds.SHEET:
        try:
            sheets = visible_sheets(f'file{file.extension}', file.raw)
        except SheetError:
            return [], {}, {'doc': file.id, 'where': 'the file', 'reason': 'unreadable'}
        file.sheets = dict(sheets)
        listed = [{'name': name, 'rows': rows, 'hidden': False} for name, rows in sheets]
        return ranges.sheet_ranges(listed, max_tokens=max_tokens), {}, None
    if shape == document_kinds.IMAGE:
        return [ranges.image_range()], {}, None
    return [], {}, {'doc': file.id, 'where': 'the file', 'reason': 'format'}


FAILED_WORDS = {
    'missing': 'the file is no longer stored',
    'unreadable': "the file can't be opened",
    'format': 'Claude does not read this kind of file',
    'truncated': 'the answer was too long, even for one page',
    'refused': 'Claude declined to read it',
    'error': 'Claude did not answer (busy, offline or too slow)',
    'account': "Claude's account refused the call",
    'over_cap': 'the run reached its cost cap first',
    'total_cap': 'the spending cap for all Claude calls was reached',
    'stopped': 'Stop was pressed first',
}
