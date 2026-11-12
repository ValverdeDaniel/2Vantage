"""The Excel view's checks, conditional fills and printed pages over synthetic sheets (plan.md §9.4; J116–J118; old
`workbook_preview` / `workbook_pages` at 891f1b3, D-194). Pure: the sheet model in, the viewer's answer out."""

from proposals.viewer import fills, workbook_pages
from proposals.viewer.workbook_checks import ERROR, HASHED, NUMBER, TabCells
from proposals.workbook import cells, print_plan
from proposals.workbook import styles as s
from proposals.workbook.model import Sheet

LONG = 'A label far too long for one narrow column'


def _work(sheet):
    found, checks, counts, _unknown = TabCells(sheet).run()
    return {(item[0], item[1]): item for item in found}, checks, counts


def test_J118_a_number_wider_than_its_column_shows_hashes_and_names_its_cell():
    sheet = Sheet('Medical')
    sheet.widths[2] = 3
    cells.text(sheet, 4, 1, 'Monthly total')
    cells.number(sheet, 4, 2, 123456789, s.MONEY_WHOLE)
    found, checks, counts = _work(sheet)
    item = found[(3, 1)]
    assert item[3] & NUMBER and item[3] & HASHED
    assert set(item[2]) == {'#'}
    assert item[4]['real'] == '$123,456,789'
    assert counts['hash'] == 1
    check = checks['hash'][0]
    assert (check['cell'], check['label']) == ('B4', 'Monthly total')
    assert '$123,456,789' in check['text']


def test_J118_text_runs_on_over_empty_cells_and_is_cut_by_a_full_one():
    sheet = Sheet('Markets Checked')
    cells.text(sheet, 1, 1, LONG)  # B1… empty: it runs on, as in Excel
    cells.text(sheet, 2, 1, LONG)
    cells.text(sheet, 2, 2, 'x')  # B2 holds something: A2 is cut there
    _found, checks, counts = _work(sheet)
    assert counts['cut'] == 1
    assert checks['cut'][0]['cell'] == 'A2'


def test_J118_wrapped_text_taller_than_its_row_is_cut():
    sheet = Sheet('Dental')
    sheet.widths[1] = 12
    cells.text(sheet, 3, 1, ' '.join(['benefit'] * 12), align=s.LEFT)
    sheet.heights[3] = 15
    _found, checks, counts = _work(sheet)
    assert counts['cut'] == 1
    assert checks['cut'][0]['text'].startswith('Cut off:')
    sheet.heights[3] = 400
    assert _work(sheet)[2]['cut'] == 0


def test_J118_a_formula_whose_stored_result_is_an_error_is_one():
    sheet = Sheet('Medical')
    cells.formula(sheet, 2, 2, '=SUM(B1)', '#N/A', s.MONEY_WHOLE)
    found, checks, counts = _work(sheet)
    assert found[(1, 1)][3] & ERROR
    assert counts['error'] == 1 and checks['error'][0]['cell'] == 'B2'


def test_J118_text_that_fits_raises_nothing():
    sheet = Sheet('Cover')
    cells.text(sheet, 1, 1, 'Fits')
    cells.number(sheet, 1, 2, 12, s.COUNT)
    assert _work(sheet)[2] == {'error': 0, 'hash': 0, 'cut': 0, 'tight': 0}


def test_J116_a_conditional_fill_lights_only_where_its_condition_holds():
    sheet = Sheet('Dynamic Medical Compare')
    cells.text(sheet, 1, 2, 'Aetna HMO')
    cells.text(sheet, 1, 3, 'Cigna PPO')
    cells.text(sheet, 3, 1, 'aetna hmo')  # Excel compares text without case
    cells.highlight(sheet, (2, 2, 2, 3), 'AND(B$1=$A$3,$A$3<>"")', s.HIGHLIGHT_CURRENT)
    assert fills.conditional_fills(sheet) == {(2, 2): s.CURRENT_GREEN}
    sheet.cells.pop((3, 1))
    assert fills.conditional_fills(sheet) == {}  # an empty base lights nothing, even beside an empty pick


def _printed(last_col=10, last_row=20, breaks=(4, 7)):
    sheet = Sheet('Medical')
    for col in range(1, last_col + 1):
        sheet.widths[col] = 10
    for row in range(1, last_row + 1):
        cells.text(sheet, row, 1, f'row {row}')
    plan = {'breaks': list(breaks), 'scale': 100, 'title_rows': (1, 1), 'title_cols': (1, 1)}
    print_plan.with_breaks(sheet, last_col, last_row, plan, draft='Draft')
    return sheet


def test_J117_pages_break_where_the_tab_breaks_numbered_down_then_across():
    found = workbook_pages.print_summary(_printed())
    assert found['scale'] == 100 and not found['fit']
    assert [page['cols'] for page in found['pages']] == [[0, 3], [4, 6], [7, 9]]
    assert [page['n'] for page in found['pages']] == [1, 2, 3]
    assert found['title_rows'] == [0, 0] and found['title_cols'] == [0, 0]
    assert found['footer'] == 'page' and found['header'] == 'draft'
    assert found['paper'] == {'w': 11.0, 'h': 8.5}


def test_J117_a_tall_tab_runs_down_onto_more_pages():
    found = workbook_pages.print_summary(_printed(last_row=120, breaks=()))
    across = {tuple(page['cols']) for page in found['pages']}
    down = [page['rows'] for page in found['pages']]
    assert len(across) == 1 and len(down) > 1
    assert down[0][0] == 0 and down[-1][1] == 119


def test_J117_fit_to_one_page_wide_scales_the_tab_down():
    sheet = _printed(last_col=30, breaks=())
    print_plan.fitted(sheet, 30, 20, fit_wide=1)
    found = workbook_pages.print_summary(sheet)
    assert found['fit'] and found['scale'] < 100
    assert {tuple(page['cols']) for page in found['pages']} == {(0, 29)}


def test_J117_a_tab_with_no_print_setup_has_no_pages():
    assert workbook_pages.print_summary(Sheet('Scratch')) is None
