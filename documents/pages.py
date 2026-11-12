"""A PDF's pages through pypdf (plan.md §3.1; E7, D52). No server OCR (D-122): a page without a text layer reads ''.

Pure: bytes in, numbers and strings out. Nothing here logs or raises a page's words; a file pypdf cannot open has no
page count (the old app kept such a file, and so does this one) and no page text.
"""

import io
import logging
import re

# pypdf names objects, never page text, in its warnings; quiet them so a carrier's odd PDF never fills the log.
logging.getLogger('pypdf').setLevel(logging.ERROR)


def reader(raw):
    """A PdfReader over the bytes, or None when pypdf cannot open them (corrupt, or encrypted without a password)."""
    from pypdf import PdfReader

    try:
        pdf = PdfReader(io.BytesIO(raw), strict=False)
        if pdf.is_encrypted and not pdf.decrypt(''):
            return None
        len(pdf.pages)  # touches the page tree, where a broken file fails
        return pdf
    except Exception:  # noqa: BLE001 - an unreadable PDF has no pages to count
        return None


def page_count(raw):
    pdf = reader(raw)
    return len(pdf.pages) if pdf is not None else None


def page_texts(raw):
    """Each page's extracted text, in page order ('' for a page pypdf cannot extract). [] for an unreadable file."""
    pdf = reader(raw)
    return _texts(pdf) if pdf is not None else []


def _texts(pdf):
    texts = []
    for page in pdf.pages:
        try:
            texts.append(page.extract_text() or '')
        except Exception:  # noqa: BLE001 - one bad page is unscreenable, not fatal
            texts.append('')
    return texts


# Printed page numbers (E94; the old ai/page_labels.py, D-149): a carrier's packet often numbers its pages from 1 again
# some pages into the file, so "the rates on page 5" means a PDF page further on. A bare number on a page's first or
# last lines ("5", "Page 5", "Page 11 of 11", "5 - Confidential", "Confidential - 5") is its printed number; the PDF's
# own /PageLabels win when it declares them. Numbers only: no page text is kept.
MAX_LABEL_PAGES = 400
_HEAD_TAIL_LINES = 3
_PRINTED = (
    re.compile(r'^page\s+(\d{1,3})(?:\s+of\s+\d{1,3})?$', re.IGNORECASE),
    re.compile(r'^(\d{1,3})$'),
    re.compile(r'^(\d{1,3})\s+[-–—|]\s+\S'),
    re.compile(r'\S\s+[-–—|]\s+(\d{1,3})$'),
    re.compile(r'^page\s+(\d{1,3})\s+of\s+\d{1,3}\b', re.IGNORECASE),
)


def _printed_number(text):
    lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
    for line in lines[-_HEAD_TAIL_LINES:][::-1] + lines[:_HEAD_TAIL_LINES]:
        if len(line) > 80 and not line[:3].strip().isdigit():
            continue
        for pattern in _PRINTED:
            found = pattern.search(line)
            if found and 1 <= int(found.group(1)) <= 999:
                return int(found.group(1))
    return None


def printed_labels(raw, texts=None):
    """{"<pdf page>": "<printed number>"} for the pages whose printed number differs from their place in the PDF; {}
    when they agree, nothing is printed, the file is not a readable PDF or it has over 400 pages. `texts`: the page
    texts when the caller has them already."""
    pdf = reader(raw)
    if pdf is None or len(pdf.pages) > MAX_LABEL_PAGES:
        return {}
    try:
        declared = list(pdf.page_labels) if '/PageLabels' in pdf.trailer['/Root'] else None
    except Exception:  # noqa: BLE001 - a malformed label tree is no map at all
        declared = None
    if declared and len(declared) == len(pdf.pages):
        pairs = enumerate(declared, start=1)
        return {str(n): str(label) for n, label in pairs if str(label).isdigit() and int(label) != n}
    out = {}
    for n, text in enumerate(texts if texts is not None else _texts(pdf), start=1):
        number = _printed_number(text)
        if number is not None and number != n:
            out[str(n)] = str(number)
    return out
