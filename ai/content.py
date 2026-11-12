"""What one call is shown (plan.md §10.4; D49, D.6): a file's range as content blocks, then the per-call note.

- A PDF range goes as a PDF of just those pages (the whole file when the range is the whole file), base64, with a
  page map in words so every value names the file's own page.
- A sheet window goes as an A1 grid of its visible cells (hidden sheets, rows and columns read as blank, E82), so
  every value names its cell ("Medical!C7").
- An image goes whole.
Files are never written anywhere: the bytes stay in memory for the call. Pure, apart from pypdf.
"""

import base64
import io

from documents.sheets import column_letter

from . import ranges

MEDIA_TYPES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}


def _b64(raw):
    return base64.standard_b64encode(raw).decode('ascii')


def pdf_part(raw, pages, total):
    """The bytes of a PDF holding only `pages` (1-based), or the file itself when that is every page."""
    if list(pages) == list(range(1, total + 1)):
        return raw
    from pypdf import PdfReader, PdfWriter

    source = PdfReader(io.BytesIO(raw), strict=False)
    writer = PdfWriter()
    for page in pages:
        writer.add_page(source.pages[page - 1])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def page_map(pages, total):
    """The words that tie the pages shown to the file's own page numbers."""
    if list(pages) == list(range(1, total + 1)):
        return f'This is the whole file, {total} page{"s" if total != 1 else ""}. Give each value its page number.'
    first, last = pages[0], pages[-1]
    shown = f'{first}–{last}' if list(pages) == list(range(first, last + 1)) else ', '.join(str(p) for p in pages)
    return (
        f"This part holds only some of the file's {total} pages: its pages {shown}, in that order (the first page "
        f"shown is the file's page {pages[0]}). Give each value the FILE's page number from that list."
    )


def grid(name, rows, first_row=1):
    """A sheet window as text: one line per row with its non-empty cells as A1 references."""
    lines = [f'Workbook sheet "{name}", rows {first_row}–{first_row + len(rows) - 1}. Empty cells are left out.']
    for offset, row in enumerate(rows):
        number = first_row + offset
        cells = [f'{column_letter(col)}{number}: {value}' for col, value in enumerate(row) if str(value).strip()]
        if cells:
            lines.append(f'{number} | ' + ' | '.join(cells))
    return '\n'.join(lines)


def blocks(file, part, note):
    """The user turn's content for one range of `file` (reading.FileIn): the file blocks, then the note."""
    if part.kind == ranges.PDF:
        data = pdf_part(file.raw, part.pages, file.page_count)
        return [
            {'type': 'document', 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': _b64(data)}},
            {'type': 'text', 'text': page_map(part.pages, file.page_count) + '\n\n' + note},
        ]
    if part.kind == ranges.SHEET:
        rows = file.sheets[part.sheet][part.rows[0] - 1 : part.rows[1]]
        text = grid(part.sheet, rows, part.rows[0])
        return [
            {'type': 'text', 'text': text},
            {'type': 'text', 'text': f'Give each value its cell as "{part.sheet}!B7".\n\n{note}'},
        ]
    media = MEDIA_TYPES.get(file.extension, 'image/png')
    return [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': media, 'data': _b64(file.raw)}},
        {'type': 'text', 'text': 'This file is one picture: give each value page 1.\n\n' + note},
    ]
