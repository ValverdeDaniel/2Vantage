"""GD4's scanned SBC (plan.md §13.4, §10.7; E25, slice 65): the Summary of Benefits and Coverage of its first current
plan as a carrier mails it and a client scans it back, a picture of a page with no text layer, made by code from the
spec's own values (never a real file).

Nothing on the server can read it: the locator calls its values "check by eye" (NOCHECK `no_text`), and only the
station's browser OCR finds where to draw the box (E25; OCR draws, it never marks a value found). The page prints
the plan's carrier and product, its deductible and out-of-pocket limit, and the rest of an SBC's first rows. Its
figures are printed once each, so a box lands on the right one; the plan's own name (which carries its deductible,
"… 2000") is left off the page, as an SBC prints the product ("Choice POS II") above its figures.
"""

import io
import textwrap
import time

from PIL import Image, ImageDraw, ImageFont

PLAN = 'P1'
PRINTED = ('deductible_single', 'oop_max_single')  # the values whose source names this file
FILE_NAME = 'Aetna Choice POS II SBC, scanned (synthetic).pdf'
DPI = 150
SIZE = (1275, 1650)  # US Letter at 150 dpi
MARGIN = 90
STAMP = time.strptime('2027-01-01', '%Y-%m-%d')  # a fixed date in the PDF's info: the same bytes on every seed


def _money(raw):
    return f'${float(raw):,.0f}'


def _font(size):
    return ImageFont.load_default(size=size)


def _rows(values, spec):
    single, oop = float(values['deductible_single']), float(values['oop_max_single'])
    return [
        ('What is the overall deductible?', f'{_money(single)} individual / {_money(single * 2)} family'),
        ('Are there services covered before you meet your deductible?', 'Yes. Preventive care is covered first.'),
        ('What is the out-of-pocket limit for this plan?', f'{_money(oop)} individual / {_money(oop * 2)} family'),
        ('Will you pay less if you use a network provider?', 'Yes. See the provider directory.'),
        ('Do you need a referral to see a specialist?', 'Yes, from your primary care physician.'),
        ('Primary care visit to treat an injury or illness', f'${values["pcp_copay"]} copay per visit'),
        ('Coverage period', f'{spec["effective_date"]} through the end of the plan year'),
    ]


def scanned_sbc_pdf(spec):
    """(bytes, plan ref, printed keys): one scanned page, an image only."""
    plan = next(p for p in spec['plans'] if p['ref'] == PLAN)
    values = plan['values']
    page = Image.new('L', SIZE, 250)  # the scanner's off-white
    draw = ImageDraw.Draw(page)
    y = MARGIN
    draw.text((MARGIN, y), 'Summary of Benefits and Coverage', font=_font(44), fill=20)
    y += 64
    draw.text((MARGIN, y), 'What this Plan Covers & What You Pay for Covered Services', font=_font(24), fill=40)
    y += 52
    draw.text((MARGIN, y), f'{plan["carrier"]} Life Insurance Company (synthetic)', font=_font(28), fill=20)
    y += 42
    draw.text((MARGIN, y), 'Choice POS II', font=_font(28), fill=20)
    y += 42
    draw.text((MARGIN, y), f'For {spec["client"]}', font=_font(24), fill=40)
    y += 64
    draw.line((MARGIN, y, SIZE[0] - MARGIN, y), fill=60, width=3)
    y += 24
    draw.text((MARGIN, y), 'Important Questions', font=_font(26), fill=20)
    draw.text((700, y), 'Answers', font=_font(26), fill=20)
    y += 48
    for question, answer in _rows(values, spec):
        draw.line((MARGIN, y - 10, SIZE[0] - MARGIN, y - 10), fill=170, width=1)
        for i, part in enumerate(textwrap.wrap(question, 44)):
            draw.text((MARGIN, y + 28 * i), part, font=_font(22), fill=30)
        draw.text((700, y), answer, font=_font(24), fill=10)
        y += 84
    footer = 'Synthetic test file: every name and number on it is made up.'
    draw.text((MARGIN, SIZE[1] - MARGIN), footer, font=_font(18), fill=90)
    out = io.BytesIO()
    page.save(out, format='PDF', resolution=DPI, creationDate=STAMP, modDate=STAMP, producer='golden')
    return out.getvalue(), PLAN, list(PRINTED)
