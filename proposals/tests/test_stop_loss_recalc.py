"""The Recalc lane for the stop-loss workbook (plan.md §9.13, §12.6; Q.4, Q.9 row 36): GD5's stored results, the
test-only evaluator and a LibreOffice recalculation of the written file agree, and the verdict row equals GD5's key.

Outside the Fast lane (`pytest -m recalc`); `bash tools/parity/recalc.sh` writes the file to $RECALC_EXPORT and
recalculates it in the parity tools image (the backend has no LibreOffice, so that step skips here)."""

import importlib.util
import os
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from proposals.tests import sheet_eval
from proposals.workbook import stop_loss_build, write
from proposals.workbook.model import FORMULA

pytestmark = [pytest.mark.recalc, pytest.mark.django_db]

ROOT = Path(__file__).resolve().parents[2]
NAME = 'GD5-stop-loss.xlsx'
MAL = 'MAXIMUM ANNUAL LIABILITY (SL + admin + attachment + lasers)'


def _recalc_module():
    spec = importlib.util.spec_from_file_location('parity_recalc', ROOT / 'tools' / 'parity' / 'recalc.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_J166_GD5_stop_loss_stored_results_the_evaluator_and_LibreOffice_agree(gd5, golden_keys, tmp_path):
    book = stop_loss_build.book(gd5.deal)
    assert sheet_eval.disagreements(book) == []
    sheet = book.by_title('Option Comparison')
    row = next(r for (r, c), cell in sheet.cells.items() if c == 2 and cell.value == MAL)
    printed = [sheet.get(row, col).result for col in range(3, 8) if sheet.get(row, col).kind == FORMULA]
    key = golden_keys['GD5']['stop_loss']['plans']
    wanted = [key[ref]['max_annual_liability'] for ref in ('SL-C', 'SL-R', 'SL-A', 'SL-B', 'SL-D')]
    assert [None if v == '' else Decimal(str(v)) for v in printed] == [
        None if w is None else Decimal(w) for w in wanted
    ]
    data = write.to_bytes(book)
    folder = os.environ.get('RECALC_EXPORT') or str(tmp_path)
    os.makedirs(folder, exist_ok=True)
    Path(folder, NAME).write_bytes(data)
    if shutil.which('soffice') is None:
        pytest.skip(f'LibreOffice is missing here: {NAME} is in {folder}; run bash tools/parity/recalc.sh')
    alone = tmp_path / 'alone'
    alone.mkdir(exist_ok=True)
    (alone / NAME).write_bytes(data)
    assert _recalc_module().recalc_dir(str(alone), report=lambda line: None) == {NAME: []}
