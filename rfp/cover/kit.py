"""The cover page's reportlab kit (plan.md §9.9; K102): the theme from the agency's brand colour, the paragraph styles,
the letterhead (logo left, agency contact right) and the label/value tables. Ported from old Vantage 891f1b3
`pipeline/pdf_kit.py` (`Theme`, `theme_for`, `letter_styles`, `logo_letterhead`, `esc`) and `rfp_cover_pdf.py`.

K.6 names `deals/pdfkit.py` as this kit's home; rfp is its only user so far, so it lives beside the cover and moves left
when a second builder needs it. Stateless: the theme travels as a parameter, never a module global.
"""

import io
from dataclasses import dataclass, replace
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle

BUNDLED_LOGO = Path(__file__).resolve().parents[2] / 'assets' / 'images' / 'logos' / 'agency-logo.png'


@dataclass(frozen=True)
class Theme:
    navy: object = colors.HexColor('#173a63')
    ink: object = colors.HexColor('#1c2430')
    ink2: object = colors.HexColor('#5b6573')
    border: object = colors.HexColor('#e6e8ec')


DEFAULT_THEME = Theme()


def theme_for(brand_color):
    """The house theme with the agency's brand colour as its navy; an unreadable colour keeps the default."""
    try:
        return replace(DEFAULT_THEME, navy=colors.HexColor(brand_color))
    except (TypeError, ValueError):
        return DEFAULT_THEME


def esc(value):
    return _xml_escape(str(value or ''))


def styles_for(theme):
    ss = getSampleStyleSheet()
    body = ParagraphStyle('cv_body', parent=ss['Normal'], fontSize=9.5, leading=13, spaceAfter=8)
    small = ParagraphStyle('cv_small', parent=ss['Normal'], fontSize=8, leading=10, textColor=theme.ink2)
    return {
        'body': body,
        'small': small,
        'brand': ParagraphStyle('cv_brand', parent=ss['Heading1'], textColor=theme.navy, fontSize=14, spaceAfter=0),
        'brand_sub': ParagraphStyle('cv_sub', parent=ss['Normal'], textColor=theme.ink2, fontSize=8.5, spaceAfter=14),
        'h2': ParagraphStyle('cv_h2', parent=ss['Heading3'], textColor=theme.navy, fontSize=11.5, spaceBefore=12,
                             spaceAfter=4),  # fmt: skip
        'label': ParagraphStyle('cv_label', parent=small, fontSize=8, leading=10),
        'value': ParagraphStyle('cv_value', parent=body, fontSize=9, leading=11.5, spaceAfter=0),
        'th': ParagraphStyle('cv_th', parent=body, fontSize=8.5, leading=10.5, spaceAfter=0, textColor=colors.white,
                             fontName='Helvetica-Bold'),  # fmt: skip
        'box': ParagraphStyle('cv_box', parent=body, fontSize=9, leading=10, spaceAfter=0, alignment=1,
                              fontName='Helvetica-Bold'),  # fmt: skip
        'title': ParagraphStyle('cv_title', parent=ss['Heading1'], textColor=theme.navy, fontSize=17, leading=21,
                                spaceAfter=2),  # fmt: skip
    }


def logo_bytes(agency):
    """The agency's uploaded logo, else the bundled one; None when neither can be read (the name prints instead)."""
    try:
        if agency.logo:
            with agency.logo.open('rb') as handle:
                return handle.read()
        return BUNDLED_LOGO.read_bytes()
    except OSError:
        return None


def letterhead(styles, theme, logo, agency_lines, *, width, logo_height=0.5 * inch):
    """The logo on the left and the agency's contact block on the right; a missing or unreadable logo prints the
    agency's name instead, so the page always has a letterhead."""
    found = [str(line).strip() for line in agency_lines if str(line or '').strip()]
    name, rest = (found[0], found[1:]) if found else ('', [])
    right_style = ParagraphStyle('lh_right', parent=styles['small'], alignment=2, leading=10.5)
    right = [Paragraph(f'<b>{esc(name)}</b>', right_style)] if name else []
    right += [Paragraph(esc(line), right_style) for line in rest]
    picture = None
    if logo:
        try:
            img_w, img_h = ImageReader(io.BytesIO(logo)).getSize()
            if img_w and img_h:
                picture = Image(io.BytesIO(logo), width=logo_height * img_w / img_h, height=logo_height)
                picture.hAlign = 'LEFT'
        except Exception:  # noqa: BLE001 - a broken picture must not lose the page; the name prints instead
            picture = None
    left = picture or Paragraph(esc(name or 'Request for Proposal'), styles['brand'])
    head = Table([[left, right]], colWidths=[width * 0.55, width * 0.45])
    head.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LINEBELOW', (0, 0), (-1, 0), 1.2, theme.navy),
            ]
        )
    )
    return [head, Spacer(1, 12)]


def pairs_table(pairs, styles, theme, width):
    """Label/value pairs, two to a row: the request forms' own shape."""
    cells = [(Paragraph(esc(k), styles['label']), Paragraph(esc(v), styles['value'])) for k, v in pairs]
    if len(cells) % 2:
        cells.append((Paragraph('', styles['label']), Paragraph('', styles['value'])))
    rows = [[*cells[i], *cells[i + 1]] for i in range(0, len(cells), 2)]
    col = width / 2
    table = Table(rows, colWidths=[col * 0.42, col * 0.58, col * 0.42, col * 0.58])
    table.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (0, 0), (-1, -1), 0.4, theme.border),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table
