"""Our RFP cover page: what a request sent direct to the carriers leads with (plan.md §9.9; K47, K102; OQ65, OQ67).

One page, Letter portrait, deliberately plain (the 2026-09-29 call; Mark's sample was never supplied, OQ67): the
letterhead; the group and its size, with the band's enrolled count (K17); the coverage requested beside what is in
force today (the incumbent carrier is a fact about the group, not the routing); the funding boxes (fully insured,
level-funded, ASO — boxes drawn as cells, since the standard fonts carry no ballot boxes); the broker (the deal's agent:
`deals.rules.agent_name`), the return-to address (OQ65) and BOR on file; the commission by line; the notes box,
always drawn; the date in agency time (bug 22). **It never names a carrier being asked**: one cover goes to every
carrier, and naming the others would hand each its competition. Every value comes from the same request the forms
are filled from (`printed.form_facts`). Ported from old Vantage 891f1b3 `pipeline/rfp_cover_pdf.py`.
"""

import io
from datetime import date

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from deals import clock
from intake.models import CurrentCoverage
from quotes import facts as quote_facts

from .. import printed, request, words
from . import kit

MARGIN = 0.7 * inch
WIDTH = letter[0] - 2 * MARGIN - 12  # SimpleDocTemplate's frame pads 6 pt a side
BLANK = '—'


def text(value):
    """A fact as printed text: dates long, booleans "Yes", blanks a dash."""
    if value in (None, ''):
        return BLANK
    if value is True:
        return 'Yes'
    if isinstance(value, date):
        return words.long_date(value)
    return str(value)


def coverage_rows(ctx):
    """(line, today, current carrier, current funding) for each requested line."""
    first = {}
    for row in CurrentCoverage.objects.filter(deal_id=ctx.deal.id).order_by('sort_order', 'id'):
        first.setdefault(row.line, row)
    out = []
    for key, label in zip(ctx.lines, words.line_labels(ctx.lines), strict=True):
        row = first.get(key)
        if row is None:
            out.append((label, 'Not recorded', '', ''))
        elif not row.in_force:
            out.append((label, 'New line — not in force today', '', ''))
        else:
            found = quote_facts.incumbent(ctx.deal, key) or {}
            funding = found.get('funding') or row.funding
            out.append((label, 'In force', found.get('carrier') or row.carrier, printed.FUNDING_WORDS.get(funding, '')))
    return out


def _table(data, widths, theme, styles, head=False):
    cells = [[Paragraph(kit.esc(text(v) if not head or r else v), styles['th' if head and not r else 'value'])
              for v in row] for r, row in enumerate(data)]  # fmt: skip
    table = Table(cells, colWidths=widths, repeatRows=1 if head else 0)
    style = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, theme.border),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    if head:
        style.append(('BACKGROUND', (0, 0), (-1, 0), theme.navy))
    table.setStyle(TableStyle(style))
    return table


def funding_boxes(ctx, styles, theme):
    picked = set(ctx.funding)
    row, widths = [], []
    style = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE')] + [
        (name, (0, 0), (-1, -1), 0) for name in ('TOPPADDING', 'BOTTOMPADDING', 'LEFTPADDING', 'RIGHTPADDING')
    ]
    for index, (key, label) in enumerate(request.FUNDING):
        col = index * 2
        row += [Paragraph('X' if key in picked else '', styles['box']), Paragraph(kit.esc(label), styles['value'])]
        widths += [0.17 * inch, 1.9 * inch]
        style += [('BOX', (col, 0), (col, 0), 0.8, theme.ink), ('LEFTPADDING', (col + 1, 0), (col + 1, 0), 7)]
    table = Table([row], colWidths=widths, rowHeights=[0.17 * inch], hAlign='LEFT')
    table.setStyle(TableStyle(style))
    return table


def notes_box(notes, styles, theme):
    body = Paragraph(kit.esc(notes).replace('\n', '<br/>') if notes else '', styles['value'])
    table = Table([[body]], colWidths=[WIDTH], rowHeights=[None if notes else 0.9 * inch])
    table.setStyle(
        TableStyle(
            [
                ('BOX', (0, 0), (-1, -1), 0.8, theme.navy),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _pairs(rows, styles, theme):
    return kit.pairs_table([(label, text(value)) for label, value in rows], styles, theme, WIDTH)


def build(ctx):
    """The cover as PDF bytes."""
    facts = printed.form_facts(ctx)
    agency = ctx.agency
    theme = kit.theme_for(agency.brand_color)
    styles = kit.styles_for(theme)
    group = ctx.group_name
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        title=f'Request for Proposal — {group}', author=agency.name or '',
    )  # fmt: skip
    head = [agency.name, agency.address, agency.city_state_zip, agency.phone, agency.email]
    story = kit.letterhead(styles, theme, kit.logo_bytes(agency), head, width=WIDTH)
    story += [
        Paragraph('Request for Proposal', styles['title']),
        Paragraph(
            f'Employee benefits · {kit.esc(group)} · prepared {words.long_date(clock.today())}', styles['brand_sub']
        ),
        Paragraph('The group', styles['h2']),
        _pairs([
            ('Group name', group), ('Requested effective date', facts.get('deal.effective_date')),
            ('Address', facts.get('group.address_street')), ('Quotes due', facts.get('deal.due_date')),
            ('City, state & ZIP', facts.get('group.city_state_zip')), ('SIC code', facts.get('group.sic')),
            ('Additional locations', facts.get('group.locations')), ('Tax ID (FEIN)', facts.get('group.fein')),
            ('Years in business', facts.get('group.years_in_business')),
            ('Waiting period', facts.get('group.waiting_period')),
        ], styles, theme),
        Paragraph('Group size', styles['h2']),
        _pairs([
            ('Eligible employees', facts.get('group.eligible')), ('Enrolled (medical)', facts.get('group.enrolled')),
            ('Waiving coverage', facts.get('group.waiving')), ('Total employees', facts.get('group.total_employees')),
            ('ATNE', facts.get('group.atne')), ('Full-time employees', facts.get('group.fte')),
        ], styles, theme),
        Paragraph('Coverage requested', styles['h2']),
    ]  # fmt: skip
    coverage = coverage_rows(ctx)
    if coverage:
        head_row = ('Line of coverage', 'Today', 'Current carrier', 'Current funding')
        widths = [WIDTH * 0.27, WIDTH * 0.27, WIDTH * 0.26, WIDTH * 0.20]
        story.append(_table([head_row, *coverage], widths, theme, styles, head=True))
    else:
        story.append(Paragraph('No lines of coverage are on the request yet.', styles['small']))
    story += [Paragraph('Funding to quote', styles['h2']), funding_boxes(ctx, styles, theme)]
    broker = [
        ('Agent / broker', facts.get('broker.agent')), ('Agency', facts.get('broker.agency')),
        ('Email', facts.get('broker.email')), ('Phone', agency.phone),
        ('Commission requested', facts.get('broker.commission')), ('Return quotes to', ctx.return_to),
    ]  # fmt: skip
    if facts.get('broker.is_bor'):
        broker.append(('Broker of record', 'Yes'))
    story += [Paragraph('Broker', styles['h2']), _pairs(broker, styles, theme)]
    breakdown = ctx.commission[1]
    if len(breakdown) > 1:
        story += [Spacer(1, 3), Paragraph('Commission by line: ' + kit.esc(' · '.join(breakdown)), styles['small'])]
    story += [
        Paragraph('Notes', styles['h2']),
        notes_box(ctx.stored['notes'], styles, theme),
        Spacer(1, 8),
        Paragraph('The census and the supporting documents are attached to the email this page came with.',
                  styles['small']),
    ]  # fmt: skip
    doc.build(story)
    return buffer.getvalue()


def filename(ctx):
    return f'{ctx.deal.client.name} - RFP cover page.pdf'
