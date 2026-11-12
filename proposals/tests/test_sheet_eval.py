"""The test-only evaluator against the client spreadsheet's own formula templates (plan.md §9.4, J.6.10; J147, J148,
J.5 B33). Pure: small books built by hand on the sheet model, no database."""

from decimal import Decimal

import pytest

from proposals.tests import sheet_eval
from proposals.workbook import cells, formulas
from proposals.workbook.model import Book
from quotes.math import contribution

TIERS = (9, 10, 11, 12)
STATED = 13
LOOKUPS = frozenset({'Compare'})  # MAX, MIN and IFERROR are the lookup grammar's (grammar.check)


def _put(sheet, row, col, value):
    """Text as a client might type it, else a number (None leaves the cell empty)."""
    if isinstance(value, str):
        return cells.text(sheet, row, col, value)
    return cells.number(sheet, row, col, value, '0.00')


def _rates_tab(counts, rates, stated=None, stated_row=True):
    """A rates tab: counts in B9:B12, rates in C9:C12, the stated premium in C13, the total in C15, annual in C16."""
    book = Book()
    sheet = book.sheet('Medical')
    for row, count, rate in zip(TIERS, counts, rates, strict=True):
        _put(sheet, row, 2, count)
        _put(sheet, row, 3, rate)
    if stated is not None:
        _put(sheet, STATED, 3, stated)
    cells.formula(sheet, 15, 3, formulas.total('B', 'C', TIERS, STATED if stated_row else None), None, '0')
    cells.formula(sheet, 16, 3, formulas.annual('C', 15), None, '0')
    return book


def _total(book):
    found = sheet_eval.evaluate(book)
    return found[('Medical', 15, 3)], found[('Medical', 16, 3)]


def test_J147_total_is_the_counts_times_the_rates_rounded_half_up():
    book = _rates_tab((10, 3, 2, 5), (500.00, 1000.50, 900.25, 1500.75))
    assert _total(book) == (17306, 17306 * 12)


def test_J147_B33_an_enrolled_unrated_tier_falls_back_to_the_stated_premium_or_blank():
    assert _total(_rates_tab((10, 2, 0, 0), (500, None, None, None), stated=15000.4)) == (15000, 180000)
    assert _total(_rates_tab((10, 2, 0, 0), (500, None, None, None), stated='TBD')) == ('', '')
    assert _total(_rates_tab((10, 2, 0, 0), (500, None, None, None))) == ('', '')
    assert _total(_rates_tab((10, 2, 0, 0), (500, None, None, None), stated_row=False)) == ('', '')


def test_J147_a_rate_typed_as_text_is_missing_never_a_value_error():
    assert _total(_rates_tab((10, 2, 0, 0), (500, 'N/A', None, None), stated=9000)) == (9000, 108000)


def test_J147_a_count_typed_as_text_counts_zero_and_an_empty_tier_needs_no_rate():
    assert _total(_rates_tab((10, '-', 0, 0), (500, None, 'TBD', None))) == (5000, 60000)


def test_J147_nobody_enrolled_prices_nothing():
    assert _total(_rates_tab((0, 0, 0, 0), (500, 1000, 900, 1500), stated=9000)) == ('', '')


def _changes(value, base, credit=None):
    book = Book()
    sheet = book.sheet('Dental')
    for col, figure in ((2, base), (3, value)):
        _put(sheet, 5, col, figure)
    if credit is not None:
        _put(sheet, 6, 3, credit)
    cells.formula(sheet, 8, 3, formulas.delta('C', 5, 'B', 5), None, '0')
    cells.formula(sheet, 9, 3, formulas.pct('C', 5, 'B', 5), None, '0')
    cells.formula(sheet, 10, 3, formulas.net('C', 5, 6), None, '0')
    found = sheet_eval.evaluate(book)
    return tuple(found[('Dental', row, 3)] for row in (8, 9, 10))


def test_J147_change_against_the_current_plan_and_the_net_after_a_credit():
    assert _changes(120000, 100000) == (20000, 0.2, 120000)
    assert _changes(25248, 26424)[:2] == (-1176, -0.045)
    assert _changes(1200, 0) == (1200, '', 1200)
    assert _changes('', 100000) == ('', '', '')
    assert _changes(1200, 1000, credit=1500) == (200, 0.2, '')
    assert _changes(1200, 1000, credit='N/A') == (200, 0.2, 1200)
    assert _changes(1200, 1000, credit=200) == (200, 0.2, 1000)


def _bank():
    book = Book()
    bank = book.sheet('Medical All Plans')
    for row, (label, deductible) in enumerate((('Current · Aetna — HMO', '$1,000'), ('Cigna — PPO', None)), 5):
        cells.text(bank, row, 1, label)
        cells.text(bank, row, 4, deductible)
        cells.text(bank, row, 5, 'https://example.com/sbc.pdf' if row == 5 else None)
    compare = book.sheet('Dynamic Medical Compare')
    sheets = frozenset(book.titles())
    cells.text(compare, 9, 2, 'See SBC')
    for col, pick in ((3, 'current · aetna — hmo'), (5, 'Cigna — PPO'), (7, 'Select a plan ▾')):
        cells.text(compare, 7, col, pick)
        found = formulas.lookup('Medical All Plans', 'D', 5, 6, f'{chr(64 + col)}$7')
        cells.formula(compare, 8, col, formulas.looked_up(found), None, '@', sheets=sheets)
        link = formulas.lookup('Medical All Plans', 'E', 5, 6, f'{chr(64 + col)}$7')
        template = f'=IFERROR(IF({link}="","",HYPERLINK({link},$B$9)),"")'
        cells.formula(compare, 9, col, template, None, '@', sheets=sheets)
    return sheet_eval.evaluate(book)


def test_J148_a_pick_looks_its_row_up_across_tabs_case_ignored():
    found = _bank()
    assert found[('Dynamic Medical Compare', 8, 3)] == '$1,000'
    assert found[('Dynamic Medical Compare', 9, 3)] == 'See SBC'


def test_J148_an_empty_cell_or_a_missing_pick_reads_blank_never_zero_or_an_error():
    found = _bank()
    assert found[('Dynamic Medical Compare', 8, 5)] == ''
    assert found[('Dynamic Medical Compare', 9, 5)] == ''
    assert found[('Dynamic Medical Compare', 8, 7)] == ''
    assert found[('Dynamic Medical Compare', 9, 7)] == ''


CONTRIBUTION_CASES = [
    # counts, rates, ee %, dependents %, dollars a tier
    ((10, 3, 2, 5), (500, 1000.5, 900.25, 1500.75), 0.75, 0.5, (None, None, None, None)),
    ((10, 0, 2, 0), (500, None, 900.25, None), 0.8, 0.25, (None, None, None, None)),
    ((10, 3, 2, 5), (500, None, 900.25, 1500.75), 0.75, 0.5, (None, None, None, None)),
    ((10, 3, 2, 5), (500, 1000.5, 900.25, 1500.75), None, None, (400, 650, 600, None)),
    ((10, 3, 0, 5), (500, 1000.5, None, 1500.75), 0.75, None, (600, None, None, 2000)),
]


@pytest.mark.parametrize('counts, rates, ee_pct, dep_pct, amounts', CONTRIBUTION_CASES)
def test_J148_the_contribution_templates_agree_with_quotes_contribution_math(counts, rates, ee_pct, dep_pct, amounts):
    book = Book()
    sheet = book.sheet('Compare')
    rows = {'ee': 20, 'dep': 21, 'pay': (22, 23, 24, 25), 'er': 26, 'emp': 27, 'monthly': 14}
    for row, count, rate in zip(TIERS, counts, rates, strict=True):
        cells.number(sheet, row, 2, count, '0')
        cells.number(sheet, row, 3, rate, '0.00')
    for row, amount in zip(rows['pay'], amounts, strict=True):
        cells.number(sheet, row, 2, amount, '0.00')
    cells.number(sheet, rows['ee'], 2, ee_pct, '0.0%')
    cells.number(sheet, rows['dep'], 2, dep_pct, '0.0%')
    cells.number(sheet, rows['monthly'], 3, 9000, '0')
    counts_refs = [f'$B${row}' for row in TIERS]
    rate_refs = [f'C{row}' for row in TIERS]
    pay_refs = [f'$B${row}' for row in rows['pay']]
    cells.formula(
        sheet,
        rows['ee'],
        3,
        formulas.employees(counts_refs, 'C9', f'$B${rows["ee"]}', pay_refs),
        None,
        '0',
        sheets=LOOKUPS,
    )
    template = formulas.dependents(counts_refs, rate_refs, f'$B${rows["dep"]}', pay_refs)
    cells.formula(sheet, rows['dep'], 3, template, None, '0', sheets=LOOKUPS)
    for row, count, rate, amount in zip(rows['pay'], counts_refs, rate_refs, pay_refs, strict=True):
        cells.formula(sheet, row, 3, formulas.tier_pay(count, rate, amount, pay_refs), None, '0', sheets=LOOKUPS)
    parts = [f'C{row}' for row in (rows['ee'], rows['dep'], *rows['pay'])]
    cells.formula(sheet, rows['er'], 3, formulas.employer_total(*parts), None, '0', sheets=LOOKUPS)
    cells.formula(
        sheet,
        rows['emp'],
        3,
        formulas.employee_total(f'C{rows["monthly"]}', f'C{rows["er"]}'),
        None,
        '0',
        sheets=LOOKUPS,
    )
    found = sheet_eval.evaluate(book)
    tiers = dict(zip(('EE', 'ES', 'EC', 'FAM'), counts, strict=True))
    by_tier = dict(zip(('EE', 'ES', 'EC', 'FAM'), rates, strict=True))
    dollars = dict(zip(('EE', 'ES', 'EC', 'FAM'), amounts, strict=True))
    expected_pay = [contribution.for_tier(tiers[t], by_tier[t], dollars[t], dollars) for t in ('EE', 'ES', 'EC', 'FAM')]
    expected = {
        rows['ee']: contribution.for_employees(tiers, by_tier, ee_pct, dollars),
        rows['dep']: contribution.for_dependents(tiers, by_tier, dep_pct, dollars),
        **dict(zip(rows['pay'], expected_pay, strict=True)),
    }
    employer = contribution.employer_total(*(expected[row] for row in (rows['ee'], rows['dep'], *rows['pay'])))
    expected[rows['er']] = employer
    expected[rows['emp']] = contribution.employee_total(9000, employer)
    for row, figure in expected.items():
        assert sheet_eval.same(found[('Compare', row, 3)], figure), (row, found[('Compare', row, 3)], figure)


def test_J148_base_pct_is_blank_on_the_base_itself_and_through_IFERROR_without_a_base():
    book = Book()
    sheet = book.sheet('Compare')
    cells.text(sheet, 2, 7, 'Current · Aetna')
    for col, pick, monthly in ((3, 'Current · Aetna', 1000), (5, 'Cigna', 950), (7, None, None)):
        cells.text(sheet, 7, col, pick)
        cells.number(sheet, 15, col, monthly, '0')
    cells.number(sheet, 15, 9, 1000, '0')
    for col in (3, 5):
        letter = chr(64 + col)
        cells.formula(
            sheet, 16, col, formulas.base_pct(f'{letter}$7', '$G$2', f'{letter}15', '$I$15'), None, '0', sheets=LOOKUPS
        )
    found = sheet_eval.evaluate(book)
    assert found[('Compare', 16, 3)] == ''
    assert found[('Compare', 16, 5)] == -0.05


def test_J147_round_is_half_away_from_zero_at_fifteen_digits_as_excel():
    assert sheet_eval.round_excel(2642.5, 0) == 2643
    assert sheet_eval.round_excel(2.675, 2) == 2.68
    assert sheet_eval.round_excel(-2.5, 0) == -3


def test_J147_a_wrong_stored_result_is_reported_with_its_cell():
    book = _rates_tab((10, 3, 2, 5), (500.00, 1000.50, 900.25, 1500.75))
    sheet = book.by_title('Medical')
    sheet.get(15, 3).result = 17305
    sheet.get(16, 3).result = Decimal(17306 * 12)
    assert sheet_eval.disagreements(book) == [('Medical', 15, 3, 17305, 17306.0)]


def test_J147_the_evaluator_is_as_closed_as_the_grammar():
    book = Book()
    sheet = book.sheet('Medical')
    sheet.put(1, 1, cells.Cell('formula', '=SUMPRODUCT(A2:A3,B2:B3)', ''))
    with pytest.raises(ValueError, match='outside the closed list'):
        sheet_eval.evaluate(book)
