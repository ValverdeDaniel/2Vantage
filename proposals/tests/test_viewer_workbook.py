"""The Export viewer's Excel view on GD1 and through its endpoint (plan.md §13.8 row 28, "done when": the Excel chip
pages through every tab as the file shows it; previews write nothing; J105, J107, J116–J118; Q.9 row 28:
`look(write(model))`, previews write nothing)."""

import io
import re

import openpyxl
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from documents.sheet_look import look
from proposals.viewer import workbook as viewer
from proposals.viewer.look import model_look
from proposals.viewer.workbook_checks import HASHED, TabCells
from proposals.workbook import build, write
from proposals.workbook import text as t

pytestmark = pytest.mark.django_db
WRITES = re.compile(r'^\s*(INSERT|UPDATE|DELETE)\b', re.IGNORECASE)


@pytest.fixture(scope='module')
def gd1_book(gd1, django_db_blocker):
    with django_db_blocker.unblock():
        book = build.book(gd1.deal)
    raw = write.to_bytes(book)
    return {
        'book': book,
        'file': openpyxl.load_workbook(io.BytesIO(raw)),
        'values': openpyxl.load_workbook(io.BytesIO(raw), data_only=True),
    }


def _preview(api, deal, **query):
    with CaptureQueriesContext(connection) as queries:
        response = api.get(f'/api/deals/{deal.id}/proposal/preview/', {'file': 'workbook', **query})
    assert not [q['sql'] for q in queries.captured_queries if WRITES.match(q['sql'])]
    return response


def test_S28_J107_the_preview_opens_on_the_files_own_tab_writes_nothing_and_is_never_stored(api, gd1, gd1_book):
    response = _preview(api, gd1.deal)
    assert response.status_code == 200
    assert response['Cache-Control'] == 'private, no-store'
    body = response.json()
    written = gd1_book['file']
    assert [tab['title'] for tab in body['tabs']] == written.sheetnames
    assert body['opens_on'] == written.active.title == 'Dynamic Medical Compare'
    assert body['tab']['title'] == body['opens_on']
    assert body['draft'] is True  # not issued (OQ35)


def test_S28_J116_each_tab_is_asked_for_by_name_and_an_unknown_one_opens_the_files_tab(api, gd1):
    body = _preview(api, gd1.deal, tab='Dental').json()
    assert body['tab']['title'] == 'Dental'
    assert _preview(api, gd1.deal, tab='No such tab').json()['tab']['title'] == body['opens_on']


def _same_look(book, written):
    for sheet in book.sheets:
        worked = TabCells(sheet)
        mine = model_look(sheet, worked.rows, worked.cols)
        theirs = look(written, sheet.title, 0, worked.rows, worked.cols)
        mine['merges'], theirs['merges'] = sorted(mine['merges']), sorted(theirs['merges'])
        assert mine == theirs, sheet.title


def test_S28_J116_the_viewers_look_of_each_tab_is_look_of_the_written_file(gd1_book, gd2, django_db_blocker):
    """look(write(model)): the look the viewer reads from the model is documents' look of the download, every tab of
    GD1 and of GD2 (one current plan: Compare's other shape)."""
    _same_look(gd1_book['book'], gd1_book['file'])
    with django_db_blocker.unblock():
        book = build.book(gd2.deal)
    _same_look(book, openpyxl.load_workbook(io.BytesIO(write.to_bytes(book))))


def test_S28_J116_every_value_reads_as_the_file_stores_and_formats_it(gd1_book):
    book, written, values = gd1_book['book'], gd1_book['file'], gd1_book['values']
    for sheet in book.sheets:
        found = TabCells(sheet).run()[0]
        assert found, sheet.title
        for r, c, shown, flags, *_extra in found:
            if flags & HASHED:
                continue
            stored = values[sheet.title].cell(r + 1, c + 1).value
            fmt = written[sheet.title].cell(r + 1, c + 1).number_format
            assert shown == t.display(stored, fmt)[0], f'{sheet.title}!{r + 1},{c + 1}'


def test_S28_J116_the_grid_draws_the_written_files_sizes_merges_and_panes(gd1_book):
    book = gd1_book['book']
    compare = book.by_title('Dynamic Medical Compare')
    tab = viewer.tab_payload(book, compare)
    sheet_look = look(gd1_book['file'], compare.title, 0, tab['rows'], tab['cols'])
    assert tab['col_px'] == sheet_look['col_px']
    assert sorted(tab['merges']) == sorted(sheet_look['merges'])
    assert tab['freeze'] == {'rows': compare.freeze[0] - 1, 'cols': compare.freeze[1] - 1}
    assert tab['zoom'] == compare.zoom
    assert len(tab['looks']) == tab['rows'] and all(len(row) == tab['cols'] for row in tab['looks'])
    assert tab['print']['pages'] and tab['print']['scale'] == compare.print['scale']


def test_S28_J116_the_compare_pick_offers_the_all_plans_list_read_only(gd1_book):
    book = gd1_book['book']
    tab = viewer.tab_payload(book, book.by_title('Dynamic Medical Compare'))
    bank = book.by_title('Medical All Plans')
    names = {cell.value for (row, col), cell in bank.cells.items() if col == 1 and isinstance(cell.value, str)}
    assert tab['dropdowns']
    for drop in tab['dropdowns']:
        assert drop['list'] and set(drop['list']) <= names
        assert drop['prompt']


def test_S28_J118_the_tab_list_carries_each_tabs_own_check_counts(gd1_book):
    body = viewer.from_book(gd1_book['book'], 'Medical All Plans')
    counts = {tab['title']: tab['counts'] for tab in body['tabs']}
    assert counts['Medical All Plans'] == body['tab']['counts']
    for kind, found in body['tab']['checks'].items():
        assert len(found) == min(body['tab']['counts'][kind], 40)
        assert all(check['cell'] and check['text'] for check in found)


def test_S28_J107_a_proposal_with_nothing_to_present_refuses_in_the_downloads_words(api, deal):
    download = api.get(f'/api/deals/{deal.id}/proposal/files/xlsx/')
    response = _preview(api, deal)
    assert response.status_code == download.status_code == 409
    assert response.json()['detail'] == download.json()['detail']
    assert response['Cache-Control'] == 'private, no-store'


def test_S28_J105_a_file_the_viewer_does_not_show_answers_400(api, deal):
    response = api.get(f'/api/deals/{deal.id}/proposal/preview/', {'file': 'web'})
    assert response.status_code == 400
    assert 'workbook' in response.json()['detail']
