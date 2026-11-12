"""A PDF's pages through pypdf (plan.md §3.1; E7, D52). No server OCR (D-122): a page without a text layer reads ''.

Pure: bytes in, numbers and strings out. Nothing here logs or raises a page's words; a file pypdf cannot open has no
page count (the old app kept such a file, and so does this one) and no page text.
"""

import io
import logging

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
    if pdf is None:
        return []
    texts = []
    for page in pdf.pages:
        try:
            texts.append(page.extract_text() or '')
        except Exception:  # noqa: BLE001 - one bad page is unscreenable, not fatal
            texts.append('')
    return texts
