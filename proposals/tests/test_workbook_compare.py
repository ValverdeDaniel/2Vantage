"""The client spreadsheet's Compare, Composite Rates and All Plans tabs (plan.md §9.4; J148–J150, J154; OQ39): who is
on the list and in what order, what the Compare columns open on, and that every formula's stored result is the cell it
looks up or quotes' figure for the pick at the shared counts (worked by hand below)."""

import io

import pytest
from openpyxl import load_workbook

from conftest import make_deal
from proposals.tests import workbook_shop
from proposals.tests.workbook_shop import (
    _all_plans,
    _book,
    _column,
    _compare,
    _picks,
    _plan,
    _rates,
    _tab,
)
from proposals.workbook import bank, write
from proposals.workbook.model import FORMULA, TEXT
from proposals.workbook.tabs import bank_map
from quotes import services as plans

pytestmark = pytest.mark.django_db
shop = workbook_shop.shop  # the synthetic deal (a fixture)


def test_J149_compare_columns_open_on_the_current_then_recommended_then_starred_plans(shop):
    picks = _picks(_compare(_book(shop['deal'])))
    assert picks[:3] == ['Current · Aetna — HMO 1000', '★ Cigna — LocalPlus 1000', '★ Cigna — Open Access 2000']
    assert set(picks[3:]) == {bank.SELECT}


def test_J149_J154_all_plans_lists_the_quotes_off_the_proposal_but_not_a_hidden_carrier_or_an_unrated_quote(shop):
    sheet = _all_plans(_book(shop['deal']))
    labels = _column(sheet, 1)
    assert labels[:6] == [
        '— CURRENT PLAN —',
        'Current · Aetna — HMO 1000',
        '— ★ PROPOSED —',
        '★ Cigna — LocalPlus 1000',
        '★ Cigna — Open Access 2000',
        '— Aetna —',
    ]
    assert 'Aetna — HMO 1000' in labels and 'UnitedHealthcare — Choice Plus' in labels and 'Oscar — Bronze' in labels
    assert not any('Humana' in label or 'Kaiser' in label for label in labels)
    notes = [cell.value for (row, col), cell in sheet.cells.items() if col == 1 and cell.kind == TEXT]
    assert '1 quoted plan without rates is not listed.' in notes
    assert '1 quoted plan from a carrier hidden on Markets checked is not listed.' in notes


def test_J150_the_two_thousand_plan_note_says_how_many_more_were_left_off(shop, monkeypatch):
    monkeypatch.setattr(bank, 'MAX_BANK_PLANS', 4)  # three presented plans and one more
    sheet = _all_plans(_book(shop['deal']))
    notes = [cell.value for (row, col), cell in sheet.cells.items() if col == 1 and cell.kind == TEXT]
    assert '2 more quoted plans are not listed: the list holds 4.' in notes


def _slot_value(sheet, row, k):
    return sheet.get(row, 3 + 2 * k).result


def _shown(cell):
    """What a cell shows: a formula's stored result, else its value."""
    return cell.result if cell.kind == FORMULA else cell.value


def test_J148_every_lookup_stores_the_all_plans_cell_it_finds(shop):
    book = _book(shop['deal'])
    compare, listed = _compare(book), _all_plans(book)
    row_of = {listed.get(row, 1).value: row for (row, col) in listed.cells if col == 1 and listed.get(row, 1).value}
    header = {listed.get(4, col).value: col for (row, col) in listed.cells if row == 4}
    compare_rows = {compare.get(row, 1).value: row for (row, col) in compare.cells if col == 1}
    for k, pick in enumerate(_picks(compare)[:3]):
        source = row_of[pick]
        assert _slot_value(compare, 6, k) == listed.get(source, header['Carrier']).value
        assert _slot_value(compare, 5, k) == (listed.get(source, header['Status']).value or '')
        rate = listed.get(source, header['Employee Only']).value
        assert _slot_value(compare, compare_rows['Employee Only'], k) == rate
    blank_slot = 5
    assert _slot_value(compare, compare_rows['Employee Only'], blank_slot) == ''


def test_J148_compare_totals_store_the_plans_premiums_at_the_shared_counts(shop):
    """Counts 10/2/1/3. Today 500×10 + 1000×2 + 900 + 1400×3 = 12,100; LocalPlus 4,805 + 1,922.20 + 865.45 +
    4,036.20 = 11,628.85 → 11,629; Open Access 4,701.20 + 1,880 + 850 + 3,900 = 11,331.20 → 11,331."""
    compare = _compare(_book(shop['deal']))
    rows = {compare.get(row, 1).value: row for (row, col) in compare.cells if col == 1}
    monthly = [_slot_value(compare, rows['Total Monthly Premium'], k) for k in range(4)]
    assert monthly == [12100, 11629, 11331, '']
    assert [_slot_value(compare, rows['Total Annual Premium'], k) for k in range(3)] == [145200, 139548, 135972]
    assert [_shown(compare.get(row, 2)) for row in (rows['Employee Only'], rows['Employee + Family'])] == [10, 3]
    change = rows['% Difference from Current']
    assert compare.get(change, 3).result == '' and compare.get(change, 4).result == ''  # the base itself
    # EE only (480.50 − 500) / 500 = −3.9%; total (11,629 − 12,100) / 12,100 = −3.9%
    assert compare.get(change, 5).result == pytest.approx(-0.039) and compare.get(change, 6).result == pytest.approx(
        -0.039
    )
    renewal = rows['% Difference from Renewal']
    assert all(compare.get(renewal, 3 + k).result == '' for k in range(6))


def test_J148_the_employer_contribution_starts_from_todays_share(shop):
    """80% of the employee rate and half the dependent cost: on LocalPlus 16 × 480.50 × 0.8 = 6,150.40 → 6,150;
    dependents (2 × 480.60 + 384.95 + 3 × 864.90) × 0.5 = 1,970.43 → 1,970; employer 8,120, employees 3,509."""
    compare = _compare(_book(shop['deal']))
    rows = {compare.get(row, 1).value: row for (row, col) in compare.cells if col == 1}
    assert compare.get(rows['Employees'], 2).value == pytest.approx(0.8)
    assert compare.get(rows['Dependents'], 2).value == pytest.approx(0.5)
    assert _slot_value(compare, rows['Employees'], 1) == 6150
    assert _slot_value(compare, rows['Dependents'], 1) == 1970
    assert _slot_value(compare, rows['Employer Total (monthly)'], 1) == 8120
    assert _slot_value(compare, rows['Employee Total (monthly)'], 1) == 3509
    assert _slot_value(compare, rows['Employer Total (annual)'], 1) == 97440


def test_J150_all_plans_totals_follow_the_compare_counts_and_fall_back_to_the_quoted_premium(shop):
    sheet = _all_plans(_book(shop['deal']))
    header = {sheet.get(4, col).value: col for (row, col) in sheet.cells if row == 4}
    row_of = {sheet.get(row, 1).value: row for (row, col) in sheet.cells if col == 1 and sheet.get(row, 1).value}
    oscar = row_of['Oscar — Bronze']
    monthly = sheet.get(oscar, header['Monthly Total'])
    assert monthly.kind == FORMULA and "'Dynamic Medical Compare'!$B$" in monthly.value
    assert monthly.result == 11000  # an enrolled tier has no rate: the quoted premium, half up
    assert sheet.get(row_of['UnitedHealthcare — Choice Plus'], header['Monthly Total']).result == 11880
    pct = sheet.get(row_of['★ Cigna — LocalPlus 1000'], header['% from Current']).result
    assert pct == pytest.approx(-0.039)
    assert sheet.get(row_of['Current · Aetna — HMO 1000'], header['% from Current']).kind != FORMULA
    assert sheet.autofilter[0] == bank_map.FIRST_ROW - 1


def test_J150_composite_rates_comes_only_when_the_list_holds_plans_the_rates_tab_does_not_show(shop, user):
    titles = [sheet.title for sheet in _book(shop['deal']).sheets]
    assert 'Medical Composite Rates' in titles
    deal = make_deal(user, name='Every quote prints (synthetic)')
    current = _plan(user, deal, 'Aetna', 'HMO', role='current', values=_rates('500', '1000', '900', '1400'))
    plans.set_enrollment(user, deal, 'medical', plans=[{'id': current.id, 'enrollment': {'EE': 5}}])
    _plan(user, deal, 'Cigna', 'PPO', values=_rates('480', '960', '860', '1340'))
    titles = [sheet.title for sheet in _book(deal).sheets]
    assert 'Dynamic Medical Compare' in titles and 'Medical All Plans' in titles
    assert 'Medical Composite Rates' not in titles


def test_J150_a_composite_card_equals_the_compare_column_for_its_plan(shop):
    book = _book(shop['deal'])
    compare, cards = _compare(book), _tab(book, 'Medical Composite Rates')
    rows = {compare.get(row, 1).value: row for (row, col) in compare.cells if col == 1}
    card_rows = {}
    for (row, col), cell in sorted(cards.cells.items()):
        if col == 1 and cell.kind == TEXT and cell.value not in card_rows:
            card_rows[cell.value] = row
    assert cards.get(card_rows['Total Monthly Premium'], 3).result == _slot_value(
        compare, rows['Total Monthly Premium'], 0
    )
    count = cards.get(card_rows['Employee Only'], 2)
    source = f"'Dynamic Medical Compare'!$B${rows['Employee Only']}"
    assert count.kind == FORMULA and count.value == f'=IF({source}="","",{source})'  # blank stays blank in Excel
    assert count.result == 10


def test_J148_J153_a_label_that_starts_like_a_formula_or_holds_a_wildcard_stays_text(shop, user):
    _plan(user, shop['deal'], '=HYPERLINK("http://x")', 'Plan * ?', values=_rates('1', '2', '3', '4'))
    book = _book(shop['deal'])
    labels = _column(_all_plans(book), 1)
    label = next(text for text in labels if 'HYPERLINK' in text)
    assert not label.startswith('=') and '*' not in label and '?' not in label
    data = load_workbook(io.BytesIO(write.to_bytes(book)))
    found = [c for row in data['Medical All Plans'].iter_rows() for c in row if 'HYPERLINK' in str(c.value or '')]
    assert {label, '=HYPERLINK("http://x")'} <= {c.value for c in found}  # the label; the carrier as typed
    assert all(c.data_type == 's' for c in found)


def test_J148_the_compare_tab_writes_with_its_frozen_header_zoom_and_drop_downs(shop):
    data = load_workbook(io.BytesIO(write.to_bytes(_book(shop['deal']))))
    sheet = data['Dynamic Medical Compare']
    assert sheet.freeze_panes == 'C8' and sheet.sheet_view.zoomScale == 110
    sources = [str(rule.formula1) for rule in sheet.data_validations.dataValidation]
    assert sources and all("'Medical All Plans'!$A$" in source for source in sources)
    assert sheet.oddHeader.center.text == 'Draft for review'  # a draft says so in its page header (J102)


# The rates tab's geometry (tabs/rates.py) for one current plan in columns B:C, its counts on rows 12 to 15.
RATES_GEOMETRY = {
    'current': {'k': 0, 'count': 2, 'rate': 3},
    'rows': {'tiers': (12, 13, 14, 15)},
    'counts': {'EE': 10, 'ES': 2, 'EC': 1, 'FAM': 3},
}


def test_J148_counts_link_to_the_rates_tab_with_one_current_plan(shop):
    compare = _compare(_book(shop['deal'], maps={'medical': RATES_GEOMETRY}))
    rows = {compare.get(row, 1).value: row for (row, col) in compare.cells if col == 1}
    count = compare.get(rows['Employee + Spouse'], 2)
    assert count.kind == FORMULA and count.value == "='Medical'!$B$13" and count.result == 2
    assert _slot_value(compare, rows['Total Monthly Premium'], 0) == 12100
    notes = [cell.value for (row, col), cell in compare.cells.items() if col == 1 and cell.kind == TEXT]
    assert "The counts follow the current plan's counts on the 'Medical' tab; type over them to try other numbers." in (
        notes
    )
