"""A PDF's page text as the locator reads it: pypdf's text, with a fillable form's answers on their labels' lines
(E81, D-209; the old docscan/phi_screen.pdf_page_texts with `form_fields`). No OCR (D-122): a scanned page reads ''.

`page_texts(raw, on_page)` calls `on_page(number, total)` after each page, so a job can report progress and stop
between pages; whatever `on_page` raises ends the read. Nothing here logs or raises a page's words.
"""

from .. import pages

# Annotation flags that keep a field off the page (PDF 32000 12.5.3): hidden, no-view.
_HIDDEN_FLAGS = 2 | 32
# How far apart two runs' baselines may be and still share a printed row.
_ROW_TOLERANCE = 2.5


class Unreadable(Exception):
    """pypdf cannot open the file (corrupt, or encrypted with a password)."""


def page_texts(raw, on_page=None):
    """Each page's text in page order ('' for a page pypdf cannot extract). Raises Unreadable."""
    pdf = pages.reader(raw)
    if pdf is None:
        raise Unreadable
    total = len(pdf.pages)
    texts = []
    for number, page in enumerate(pdf.pages, start=1):
        texts.append(_page_text(page))
        if on_page:
            on_page(number, total)
    return texts


def _page_text(page):
    try:
        fields = _filled_fields(page)
        return _rows_with_fields(page, fields) if fields else page.extract_text() or ''
    except Exception:  # noqa: BLE001 - one bad page is unreadable, not fatal
        return ''


def _resolved(value):
    """An indirect PDF object as the object it points at."""
    return value.get_object() if hasattr(value, 'get_object') else value


def _inherited(field, key):
    """A field attribute, looked up through its /Parent chain (a widget often holds only its rectangle)."""
    node = field
    for _ in range(12):
        if node is None:
            return None
        value = node.get(key)
        if value is not None:
            return _resolved(value)
        node = _resolved(node.get('/Parent'))
    return None


def _field_text(value):
    if value is None:
        return ''
    if isinstance(value, list | tuple):
        return ', '.join(text for text in (_field_text(item) for item in value) if text)
    text = str(value)
    if text.startswith('/'):
        return ''  # a name (a checkbox state), not printed text
    return ' '.join(text.split())


def _filled_fields(page):
    """[(x0, y0, x1, y1, text)] for the page's visible, filled text and choice fields. Checkboxes print no text."""
    out = []
    for ref in _resolved(page.get('/Annots')) or []:
        try:
            annot = _resolved(ref)
            if annot.get('/Subtype') != '/Widget' or int(_resolved(annot.get('/F', 0)) or 0) & _HIDDEN_FLAGS:
                continue
            if _inherited(annot, '/FT') not in ('/Tx', '/Ch'):
                continue
            text = _field_text(_inherited(annot, '/V'))
            rect = [float(_resolved(v)) for v in _resolved(annot.get('/Rect')) or ()]
        except Exception:  # noqa: BLE001 - one broken field is no answer
            continue
        if not text or len(rect) != 4:
            continue
        x0, x1 = sorted((rect[0], rect[2]))
        y0, y1 = sorted((rect[1], rect[3]))
        out.append((x0, y0, x1, y1, text))
    return out


def _rows_with_fields(page, fields):
    """The page's printed runs and its field answers as rows, top to bottom, each row left to right. An answer joins
    the row of the nearest run to its left whose baseline sits inside the field's height, else a row of its own."""
    runs = []

    def visit(text, cm, tm, _font, _size):
        printed = ' '.join(str(text or '').split())
        if printed:
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            runs.append((y, x, printed))

    page.extract_text(visitor_text=visit)
    rows = []  # [baseline, [(x, words), ...]]
    for y, x, printed in sorted(runs, key=lambda run: (-run[0], run[1])):
        if rows and abs(rows[-1][0] - y) <= _ROW_TOLERANCE:
            rows[-1][1].append((x, printed))
        else:
            rows.append([y, [(x, printed)]])
    for x0, y0, _x1, y1, text in fields:
        best = None
        for row in rows:
            if not y0 - _ROW_TOLERANCE <= row[0] <= y1 + _ROW_TOLERANCE:
                continue
            left = [rx for rx, _words in row[1] if rx < x0]
            if left and (best is None or max(left) > best[0]):
                best = (max(left), row)
        if best:
            best[1][1].append((x0, text))
        else:
            rows.append([(y0 + y1) / 2, [(x0, text)]])
    rows.sort(key=lambda row: -row[0])
    return '\n'.join(' '.join(words for _x, words in sorted(row[1], key=lambda pair: pair[0])) for row in rows)
