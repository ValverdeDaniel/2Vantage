"""The Recalc lane (plan.md §9.4 "Correctness requirement", §12.1, §12.6; Q.2, Q.9 row 27): the client spreadsheet's
stored results, the test-only evaluator and a LibreOffice recalculation of the written file all agree.

Outside the Fast lane (`pytest -m recalc`). Each test builds a workbook, holds its stored results to the evaluator and
to the key or worked example, and writes the file to $RECALC_EXPORT (else a temporary folder). LibreOffice lives in
the parity tools image, not the backend: where `soffice` is missing the LibreOffice step skips, and
`bash tools/parity/recalc.sh` recalculates the written files there (tools/parity/recalc.py).
"""

import datetime
import importlib.util
import os
import shutil
from pathlib import Path

import pytest

from conftest import make_deal
from proposals.tests import sheet_eval
from proposals.workbook import build, write
from proposals.workbook.model import FORMULA, NUMBER, TEXT
from quotes import services

pytestmark = [pytest.mark.recalc, pytest.mark.django_db]

ROOT = Path(__file__).resolve().parents[2]
EFFECTIVE = datetime.date(2027, 1, 1)
# One plan per rate basis: plan.md §5.5's worked examples and slice 7's PROVISIONAL ones (quotes/tests/test_math.py),
# OQ103: no signed example was found, so these stand until Stephanie signs hers.
# line: [(role, unit rate or stop-loss rates, enrollment, expected monthly)]
RATE_BASES = {
    'basic_life_add': [
        ('current', {'unit_rate': '0.12'}, {'volume': 1_250_000}, 150),
        ('alternate', {'unit_rate': '0.0996'}, None, 125),  # 124.50, half up; borrows the current plan's volume
    ],
    'voluntary_life': [
        ('current', {'unit_rate': '0.185'}, {'volume': 2_000_000}, 370),
        ('alternate', {'unit_rate': '0.233'}, {'volume': 1_830_000}, 426),
    ],
    'std': [
        ('current', {'unit_rate': '0.42'}, {'volume': 18_450}, 775),
        ('alternate', {'unit_rate': '0.25'}, {'volume': 12_900}, 323),  # 322.50, half up
    ],
    'ltd': [
        ('current', {'unit_rate': '0.45'}, {'volume': 3_000_000}, 1125),
        ('alternate', {'unit_rate': '0.62'}, {'volume': 2_412_600}, 1247),
    ],
    'voluntary_ltd': [('current', {'unit_rate': '0.50'}, {'volume': 1_110_000}, 463)],  # 462.50, half up
    'hsa': [('current', {'unit_rate': '3.50'}, {'lives': 42}, 147)],
    'stop_loss': [('current', {'sl_spec_rate': '85.20', 'sl_agg_rate': '12.10'}, {'lives': 40}, 3892)],
}


def _folder(tmp_path):
    folder = os.environ.get('RECALC_EXPORT') or str(tmp_path)
    os.makedirs(folder, exist_ok=True)
    return folder


def _recalc_module():
    spec = importlib.util.spec_from_file_location('parity_recalc', ROOT / 'tools' / 'parity' / 'recalc.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _three_ways(book, name, tmp_path):
    """Stored results equal the evaluator; the file is written; LibreOffice agrees where it is installed."""
    assert sheet_eval.disagreements(book) == []
    data = write.to_bytes(book)
    folder = _folder(tmp_path)
    Path(folder, name).write_bytes(data)
    if shutil.which('soffice') is None:
        pytest.skip(f'LibreOffice is missing here: {name} is in {folder}; run bash tools/parity/recalc.sh')
    alone = tmp_path / 'alone'
    alone.mkdir(exist_ok=True)
    (alone / name).write_bytes(data)
    assert _recalc_module().recalc_dir(str(alone), report=lambda line: None) == {name: []}


def _row_numbers(sheet, label):
    """The numbers on the row whose column-A label is `label` (one per plan column)."""
    rows = [row for (row, col), cell in sheet.cells.items() if col == 1 and cell.kind == TEXT and cell.value == label]
    assert rows, f'no "{label}" row on {sheet.title}'
    found = {}
    for (row, col), cell in sheet.cells.items():
        if row == rows[0] and col > 1 and cell.kind in (NUMBER, FORMULA):
            found[col] = cell.value if cell.kind == NUMBER else cell.result
    return [found[col] for col in sorted(found)]


def test_J147_GD1_stored_results_the_evaluator_and_LibreOffice_agree(gd1, golden_keys, tmp_path):
    book = build.book(gd1.deal)
    key = golden_keys['GD1']['plans']
    for title, refs in (('Dental', ('DN', 'DNA')), ('Vision', ('VS', 'VS2', 'VSA'))):
        monthly = _row_numbers(book.by_title(title), 'Monthly Total by Product')
        assert monthly == [key[ref]['monthly'] for ref in refs], (title, monthly)
    _three_ways(book, 'GD1.xlsx', tmp_path)


def _rate_bases_deal(user):
    deal = make_deal(user, name='Rate bases (synthetic)', requested_lines=list(RATE_BASES), effective_date=EFFECTIVE)
    for line, plans in RATE_BASES.items():
        made = []
        current = None
        for role, rates, enrollment, _expected in plans:
            plan = services.create_plan(
                user,
                deal,
                line=line,
                role=role,
                carrier='Lincoln' if role == 'current' else 'Sun Life',
                name=f'{line} {role}',
                values=rates,
                replaces_ids=[current.id] if current and role == 'alternate' else (),
            )
            current = current or plan
            if enrollment:
                made.append({'id': plan.id, 'enrollment': enrollment})
        services.set_enrollment(user, deal, line, plans=made)
    return deal


def test_OQ103_every_rate_basis_prints_its_worked_example_and_recalculates_to_it(user, tmp_path):
    deal = _rate_bases_deal(user)
    book = build.book(deal)
    for line, plans in RATE_BASES.items():
        title = next(t for t in book.titles() if t.lower().replace('-', ' ').startswith(_tab_start(line)))
        monthly = _row_numbers(book.by_title(title), 'Estimated Monthly Premium')
        annual = _row_numbers(book.by_title(title), 'Estimated Annual Premium')
        expected = [figure for _role, _rates, _enrollment, figure in plans]
        assert monthly == expected, (line, monthly)
        assert annual == [figure * 12 for figure in expected], (line, annual)
    _three_ways(book, 'rate-bases.xlsx', tmp_path)


def _tab_start(line):
    return {
        'basic_life_add': 'basic life',
        'voluntary_life': 'voluntary life',
        'std': 'short term disability',
        'ltd': 'long term disability',
        'voluntary_ltd': 'voluntary ltd',
        'hsa': 'hsa',
        'stop_loss': 'stop loss',
    }[line]


def test_J147_B33_a_what_if_on_an_unrated_tier_falls_back_to_the_stated_premium_or_blank(user, tmp_path):
    deal = make_deal(user, name='What-if (synthetic)', effective_date=EFFECTIVE)
    stated = services.create_plan(
        user,
        deal,
        line='medical',
        role='current',
        carrier='Aetna',
        name='HMO 1000',
        values={'rate_ee': '500.00', 'group_premium_monthly': '15000'},
    )
    services.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='Cigna',
        name='PPO 1500',
        values={'rate_ee': '480.00'},
        replaces_ids=[stated.id],
    )
    services.set_enrollment(user, deal, 'medical', plans=[{'id': stated.id, 'enrollment': {'EE': 10, 'ES': 2}}])
    book = build.book(deal)
    totals = _row_numbers(book.by_title('Medical'), 'Monthly Total by Product')
    assert totals == [15000, '']
    _three_ways(book, 'what-if.xlsx', tmp_path)
