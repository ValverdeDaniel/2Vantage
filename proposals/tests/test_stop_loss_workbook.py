"""The stop-loss analysis workbook (plan.md §9.13; J166, F106, G117, OQ43, OQ104; Q.9 row 36): GD5's five tabs, every
stored result equal to the test-only evaluator and to GD5's hand-worked key, lasers by position with no claimant in
the file, the Binding Notes from the `disclosure_state` provider, and the refusals."""

import io
import re
from decimal import Decimal

import openpyxl
import pytest

from conftest import make_deal
from deals.models import Activity
from proposals.tests import sheet_eval
from proposals.workbook import stop_loss_build, write
from proposals.workbook.model import FORMULA, NUMBER, TEXT
from proposals.workbook.tabs import stop_loss_look as look
from quotes import providers, services

pytestmark = pytest.mark.django_db

TABS = ['In-Force Snapshot', 'Option Comparison', 'Binding Notes', 'Glossary', 'FIE Rates']
CLAIMANTS = ('J.D.', 'R.K.', 'M.P.')
LASER = re.compile(r'Laser \d+')


def _row(sheet, label):
    """{col: number} on the row whose column-B label is `label`."""
    rows = [r for (r, c), cell in sheet.cells.items() if c == 2 and cell.kind == TEXT and cell.value == label]
    assert rows, f'no "{label}" row on {sheet.title}'
    out = {}
    for (r, c), cell in sheet.cells.items():
        if r == rows[0] and c > 2 and cell.kind in (NUMBER, FORMULA):
            out[c] = cell.value if cell.kind == NUMBER else cell.result
    return [out[c] for c in sorted(out)]


def _exact(text):
    return None if text is None else Decimal(text)


@pytest.fixture(scope='module')
def gd5_book(gd5, django_db_blocker):
    with django_db_blocker.unblock():
        return stop_loss_build.book(gd5.deal)


def test_J166_GD5_five_tabs_in_the_old_order_opening_on_the_snapshot(gd5_book):
    assert gd5_book.titles() == TABS
    assert gd5_book.opens_on == 0


def test_J166_GD5_every_stored_result_is_what_the_formula_gives(gd5_book):
    assert sheet_eval.disagreements(gd5_book) == []


def test_J166_GD5_the_comparison_prints_the_key(gd5_book, golden_keys):
    key = golden_keys['GD5']['stop_loss']['plans']
    sheet = gd5_book.by_title('Option Comparison')
    order = ['SL-C', 'SL-R', 'SL-A', 'SL-B', 'SL-D']  # CURRENT first, then the options in the board's order
    for label, name in (
        ('Annual SL premium', 'annual_premium'),
        ('Annual aggregate attachment', 'annual_attachment'),
        ('Total additional laser liability', 'laser_liability'),
        ('MAXIMUM ANNUAL LIABILITY (SL + admin + attachment + lasers)', 'max_annual_liability'),
        ('Projected cost (SL + admin + expected claims)', 'projected_cost'),
    ):
        printed = [None if value == '' else Decimal(str(value)) for value in _row(sheet, label)]
        assert printed == [_exact(key[ref][name]) for ref in order], label
    vs = [value for value in _row(sheet, 'Max liability vs CURRENT')]
    assert [None if v == '' else Decimal(str(v)) for v in vs] == [
        _exact(key[ref]['vs']['max_annual_liability']) for ref in order[1:]
    ]


def test_J166_GD5_the_snapshot_states_the_in_force_verdict(gd5_book, golden_keys):
    key = golden_keys['GD5']['stop_loss']
    sheet = gd5_book.by_title('In-Force Snapshot')
    mal = _row(sheet, 'MAXIMUM ANNUAL LIABILITY  (SL + admin + attachment + lasers)')
    assert Decimal(str(mal[-1])) == _exact(key['plans']['SL-C']['max_annual_liability'])
    assert _row(sheet, 'Enrolled employees (headcount)') == [key['basis']['lives']]


def test_OQ104_GD5_lasers_print_by_position_and_no_claimant_reaches_the_file(gd5_book, golden_keys):
    wanted = golden_keys['GD5']['stop_loss']['workbook']
    sheet = gd5_book.by_title('Option Comparison')
    labels = sorted(cell.value for (r, c), cell in sheet.cells.items() if c == 2 and LASER.fullmatch(str(cell.value)))
    assert labels == ['Laser 1', 'Laser 2', 'Laser 3']
    data = write.to_bytes(gd5_book)
    found = openpyxl.load_workbook(io.BytesIO(data))
    text = ' '.join(str(cell.value) for ws in found.worksheets for row in ws.iter_rows() for cell in row if cell.value)
    for claimant in CLAIMANTS:
        assert claimant not in text
    snapshot = gd5_book.by_title('In-Force Snapshot')
    rows = look.snapshot_rows(wanted['laser_rows'])
    amounts = [snapshot.get(r, 3).value for r in range(rows['LASER_FIRST'], rows['LASER_FIRST'] + 2)]
    assert amounts == [125000, 90000]


def test_J166_GD5_fie_rates_take_the_medical_enrollment(gd5_book, golden_keys):
    tiers = golden_keys['GD5']['stop_loss']['workbook']['fie_enrolled']
    sheet = gd5_book.by_title('FIE Rates')
    assert [sheet.get(row, 2).value for row in range(3, 7)] == [tiers[t] for t in ('EE', 'ES', 'EC', 'FAM')]


def test_G117_the_binding_notes_read_the_disclosure_provider(gd5, monkeypatch):
    notes = stop_loss_build.book(gd5.deal).by_title('Binding Notes')
    assert notes.get(5, 3).value == 'SIIA disclosure not started'  # the slot's default until slice 43 fills it
    monkeypatch.setitem(providers._slots, 'disclosure_state', lambda deal_id: providers.SIGNED)
    notes = stop_loss_build.book(gd5.deal).by_title('Binding Notes')
    assert [notes.get(row, 3).value for row in (5, 6)] == ['SIIA disclosure signed'] * 2


def test_J166_the_download_writes_nothing_and_names_the_file(api, gd5):
    before = Activity.objects.count()
    response = api.get(f'/api/deals/{gd5.deal.id}/plans/stop-loss/workbook/')
    assert response.status_code == 200
    assert 'golden-stop-loss-synthetic-stop-loss-analysis.xlsx' in response['Content-Disposition']
    body = b''.join(response.streaming_content)
    assert openpyxl.load_workbook(io.BytesIO(body)).sheetnames == TABS
    assert Activity.objects.count() == before


def test_F106_two_in_force_contracts_and_no_contract_refuse_in_words(api, user):
    deal = make_deal(user, requested_lines=['stop_loss'])
    response = api.get(f'/api/deals/{deal.id}/plans/stop-loss/workbook/')
    assert response.status_code == 409 and 'No stop-loss plans' in response.json()['detail']
    for name in ('One', 'Two'):
        services.create_plan(user, deal, line='stop_loss', role='current', carrier='Symetra', name=name)
    response = api.get(f'/api/deals/{deal.id}/plans/stop-loss/workbook/')
    assert response.status_code == 409
    assert response.json()['detail'].startswith('This deal has 2 in-force stop-loss contracts')


def test_J166_no_in_force_contract_still_writes_the_census_and_the_options(user):
    deal = make_deal(user, requested_lines=['stop_loss'])
    services.create_plan(user, deal, line='stop_loss', role='alternate', carrier='Voya', name='Core',
                         values={'sl_spec_rate': '80', 'sl_lasers': 'Q.Q. 90000'})  # fmt: skip
    book = stop_loss_build.book(deal)
    assert sheet_eval.disagreements(book) == []
    snapshot = book.by_title('In-Force Snapshot')
    assert 'No in-force stop-loss contract recorded' in snapshot.get(3, 2).value
    assert book.by_title('Option Comparison').get(6, 3).value == 'Core'
