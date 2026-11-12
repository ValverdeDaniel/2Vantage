"""The page after the carrier's form, for what its boxes cannot hold (G57, G59; G60's helpers).

Florida Blue's flat form shows one plan row and one condition row, and some answers are too long for their boxes; the
Warner form has no field for its detail lines. Those print here, under their section's heading, in the carrier's own
blue: a row keeps its number on our form ("Plan 2"), a yes/no prints as a ticked pair, a blank as an em dash. The
footer names the form, the group and the date, and carries DRAFT until the officer signs. Built from the old
replica's helpers, the replica itself dropped (G60). Ported from old Vantage 891f1b3 (`questionnaire_pdf.py`).
"""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from deals import clock

from ..engine.spec import block_fields, get_block
from ..engine.walk import visible_fields
from . import display, fonts

# The blue Florida Blue fills its section bands with, from the printed form's content stream.
BAND_BLUE = colors.CMYKColor(0.83874, 0.31928, 0.033112, 0)
INK = colors.HexColor('#1c2430')
HAIRLINE = colors.HexColor('#c8ccd4')
FOOTER_HEIGHT = 34
MARGIN = 0.35 * inch
TITLE = 'Attachment — continued from the carrier form'


def _style(name, size, leading, color=INK, font='Helvetica', **extra):
    return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading, textColor=color, **extra)


STYLES = {
    'title': _style('qTitle', 15, 18, BAND_BLUE, 'Helvetica-Bold', alignment=TA_CENTER),
    'subtitle': _style('qSubtitle', 9, 12, fonts.INK2, alignment=TA_CENTER, spaceAfter=10),
    'section': _style('qSection', 10, 13, colors.white, 'Helvetica-Bold', alignment=TA_CENTER),
    'label': _style('qLabel', 7.4, 9.4, fonts.INK2),
    'value': _style('qValue', 9, 11.5, INK, 'Helvetica-Bold'),
    'chip': _style('qRowChip', 8, 10, colors.white, 'Helvetica-Bold'),
    'narrative': _style('qNarrative', 8, 11, leftIndent=10, spaceAfter=6),
}
PLAIN = [(name, (0, 0), (-1, -1), 0) for name in ('LEFTPADDING', 'RIGHTPADDING', 'TOPPADDING', 'BOTTOMPADDING')]


def _esc(value):
    return escape('' if value is None else str(value))


def band(section, width):
    title = f'Section {section["number"]}. {section["label"]}' if section.get('number') else section['label']
    table = Table([[Paragraph(_esc(title), STYLES['section'])]], colWidths=[width])
    table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, -1), BAND_BLUE),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]
        )
    )
    return [Spacer(1, 8), table, Spacer(1, 6)]


def _checkbox(checked):
    """A drawn box, never a dingbat (the ZapfDingbats tick is unreliable across viewers)."""
    cell = Table([['X' if checked else '']], colWidths=[9], rowHeights=[9])
    cell.setStyle(
        TableStyle(
            [
                ('BOX', (0, 0), (-1, -1), 0.7, INK),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                *PLAIN,
            ]
        )
    )
    return cell


def _yes_no(value):
    answer = str(value or '').strip().lower()
    cells = [
        _checkbox(answer == 'yes'),
        Paragraph('Yes', STYLES['label']),
        _checkbox(answer == 'no'),
        Paragraph('No', STYLES['label']),
    ]
    table = Table([cells], colWidths=[12, 22, 12, 20])
    table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), *PLAIN]))
    return table


def _cell(field, value):
    """One labelled answer: caption above, answer below a hairline."""
    if field.get('type') == 'yesno':
        answer = _yes_no(value)
    else:
        answer = Paragraph(_esc(display.listed(field, value)), STYLES['value'])
    cell = Table([[Paragraph(_esc(field.get('label', '')), STYLES['label'])], [answer]], colWidths=['100%'])
    cell.setStyle(
        TableStyle(
            [
                ('LINEBELOW', (0, 1), (-1, 1), 0.5, HAIRLINE),
                *PLAIN,
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ]
        )
    )
    return cell


def grid(fields, values, width, columns=3):
    """Fields left to right, each taking its `width` share of the row (3 is the whole row)."""
    rows, row, used = [], [], 0
    for field in fields:
        span = min(int(field.get('width', 1) or 1), columns)
        if used + span > columns:
            rows.append((row, used))
            row, used = [], 0
        row.append((field, span))
        used += span
    if row:
        rows.append((row, used))
    unit, out = width / columns, []
    for cells, used in rows:
        widths = [unit * span for _field, span in cells] + ([unit * (columns - used)] if used < columns else [])
        data = [[_cell(field, values.get(field['key'])) for field, _span in cells] + ([''] if used < columns else [])]
        table = Table(data, colWidths=widths)
        table.setStyle(
            TableStyle(
                [
                    ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
                    *PLAIN,
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]
            )
        )
        out.append(table)
    return out


def _chip(label, width):
    chip = Table([[Paragraph(_esc(label), STYLES['chip'])]], colWidths=[width])
    chip.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, -1), BAND_BLUE),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]
        )
    )
    return chip


def rows(form, block, numbered, width, wrapped=()):
    """One card per row, kept whole on a page, its chip carrying the row's number on our form; a `wrapped` answer
    (the illness detail) prints under its card so a long one can split across pages."""
    spec, out = get_block(form, block), []
    for number, vals in numbered:
        shown = visible_fields(form, block, vals)
        fields = [f for f in block_fields(form, block) if f['key'] in shown and not f.get('auto')]
        boxed = [f for f in fields if f['key'] not in wrapped]
        if boxed:
            card = [_chip(f'{spec.get("row_label", "Row")} {number}', width), Spacer(1, 4), *grid(boxed, vals, width)]
            out.append(KeepTogether(card))
        for field in fields:
            body = str(vals.get(field['key']) or '').strip()
            if field['key'] in wrapped and body:
                out.append(Paragraph(f'<b>{_esc(field["label"])}</b> {_esc(body)}', STYLES['narrative']))
        out.append(Spacer(1, 4))
    return out


def _chrome(left, right, draft):
    """The footer painter for one render: everything it prints is captured here, never in module state."""
    page_w = letter[0]
    stamp = clock.today().strftime('%m/%d/%Y')

    def paint(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(HAIRLINE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, FOOTER_HEIGHT + 4, page_w - MARGIN, FOOTER_HEIGHT + 4)
        canvas.setFillColor(fonts.INK2)
        canvas.setFont('Helvetica', 6.5)
        canvas.drawString(MARGIN, FOOTER_HEIGHT - 6, f'{left} · data as submitted by {right} · generated {stamp}')
        canvas.drawRightString(page_w - MARGIN, FOOTER_HEIGHT - 6, f'Page {canvas.getPageNumber()}')
        if draft:
            canvas.setFillColor(fonts.DRAFT_RED)
            canvas.setFont(fonts.NOTE_FONT, fonts.NOTE_SIZE)
            canvas.drawString(MARGIN, FOOTER_HEIGHT - 15, 'DRAFT — NOT SIGNED BY THE EMPLOYER')
        canvas.restoreState()

    return paint


def _render(form, found, name, subtitle, body):
    """The attachment's pages, its footer naming the form as `name` (the old stamp said the carrier, the old AcroForm
    fill the short label)."""
    if not body:
        return None
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN + FOOTER_HEIGHT,
        title=f'{form["title"]} — attachment',
    )
    chrome = _chrome(f'Attachment to the {name} questionnaire', found.client, draft=not found.officer)
    doc.build(
        [Paragraph(TITLE, STYLES['title']), Paragraph(_esc(subtitle), STYLES['subtitle']), *body],
        onFirstPage=chrome,
        onLaterPages=chrome,
    )
    buffer.seek(0)
    return buffer


def stamp_pages(form, layout, found, place, chunks):
    """Florida Blue's attachment: every answer `place` sent here, under its own section, then the rows."""
    width = letter[0] - MARGIN * 2
    wrapped = {key for keys in layout.OFF_FORM_BLOCK_FIELDS.values() for key in keys}
    body = []
    for section in form['sections']:
        fields = [f for f in section.get('fields') or [] if f['key'] in place['overflow']]
        blocks = [(block, chunks[block]) for block in section.get('blocks') or [] if block in chunks]
        if not fields and not blocks:
            continue
        body += band(section, width)
        for block, numbered in blocks:
            body += rows(form, block, numbered, width, wrapped)
        body += grid(fields, found.scalars, width)
    subtitle = (
        f'Answers too long for the boxes on the printed {form["carrier"]} form, and the rows it has no space for.'
    )
    return _render(form, found, form['carrier'], subtitle, body)


def detail_pages(form, found, keys):
    """An AcroForm's attachment: the answers its page has no field for (Warner's detail lines)."""
    width = letter[0] - MARGIN * 2
    body = []
    for section in form['sections']:
        fields = [f for f in section.get('fields') or [] if f['key'] in keys]
        if fields:
            body += band(section, width) + grid(fields, found.scalars, width)
    name = form.get('short_label') or form['carrier']
    return _render(form, found, name, f'Details the printed {name} form has no room for.', body)
