"""The spreadsheet-injection guard (plan.md §3.8; D114, J153, K107): text written into a workbook stays text."""

import io

import openpyxl

from documents import xlsx_safe

RISKY = ['=HYPERLINK("http://example.com","x")', '+1+1', '-2', '@SUM(A1)', 'http://example.com/a', '00123']


def _read(content):
    return openpyxl.load_workbook(io.BytesIO(content))['Sheet1']


def test_D114_xlsxwriter_text_never_becomes_a_formula_a_link_or_a_number():
    out = io.BytesIO()
    book = xlsx_safe.workbook(out)
    sheet = book.add_worksheet('Sheet1')
    for row, text in enumerate(RISKY):
        xlsx_safe.write(sheet, row, 0, text)
    xlsx_safe.write(sheet, len(RISKY), 0, 1234.5)
    book.close()
    ws = _read(out.getvalue())
    for row, text in enumerate(RISKY, start=1):
        assert ws.cell(row=row, column=1).value == text and ws.cell(row=row, column=1).data_type == 's'
    assert ws.cell(row=len(RISKY) + 1, column=1).value == 1234.5
    assert not ws._hyperlinks


def test_J153_links_are_written_one_by_one_and_only_to_the_web_or_mail():
    out = io.BytesIO()
    book = xlsx_safe.workbook(out)
    sheet = book.add_worksheet('Sheet1')
    xlsx_safe.write_link(sheet, 0, 0, 'https://example.com/sbc.pdf', 'SBC')
    xlsx_safe.write_link(sheet, 1, 0, 'file:///etc/passwd', 'Local file')
    book.close()
    ws = _read(out.getvalue())
    assert ws['A1'].hyperlink.target == 'https://example.com/sbc.pdf' and ws['A1'].value == 'SBC'
    assert ws['A2'].hyperlink is None and ws['A2'].value == 'Local file'


def test_D114_openpyxl_put_keeps_formula_text_literal():
    book = openpyxl.Workbook()
    ws = book.active
    xlsx_safe.put(ws, 1, 1, '=1+1')
    xlsx_safe.put(ws, 2, 1, 'Plain')
    xlsx_safe.put(ws, 3, 1, 42)
    saved = io.BytesIO()
    book.save(saved)
    back = openpyxl.load_workbook(saved).active
    assert back['A1'].value == '=1+1' and back['A1'].data_type == 's' and back['A1'].quotePrefix
    assert back['A2'].value == 'Plain' and back['A3'].value == 42


def test_K107_csv_text_that_starts_like_a_formula_gets_an_apostrophe():
    assert xlsx_safe.csv_text('=cmd') == "'=cmd" and xlsx_safe.csv_text('@x') == "'@x"
    assert xlsx_safe.csv_text('Gold PPO') == 'Gold PPO' and xlsx_safe.csv_text(None) == ''
