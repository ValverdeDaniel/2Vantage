"""The sheet viewer's server side (plan.md §7.4; E27–E29; OQ25): windows, the opened cell, find and the look."""

import io

import openpyxl
from openpyxl.styles import Border, Font, PatternFill, Side

from documents import sheet_look, sheets
from documents.sheet_find import find_value

from .helpers import RATES_XLSX_ROWS, stored, xlsx

RATES = xlsx(RATES_XLSX_ROWS, hidden_rows=[3], hidden_cols=[2], extra_sheets=[('Notes', True)])


def test_E27_a_window_lists_the_sheets_and_tags_the_hidden_one():
    data = sheets.window('rates.xlsx', RATES, look=True)
    assert [(s['name'], s['hidden']) for s in data['sheets']] == [('Rates', False), ('Notes', True)]
    assert data['sheet'] == 'Rates' and data['start'] == 0 and data['total_rows'] == 4
    assert data['rows'][2] == ['Employee only', '512.34', '410.5'] and data['col_letters'] == ['A', 'B', 'C']


def test_OQ25_hidden_rows_and_columns_come_back_to_be_greyed():
    fmt = sheets.window('rates.xlsx', RATES, look=True)['format']
    assert fmt['hidden_rows'] == [3] and fmt['hidden_cols'] == [2]
    head = fmt['styles'][fmt['cells'][0][0]]
    assert head['b'] == 1 and head['bg'] == '#DDEBF7' and head['bb'].startswith('1px solid')


def test_E29_plain_has_no_look_and_the_same_text():
    plain = sheets.window('rates.xlsx', RATES, look=False)
    assert plain['format'] is None and plain['rows'] == sheets.window('rates.xlsx', RATES, look=True)['rows']


def test_E28_a_cell_opens_its_sheet_around_it():
    rows = [['Plan', 'Value']] + [[f'Row {i}', i] for i in range(1, 300)]
    data = sheets.window('long.xlsx', xlsx(rows), cell='Rates!B250')
    assert data['match'] == {'sheet': 'Rates', 'row': 249, 'col': 1, 'cell': 'B250'}
    assert data['start'] == 249 - sheets.CONTEXT_ROWS and data['total_rows'] == 300
    assert data['rows'][sheets.CONTEXT_ROWS][1] == '249'


def test_E27_windows_page_by_200_rows():
    rows = [[f'r{i}'] for i in range(450)]
    data = sheets.window('long.csv', '\n'.join(r[0] for r in rows).encode(), start=400)
    assert data['sheet'] == sheets.CSV_SHEET and data['start'] == 400 and len(data['rows']) == 50
    assert data['total_rows'] == 450 and data['format'] is None


def test_E29_limits_cut_long_cells_and_wide_sheets():
    wide = [['x' * 500] + [str(i) for i in range(sheets.MAX_COLS + 20)]]
    data = sheets.window('wide.csv', ','.join(wide[0]).encode())
    assert len(data['rows'][0][0]) == sheets.MAX_CELL and data['cols'] == sheets.MAX_COLS


def test_E28_find_posts_the_value_and_answers_the_cell():
    assert find_value('rates.xlsx', RATES, '1580.47', hint='Gold PPO 1500') == {
        'sheet': 'Rates',
        'cell': 'B4',
        'state': 'found',
    }
    assert find_value('rates.xlsx', RATES, '$410.50')['cell'] == 'C3'  # numbers compare as numbers
    assert find_value('rates.xlsx', RATES, '99999') == {'sheet': None, 'cell': None, 'state': 'absent'}


def test_E28_the_hint_picks_the_plan_column():
    rows = [['', 'Gold PPO', 'Silver HMO'], ['Deductible', 1500, 1500]]
    assert find_value('both.xlsx', xlsx(rows), '1500', hint='Silver HMO')['cell'] == 'C2'


def test_E28_find_endpoint_takes_the_value_in_the_body(api, user, deal):
    doc = stored(user, deal, name='rates.xlsx', content=RATES)
    found = api.post(f'/api/documents/{doc.id}/sheet/find/', {'value': '512.34', 'hint': 'Gold'}, format='json')
    assert found.status_code == 200 and found.json()['cell'] == 'B3'
    assert api.post(f'/api/documents/{doc.id}/sheet/find/', {}, format='json').status_code == 400
    window = api.get(f'/api/documents/{doc.id}/sheet/', {'cell': 'B3', 'sheet': 'Rates', 'look': '1'})
    assert window.status_code == 200 and window.json()['match']['cell'] == 'B3' and window.json()['format']


def test_E29_a_bad_start_or_a_pdf_answers_400(api, user, deal):
    doc = stored(user, deal, name='rates.xlsx', content=RATES)
    assert api.get(f'/api/documents/{doc.id}/sheet/', {'start': 'x'}).status_code == 400
    pdf = stored(user, deal)
    assert api.get(f'/api/documents/{pdf.id}/sheet/').status_code == 400


def test_E29_look_reads_a_workbook_built_in_memory():
    book = openpyxl.Workbook()
    ws = book.active
    ws.title = 'Proposal'
    ws['A1'] = 'Client proposal'
    ws['A1'].font = Font(bold=True, size=14, color='FF173A63')
    ws['A2'].fill = PatternFill('solid', fgColor='FFE7E9EE')
    ws['B2'].border = Border(bottom=Side(style='medium', color='FF000000'))
    ws.merge_cells('A1:C1')
    ws.column_dimensions['B'].width = 20
    ws.row_dimensions[2].hidden = True
    fmt = sheet_look.look(book, 'Proposal', 0, 3, 3)
    title = fmt['styles'][fmt['cells'][0][0]]
    assert title['b'] == 1 and title['s'] == 14 and title['fg'] == '#173A63'
    assert fmt['merges'] == [[0, 0, 1, 3]] and fmt['cells'][0][1] == 0  # covered by the merge
    assert fmt['styles'][fmt['cells'][1][0]]['bg'] == '#E7E9EE'
    assert fmt['styles'][fmt['cells'][1][1]]['bb'] == '2px solid #000000'
    assert fmt['col_px'][1] == 140 and fmt['hidden_rows'] == [1]
    saved = io.BytesIO()
    book.save(saved)  # look() never changed the workbook
    assert openpyxl.load_workbook(saved)['Proposal']['A1'].value == 'Client proposal'
