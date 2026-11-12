"""The golden deals' synthetic files (plan.md §13.4; slice 15): made by code from the spec's own values, never a real
file, and attached through documents' upload service so each value's ↗ opens where it is printed.

GD1 carries two:
- "Aetna 2027 renewal (synthetic).pdf" (kind renewal): a cover letter, then the rate exhibit of the three renewals,
  current and renewal rates by tier. The renewals' four tier rates point at it (`doc`; the viewer finds the page).
- "Cigna medical quote (synthetic).xlsx" (kind quote): the four Cigna alternates side by side, styled like a carrier
  workbook, with a hidden underwriting row, a hidden column and a hidden notes sheet (OQ25). Every value of those
  plans points at its own cell (`doc` and `cell`, "Medical!C10").
GD4 carries one beside its census files (golden/census_files.py):
- "Aetna Choice POS II SBC, scanned (synthetic).pdf" (kind sbc): P1's SBC as a scan, a picture with no text layer
  (golden/scanned_sbc.py; slice 65, E25). P1's deductible and out-of-pocket limit point at it (`doc`); the locator
  calls them "check by eye", and the station's browser OCR draws their boxes.
The values are the spec's; the files only print them.
"""

import io
from collections import namedtuple

from django.core.files.uploadedfile import SimpleUploadedFile

import synthetic_files
from documents import services as documents
from documents import xlsx_safe

from . import renewal_packet, scanned_sbc

Attached = namedtuple('Attached', 'document cells keys')  # cells: {key: 'Sheet!A1'} or None; keys: the printed keys

TIERS = [
    ('rate_ee', 'Employee only'),
    ('rate_es', 'EE + Spouse'),
    ('rate_ec', 'EE + Child(ren)'),
    ('rate_fam', 'Family'),
]
RENEWALS = ('A2', 'B2', 'C2')
CIGNA = ('CG1', 'CG2', 'CG3', 'CG4')
QUOTE_ROWS = [
    ('plan_type', 'Plan Type'),
    ('funding', 'Funding'),
    ('deductible_single', 'Deductible (Single)'),
    ('oop_max_single', 'OOP Max (Single)'),
    ('pcp_copay', 'PCP Copay'),
    ('rate_ee', 'Rate — EE'),
    ('rate_es', 'Rate — EE + Spouse'),
    ('rate_ec', 'Rate — EE + Child(ren)'),
    ('rate_fam', 'Rate — Family'),
]
WORDS = {'fully_insured': 'Fully insured'}


def _money(raw):
    number = float(raw)
    return f'${number:,.2f}'


def _plans(spec, refs):
    by_ref = {plan['ref']: plan for plan in spec['plans']}
    return [by_ref[ref] for ref in refs]


def aetna_renewal_pdf(spec):
    renewals = _plans(spec, RENEWALS)
    current = {plan['ref']: plan for plan in _plans(spec, [plan['links'][0] for plan in renewals])}
    cover = [
        (72, 720, 'Aetna Life Insurance Company (synthetic)', 14, True),
        (72, 696, f"Renewal for {spec['client']}", 11),
        (72, 676, f"Effective {spec['effective_date']}"),
        (72, 640, 'Thank you for your business. Your medical renewal rates are on the next page.'),
        (72, 624, 'Benefits are unchanged. Rates are guaranteed for twelve months.'),
        (72, 100, 'Synthetic test file: every name and number on it is made up.', 8),
    ]
    exhibit = [(72, 730, 'Renewal rate exhibit', 14, True)]
    y = 700
    for plan in renewals:
        before = current[plan['links'][0]]['values']
        exhibit += [(72, y, plan['name'], 11, True), (300, y, 'Current', 10, True), (400, y, 'Renewal', 10, True)]
        exhibit.append(('rect', 68, y - 4 - 16 * len(TIERS), 420, 16 * len(TIERS) + 18))
        for i, (key, label) in enumerate(TIERS, start=1):
            row = y - 16 * i
            exhibit += [(84, row, label), (300, row, _money(before[key])), (400, row, _money(plan['values'][key]))]
        y -= 16 * len(TIERS) + 44
    return synthetic_files.pdf([cover, exhibit])


def cigna_quote_xlsx(spec):
    """(bytes, {ref: {key: 'Medical!C10'}})"""
    plans = _plans(spec, CIGNA)
    out = io.BytesIO()
    book = xlsx_safe.workbook(out)
    title = book.add_format({'bold': True, 'font_size': 13, 'font_color': '#FFFFFF', 'bg_color': '#1F4E79'})
    head = book.add_format({'bold': True, 'bg_color': '#DDEBF7', 'border': 1, 'text_wrap': True, 'align': 'center'})
    label = book.add_format({'bold': True, 'border': 1, 'bg_color': '#F2F2F2'})
    text = book.add_format({'border': 1, 'align': 'center'})
    money = book.add_format({'border': 1, 'num_format': '$#,##0.00', 'align': 'center'})
    sheet = book.add_worksheet('Medical')
    sheet.set_column(0, 0, 26)
    sheet.set_column(1, len(plans), 20)
    sheet.set_column(len(plans) + 1, len(plans) + 1, 14, None, {'hidden': True})
    sheet.merge_range(0, 0, 0, len(plans), f"Cigna medical quote for {spec['client']}", title)
    xlsx_safe.write_text(sheet, 1, 0, f"Effective {spec['effective_date']} · synthetic test file")
    xlsx_safe.write_text(sheet, 3, 0, 'Benefit', head)
    xlsx_safe.write_text(sheet, 3, len(plans) + 1, 'Internal code', head)
    cells = {plan['ref']: {} for plan in plans}
    for col, plan in enumerate(plans, start=1):
        xlsx_safe.write_text(sheet, 3, col, plan['name'], head)
    row = 4
    for key, row_label in QUOTE_ROWS:
        if key == 'rate_ee':  # a hidden row a quote read skips (OQ25)
            xlsx_safe.write_text(sheet, row, 0, 'Underwriting factor', label)
            for col in range(1, len(plans) + 1):
                xlsx_safe.write(sheet, row, col, 0.97, text)
            sheet.set_row(row, None, None, {'hidden': True})
            row += 1
        xlsx_safe.write_text(sheet, row, 0, row_label, label)
        for col, plan in enumerate(plans, start=1):
            raw = plan['values'][key]
            if key.startswith('rate_') or key in ('deductible_single', 'oop_max_single'):
                xlsx_safe.write(sheet, row, col, float(raw), money if key.startswith('rate_') else text)
            else:
                xlsx_safe.write_text(sheet, row, col, WORDS.get(raw, raw), text)
            cells[plan['ref']][key] = f'Medical!{chr(65 + col)}{row + 1}'
        xlsx_safe.write_text(sheet, row, len(plans) + 1, f'UW-{row + 1}', text)  # the hidden column (OQ25)
        row += 1
    notes = book.add_worksheet('Rating notes')
    xlsx_safe.write_text(notes, 0, 0, 'Internal rating notes (hidden in Excel).')
    notes.hide()
    book.close()
    return out.getvalue(), cells


def _upload(user, deal, name, content, data):
    return documents.upload(user, deal, SimpleUploadedFile(name, content), data)


def attach_gd1(user, deal, spec):
    """Upload GD1's two files; {plan ref: Attached} for the plans whose values they print."""
    renewal = _upload(
        user,
        deal,
        'Aetna 2027 renewal (synthetic).pdf',
        aetna_renewal_pdf(spec),
        {'kind': 'renewal', 'role': 'renewal', 'carrier': 'Aetna', 'lines': ['medical']},
    )
    content, cells = cigna_quote_xlsx(spec)
    quote = _upload(
        user,
        deal,
        'Cigna medical quote (synthetic).xlsx',
        content,
        {'kind': 'quote', 'role': 'alternates', 'carrier': 'Cigna', 'lines': ['medical']},
    )
    attached = {ref: Attached(renewal, None, [key for key, _ in TIERS]) for ref in RENEWALS}
    attached.update({ref: Attached(quote, cells[ref], list(cells[ref])) for ref in CIGNA})
    return attached


def attach_gd4(user, deal, spec):
    """Upload GD4's scanned SBC; {plan ref: Attached} for the plan whose values it prints (slice 65)."""
    content, ref, keys = scanned_sbc.scanned_sbc_pdf(spec)
    sbc = _upload(
        user,
        deal,
        scanned_sbc.FILE_NAME,
        content,
        {'kind': 'sbc', 'role': 'current', 'carrier': 'Aetna', 'lines': ['medical']},
    )
    return {ref: Attached(sbc, None, keys)}


ATTACH = {'GD1': attach_gd1, 'GD3': renewal_packet.attach, 'GD4': attach_gd4}  # GD3's packet: slice 18


def attach(user, deal, spec):
    """{plan ref: Attached} for a spec that has synthetic files, else {}."""
    builder = ATTACH.get(spec['key'])
    return builder(user, deal, spec) if builder else {}
