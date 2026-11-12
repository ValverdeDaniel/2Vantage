"""The CAA / ERISA §408(b)(2) compensation disclosure: the PDF (plan.md §9.15; H108).

Ported from 891f1b3 `commissions/disclosure_pdf.py`: pure reportlab platypus, built in memory, streamed and never
stored. The prose is the old template's, word for word (legal text is never paraphrased); only the merge slots move:
the agency's name (`AgencySettings.name`), the date, the client's name and address, the recipient, the comp table and
the additional-compensation sentence. Dynamic text is XML-escaped before it enters a Paragraph.
"""

import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from deals import clock

NAVY = colors.HexColor('#173a63')
INK2 = colors.HexColor('#5b6573')
BORDER = colors.HexColor('#e6e8ec')

# --- Verbatim template text ---------------------------------------------------

INTRO = (
    'ERISA Section 408(b)(2) and applicable State laws require Vantage Risk '
    'Solutions (and, in certain cases, certain affiliates or subsidiaries or '
    '{agency}) to provide certain disclosures to certain ERISA '
    'Plans. {agency} provides certain services in connection '
    'with one or more of {client_upper}’S (“You” or '
    '“Your”) ERISA Plans. These services include:'
)

SERVICES = [
    'Design & development of Your insurance program;',
    'Negotiating and placement of Your employee benefit insurance program;',
    'Year end accounting and other reporting;',
    'Legislative and corporate compliance support;',
    'Day-to-day administrative assistance with Your employee benefit insurance;',
    'Providing employee education programs and communication materials; and',
    'Benefit plan Management, including certain value-added services, which '
    'may include plan administrative services (such as COBRA administration, '
    'account-based plan services and ERISA compliance services) that are '
    'offered by BBP Admin, a division of {agency}.',
]

TABLE_LEAD = (
    'In exchange for the provision of these services, {agency} receives the following compensation as selected below:'
)

ADDITIONAL_COMP_LEAD = 'If applicable, {agency} may receive additional compensation as stated here: '

TRAILING_BULLETS = [
    '{agency} may receive interest or investment income on funds held by it, such as premiums or return premiums.',
    'In addition to this compensation, {agency} has agreements '
    'with many of its insurance markets through which it is compensated on a '
    'non-commission basis for insurance placed in these insurance markets '
    'and/or separate fees for consulting and/or administrative services '
    'specific to such insurance markets. These payments are based upon such '
    'factors as the overall volume, growth, and profitability of the total '
    'premium placed with each insurer.',
    '{agency} and its employees may receive compensation from '
    'plan vendors and service providers that is not in connection with any '
    'particular customer. This compensation includes such items as gifts '
    'valued at less than $100 annually, an occasional dinner or ticket to a '
    'sporting event or other entertainment, or reimbursement in connection '
    'with educational meetings, client workshops or events, or marketing or '
    'advertising initiatives, including services for identifying prospective '
    'clients. Plan vendors and service providers may also pay for, or '
    'reimburse {agency} for the costs associated with, '
    'education or training events that may be attended by Vantage Risk '
    'Solutions employees and for {agency} -sponsored '
    'conferences and events.',
]

CLOSING_PARAGRAPHS = [
    'This Disclosure does not preempt any agreement by and between Vantage '
    'Risk Solutions and You. In the event there are conflicting terms in a '
    'written, fully-executed agreement for services, the terms found within '
    'such agreement shall prevail (to the extent of such conflict).',
    'This disclosure document includes the disclosures {agency} '
    'is required to make in accordance with ERISA Section 408(b)(2) and '
    'applicable State laws. Any other plan service provider that is subject '
    'to the 408(b)(2) disclosure requirements is required to make its own '
    'independent 408(b)(2) disclosure and any such disclosures are not '
    'included in this {agency} disclosure.',
    'This Disclosure and its contents, including the fees arrangement we '
    'have reached, is confidential. You agree not to disclose the contents '
    'of this disclosure to third parties unless you are required to do so '
    'by law.',
]


def _esc(value):
    return escape(str(value or ''))


def _styles():
    sheet = getSampleStyleSheet()
    body = ParagraphStyle('body', parent=sheet['Normal'], fontSize=9.5, leading=13, spaceAfter=8)
    return {
        'brand': ParagraphStyle('brand', parent=sheet['Heading1'], textColor=NAVY, fontSize=14, spaceAfter=0),
        'brand_sub': ParagraphStyle('brand_sub', parent=sheet['Normal'], textColor=INK2, fontSize=8.5, spaceAfter=14),
        'body': body,
        'bullet': ParagraphStyle('bullet', parent=body, leftIndent=16, bulletIndent=6, spaceAfter=3),
        'small': ParagraphStyle('small', parent=sheet['Normal'], fontSize=8, leading=10, textColor=INK2),
    }


def _table(data):
    header = [
        '',
        'USD$ Per Plan\nMember Per Month',
        'USD$ Per Employee\nPer Month',
        'Percentage\nof Premium',
        'Carrier',
    ]
    rows = [
        header,
        ['Direct Compensation from You', 'N/A', 'N/A', 'N/A', 'N/A'],
        ['Indirect Compensation from Insurance Carriers', '', '', '', ''],
    ]
    rows += [[row['label'], row['pmpm'], row['pepm'], row['pct'], row['carrier']] for row in data['rows']]
    table = Table(rows, colWidths=[2.3 * inch, 1.15 * inch, 1.2 * inch, 0.95 * inch, 1.3 * inch])
    table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), NAVY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 8.5),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LINEBELOW', (0, 0), (-1, -1), 0.4, BORDER),
                ('SPAN', (0, 2), (-1, 2)),
                ('TEXTCOLOR', (0, 2), (0, 2), INK2),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build(data):
    """`data` is `disclosure.data(deal)`; returns the PDF's bytes."""
    agency = _esc(data['agency'])
    style = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.8 * inch,
        rightMargin=0.8 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title='Compensation Disclosure',
    )
    today = clock.today()
    name = data['client_name']
    story = [
        Paragraph(agency, style['brand']),
        Paragraph('Compensation Disclosure — ERISA Section 408(b)(2)', style['brand_sub']),
        Paragraph(f'{today:%B} {today.day}, {today.year}', style['body']),
        Paragraph('<br/>'.join([_esc(name)] + [_esc(line) for line in data['address_lines'] if line]), style['body']),
        Spacer(1, 4),
        Paragraph(f'Dear {_esc(data["recipient"])}:', style['body']),
        Paragraph(INTRO.format(agency=agency, client_upper=_esc(name.upper())), style['body']),
    ]
    story += [Paragraph(item.format(agency=agency), style['bullet'], bulletText='•') for item in SERVICES]
    story += [Spacer(1, 4), Paragraph(TABLE_LEAD.format(agency=agency), style['body']), _table(data), Spacer(1, 8)]
    additional = _esc('; '.join(data['additional_comp'])) or 'N/A'
    lead = ADDITIONAL_COMP_LEAD.format(agency=agency)
    story.append(Paragraph(lead + additional, style['bullet'], bulletText='•'))
    story += [Paragraph(item.format(agency=agency), style['bullet'], bulletText='•') for item in TRAILING_BULLETS]
    story.append(Spacer(1, 4))
    story += [Paragraph(para.format(agency=agency), style['body']) for para in CLOSING_PARAGRAPHS]
    story += [
        Spacer(1, 10),
        Paragraph('Sincerely,', style['body']),
        Paragraph(agency, style['body']),
        Spacer(1, 14),
        Paragraph('CONFIDENTIAL', style['small']),
    ]
    doc.build(story)
    return buffer.getvalue()
