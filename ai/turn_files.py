"""The files a chat turn sees (plan.md §10.6; D82, D84; slice 24).

- **Attached** to the person's message: at most three of the deal's files, each whole when it has at most 100 pages
  (a PDF as one document block, a workbook as A1 grids of its visible cells, an image whole), before the words of the
  newest message, inside its cache breakpoint, so every round of the turn reads them from the cache. A longer file is
  named instead, to read with `read_document`.
- **`read_document`** (D84: a file not attached stays reachable): the text of some of a file's pages, at most 40
  pages and 60,000 characters, or a workbook's visible cells.
Files that list members (census, questionnaire and the other PHI kinds) are never put in a chat: their reads wait
for their own reviews (§10.8; D111 is deferred). Nothing here is stored: the bytes live for the call. File names are
never sent (D55).
"""

from documents import kinds as document_kinds
from documents import pages as document_pages
from documents.models import Document

from . import content, ranges, read_files, registry, tools

MAX_ATTACHED = 3
ATTACHED_PAGES = 100
READ_PAGES = 40
READ_CHARS = 60_000
PAGE_TOKENS = 2000  # a PDF page sent as a document block (budget.PAGE_INPUT_TOKENS)

MEMBER_FILE = 'That file lists members, so it is not read in a chat: its own review reads it.'
NOT_HERE = 'There is no file with that id on this deal.'
PICTURE = 'That file is a picture: ask the producer to attach it to a message so you can see it.'


def readable(document):
    return document.kind not in document_kinds.PHI_KINDS


def _sheet_text(file, limit):
    parts, used = [], 0
    for name, rows in (file.sheets or {}).items():
        block = content.grid(name, rows)
        if used + len(block) > limit:
            parts.append(f'(Sheet "{name}" and any after it were cut at {limit:,} characters.)')
            break
        parts.append(block)
        used += len(block)
    return '\n\n'.join(parts)


def _label(document):
    return f'File {document.id} ({document_kinds.label(document.kind)})'


def blocks(documents):
    """(content blocks, estimated input tokens, lines for the words) for the files attached to the newest message."""
    files, _failed = read_files.from_documents([doc for doc in documents if readable(doc)][:MAX_ATTACHED])
    out, tokens, said = [], 0, []
    for file in files:
        label = _label(file.document)
        _parts, _out, failure = read_files.plan(file, max_tokens=128_000)
        if failure:
            said.append(f'{label} could not be opened.')
            continue
        if file.shape == document_kinds.PDF:
            if file.page_count > ATTACHED_PAGES:
                said.append(f'{label} has {file.page_count} pages, too many to attach: read it with read_document.')
                continue
            whole = list(range(1, file.page_count + 1))
            out.append({'type': 'text', 'text': f'{label}, {file.page_count} pages:'})
            out.append(content.blocks(file, _Whole(ranges.PDF, whole), '')[0])
            tokens += PAGE_TOKENS * file.page_count
        elif file.shape == document_kinds.SHEET:
            text = _sheet_text(file, READ_CHARS)
            out.append({'type': 'text', 'text': f'{label}, a workbook:\n{text}'})
            tokens += len(text) // 3
        else:
            out.append({'type': 'text', 'text': f'{label}, a picture:'})
            out.append(content.blocks(file, _Whole(ranges.IMAGE, [1]), '')[0])
            tokens += 1600
    return out, tokens, said


class _Whole:
    """A whole file as content.blocks takes a range."""

    def __init__(self, kind, pages):
        self.kind, self.pages = kind, pages


def read_document(turn, data):
    document_id = tools.integer(data.get('document_id'), 'document_id')
    first = tools.integer(data.get('first_page', 0) or 0, 'first_page')
    last = tools.integer(data.get('last_page', 0) or 0, 'last_page')
    document = Document.objects.filter(deal_id=turn.deal.id, pk=document_id).first()
    if document is None:
        raise tools.ToolRefused(NOT_HERE)
    if not readable(document):
        raise tools.ToolRefused(MEMBER_FILE)
    files, _failed = read_files.from_documents([document])
    if not files:
        raise tools.ToolRefused('That file is no longer stored.')
    file = files[0]
    if file.shape == document_kinds.SHEET:
        _parts, _out, failure = read_files.plan(file, max_tokens=128_000)
        if failure:
            raise tools.ToolRefused("That file can't be opened.")
        return f'{_label(document)}, a workbook:\n{_sheet_text(file, READ_CHARS)}'
    if file.shape != document_kinds.PDF:
        raise tools.ToolRefused(PICTURE)
    texts = document_pages.page_texts(file.raw) or []
    if not texts:
        raise tools.ToolRefused("That file can't be opened.")
    first = max(1, first or 1)
    last = min(len(texts), last or len(texts), first + READ_PAGES - 1)
    if first > len(texts):
        raise tools.ToolRefused(f'That file has {len(texts)} pages.')
    parts, used = [f'{_label(document)}, pages {first}–{last} of {len(texts)} (text only; tables may wrap):'], 0
    for number in range(first, last + 1):
        page = f'--- page {number} ---\n{texts[number - 1] or "(no text on this page)"}'
        if used + len(page) > READ_CHARS:
            parts.append(f'(Cut at {READ_CHARS:,} characters: ask for page {number} on.)')
            break
        parts.append(page)
        used += len(page)
    return '\n'.join(parts)


READ_DOCUMENT = registry.Tool(
    name='read_document',
    owner='ai',
    order=10,
    description=(
        "The text of some pages of one of the deal's files (by its id in <documents>): a file not attached to this "
        "message, or pages to read closely. first_page and last_page are the PDF's own page numbers; 0 and 0 read "
        'from the start, at most 40 pages. A workbook answers its visible cells.'
    ),
    schema=tools.schema(
        {
            'document_id': {'type': 'integer'},
            'first_page': {'type': 'integer'},
            'last_page': {'type': 'integer'},
        }
    ),
    run=read_document,
)
