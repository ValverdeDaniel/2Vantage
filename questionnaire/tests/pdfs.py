"""Reading the questionnaire PDFs back for the tests: every string drawn on a page with where it was drawn, through
pypdf's own text machinery (so the stamped face's ToUnicode map is proved too), and the AcroForm's field values."""

from io import BytesIO

from pypdf import PdfReader


def reader(data):
    return PdfReader(BytesIO(data))


def placed(page):
    """[(x, y, text, font name)] for every string drawn on a page."""
    hits = []

    def visit(text, _cm, tm, font, _size):
        if text.strip():
            name = str(font.get('/BaseFont', '')) if hasattr(font, 'get') else str(font)
            hits.append((round(tm[4], 2), round(tm[5], 2), text.strip(), name))

    page.extract_text(visitor_text=visit)
    return hits


def texts(data):
    """Every page's text, joined."""
    return '\n'.join(page.extract_text() or '' for page in reader(data).pages)


def inside(data, rect, expected):
    """Whether `expected` is drawn inside the (page, x, y, w, h) box: any occurrence counts."""
    page, x, y, w, h = rect[:5]
    found = [(px, py) for px, py, text, _font in placed(reader(data).pages[page]) if text == expected]
    return any(x - 1 <= px <= x + w and y - 2 <= py <= y + h + 2 for px, py in found)


def drawn(data, expected, page=None):
    """Whether `expected` is drawn anywhere (on one page, or any)."""
    pages = reader(data).pages
    chosen = [pages[page]] if page is not None else pages
    return any(text == expected for one in chosen for _x, _y, text, _font in placed(one))


def fields(data):
    """{field name: value} of an AcroForm."""
    return {name: field.get('/V') for name, field in (reader(data).get_fields() or {}).items()}
