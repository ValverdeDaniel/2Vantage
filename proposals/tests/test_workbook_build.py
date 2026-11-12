"""The client spreadsheet on GD1 (plan.md §9.4, §12.6; Q.9 row 27; J145–J152): every total on its rates tabs equals
GD1's key three ways (quotes' figure, the stored result, the evaluator over the written cells; LibreOffice is the
Recalc lane's), the file read back equals the sheet model, and the old file settings hold."""

import io
import zipfile
from decimal import Decimal

import openpyxl
import pytest

from proposals.tests import sheet_eval
from proposals.workbook import build, facts, write
from proposals.workbook.model import BLANK, FORMULA, NUMBER, TEXT
from proposals.workbook.tabs import rates
from quotes import selectors

pytestmark = pytest.mark.django_db


@pytest.fixture(scope='module')
def gd1_book(gd1, django_db_blocker):
    with django_db_blocker.unblock():
        read = facts.read_deal(gd1.deal)
        book = build.from_facts(read)
        state = selectors.deal_state(gd1.deal)
    return read, book, write.to_bytes(book), state


def _geometry(line):
    return rates.tier_line_map(rates.spec(line)[0])


def _result(sheet, row, col):
    cell = sheet.get(row, col)
    assert cell is not None and cell.kind == FORMULA, (sheet.title, row, col)
    return cell.result


def test_J147_GD1_rates_tabs_equal_the_key_three_ways(gd1, golden_keys, gd1_book):
    read, book, _data, state = gd1_book
    key = golden_keys['GD1']['plans']
    by_id = {pid: ref for ref, pid in gd1.refs.items()}
    evaluated = sheet_eval.evaluate(book)
    checked = 0
    for line in read.lines:
        sheet = book.by_title({'medical': 'Medical', 'dental': 'Dental', 'vision': 'Vision'}[line.key])
        g = _geometry(line)
        rows = g['rows']
        for col, plan in zip(g['cols'], line.presented, strict=True):
            figures = key[by_id[plan.id]]
            app = state[line.key].results[plan.id]
            for row, field in ((rows['tm'], 'monthly'), (rows['ta'], 'annual')):
                stored = _result(sheet, row, col['rate'])
                assert stored == figures[field] == app[field], (line.key, by_id[plan.id], field)
                assert sheet_eval.same(evaluated[(sheet.title, row, col['rate'])], figures[field])
                checked += 1
            if rows['dp'] and plan.role != 'current' and figures['change']:
                assert _result(sheet, rows['dp'], col['rate']) == figures['change']['delta']
                pct = _result(sheet, rows['pp'], col['rate'])
                assert Decimal(str(pct)) * 100 == Decimal(str(figures['change']['pct']))
    assert checked >= 2 * 13  # every presented plan on the three rates tabs


def test_J147_every_stored_result_equals_the_evaluator_over_the_written_cells(gd1_book):
    _read, book, _data, _state = gd1_book
    assert sheet_eval.disagreements(book) == []


def _sheet_cells(sheet):
    return {(row, col): cell for (row, col), cell in sheet.cells.items() if cell.kind != BLANK}


def test_J147_the_file_read_back_equals_the_sheet_model(gd1_book):
    _read, book, data, _state = gd1_book
    formulas = openpyxl.load_workbook(io.BytesIO(data))
    stored = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    assert formulas.sheetnames == book.titles()
    for sheet in book.sheets:
        ws, values = formulas[sheet.title], stored[sheet.title]
        for (row, col), cell in _sheet_cells(sheet).items():
            written = ws.cell(row=row, column=col)
            if cell.kind == TEXT:
                assert written.value == cell.value and written.data_type == 's', (sheet.title, row, col)
            elif cell.kind == NUMBER:
                assert written.value == pytest.approx(float(cell.value)), (sheet.title, row, col)
            else:
                assert written.value == cell.value, (sheet.title, row, col)
                assert sheet_eval.same(values.cell(row=row, column=col).value, cell.result), (sheet.title, row, col)
            assert written.number_format == cell.style.get('num_format', 'General'), (sheet.title, row, col)
            assert bool(written.font.b) == bool(cell.style.get('bold')), (sheet.title, row, col)
        merged = {(r.min_row, r.min_col, r.max_row, r.max_col) for r in ws.merged_cells.ranges}
        assert merged == set(sheet.merges), sheet.title
        if sheet.freeze:
            assert ws.freeze_panes == f'{openpyxl.utils.get_column_letter(sheet.freeze[1])}{sheet.freeze[0]}'
        assert len(ws.data_validations.dataValidation) == len(sheet.validations), sheet.title


def test_J152_file_settings_author_recalculation_zoom_and_opening_tab(gd1_book):
    read, book, data, _state = gd1_book
    loaded = openpyxl.load_workbook(io.BytesIO(data))
    assert loaded.properties.creator == read.agency['name']
    opening = book.titles().index('Dynamic Medical Compare')
    assert book.opens_on == opening and loaded.active.title == 'Dynamic Medical Compare'
    assert [bool(ws.sheet_view.tabSelected) for ws in loaded.worksheets] == [
        i == opening for i in range(len(book.sheets))
    ]
    assert 'fullCalcOnLoad="1"' in zipfile.ZipFile(io.BytesIO(data)).read('xl/workbook.xml').decode()
    assert loaded['Medical'].sheet_view.zoomScale == 130
    assert loaded['Dynamic Medical Compare'].sheet_view.zoomScale == 110
    assert loaded['Medical'].freeze_panes == 'B7'


def test_J102_draft_rides_the_page_headers_never_the_cover(gd1_book):
    read, _book, data, _state = gd1_book
    loaded = openpyxl.load_workbook(io.BytesIO(data))
    assert read.draft not in (loaded['Cover'].oddHeader.center.text or '')
    for title in ('Medical', 'Dental All Plans', 'Dynamic Vision Compare', 'Disclaimers'):
        assert read.draft in (loaded[title].oddHeader.center.text or ''), title
    texts = [cell.value for row in loaded['Cover'].iter_rows() for cell in row if isinstance(cell.value, str)]
    assert not any(read.draft in text for text in texts)


def test_J145_cover_prints_the_client_title_prepared_by_and_each_lines_words(gd1, gd1_book):
    read, book, _data, _state = gd1_book
    texts = [cell.value for cell in book.by_title('Cover').cells.values() if cell.kind == TEXT]
    assert gd1.deal.client.name in texts
    assert 'Proposed Benefit Plans Effective January 1st, 2027' in texts or any('Effective' in t for t in texts)
    assert f'Prepared by {read.agency["name"]}' in texts
    assert 'Our recommendation' in texts
    for words in gd1.spec['reasons'].values():
        assert words in texts


def test_J147_rates_tabs_put_a_page_break_before_each_carrier(gd1_book):
    _read, book, data, _state = gd1_book
    loaded = openpyxl.load_workbook(io.BytesIO(data))
    medical = book.by_title('Medical')
    assert medical.print['col_breaks'], 'Medical has carriers after the current plans'
    assert [brk.id for brk in loaded['Medical'].col_breaks.brk] == medical.print['col_breaks']
    assert loaded['Medical'].print_title_rows == '$4:$6'
    assert loaded['Medical'].page_setup.orientation == 'landscape'
