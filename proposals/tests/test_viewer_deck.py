"""The Export viewer's deck view on GD1 and through its endpoint (plan.md §13.8 row 30, "done when": the PowerPoint and
PDF chips page through the slides; J107–J111; Q.9 row 30: previews write nothing)."""

import base64
import io
import re

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from pypdf import PdfReader

from proposals.layout import tokens
from proposals.story import build
from proposals.viewer import deck, fit_report

pytestmark = pytest.mark.django_db
WRITES = re.compile(r'^\s*(INSERT|UPDATE|DELETE)\b', re.IGNORECASE)


@pytest.fixture(scope='module')
def gd1_deck(gd1, django_db_blocker):
    with django_db_blocker.unblock():
        return build.deck(gd1.deal)


def _preview(api, deal):
    with CaptureQueriesContext(connection) as queries:
        response = api.get(f'/api/deals/{deal.id}/proposal/preview/', {'file': 'deck'})
    assert not [q['sql'] for q in queries.captured_queries if WRITES.match(q['sql'])]
    return response


def _texts(data):
    return [' '.join(page.extract_text().split()) for page in PdfReader(io.BytesIO(data)).pages]


def test_S30_J109_the_deck_preview_is_the_pdf_download_page_for_page_and_writes_nothing(api, gd1):
    response = _preview(api, gd1.deal)
    assert response.status_code == 200
    assert response['Cache-Control'] == 'private, no-store'
    body = response.json()
    assert body['file'] == 'deck' and body['style'] == 'presentation' and body['draft'] is True  # OQ35
    shown = _texts(base64.b64decode(body['pdf']))
    download = api.get(f'/api/deals/{gd1.deal.id}/proposal/files/pdf/')
    assert shown == _texts(b''.join(download.streaming_content))
    slides = body['slides']
    assert [slide['n'] for slide in slides] == list(range(1, len(shown) + 1))
    assert all(slide['title'] in text for slide, text in zip(slides, shown, strict=True))
    assert slides[0]['kind'] == 'cover'
    medical = next(slide for slide in slides if slide['kind'] == 'table')
    assert medical['line'] == 'medical' and medical['title'].startswith('Medical — Replacing:')
    assert [s['title'] for s in slides if s['chart']] == ['What you pay today and what we recommend']  # J.5 B22


def test_S30_J111_each_slide_carries_its_speaker_notes_from_the_page_log(gd1_deck):
    slides = deck.slides(gd1_deck['pages'])
    assert [slide['notes'] for slide in slides] == [page['notes'] for page in gd1_deck['pages']]
    assert any(slide['notes'] for slide in slides if slide['kind'] == 'table')


def test_S30_J110_each_plan_set_reports_how_its_table_fitted_on_its_first_slide(gd1_deck):
    slides = deck.slides(gd1_deck['pages'])
    heads = [slide for slide in slides if slide['kind'] == 'table' and not slide['continued']]
    assert heads and all(slide['fit'] for slide in heads)
    for slide in heads:
        fit = slide['fit']
        assert fit['outcome'] in ('fits', 'notes_follow', 'runs_on')
        assert tokens.TABLE_TYPE['floor'] <= fit['size'] <= tokens.TABLE_TYPE['cell']
        assert fit['slides'][0] == slide['n']
        assert fit['money_slide'] in fit['slides']  # each GD1 set prints its rates or cost
        assert fit['tall_rows'] == [] or all(row['lines'] > tokens.MAX_ROW_LINES for row in fit['tall_rows'])
    assert all(slide['fit'] is None for slide in slides if slide['kind'] != 'table' or slide['continued'])


def _cell(row, col, kind, words, lines=1):
    para = {'lines': [[{'text': words if n == 0 else 'more'}] for n in range(lines)]}
    return {'t': 'cell', 'row': row, 'col': col, 'kind': kind, 'text': {'t': 'text', 'paragraphs': [para]}}


def _page(n, title, line, fit=None, continued=False, cells=()):
    table = {'t': 'table', 'cells': list(cells)}
    page = {'n': n, 'kind': 'content', 'title': title, 'line': line, 'continued': continued, 'fit': fit}
    return dict(page, notes=[], frames=[table])


def test_S30_J110_a_run_on_table_names_its_slides_where_its_money_starts_and_its_tall_rows():
    fit = {'outcome': 'runs_on', 'size': 8.0, 'floor': 8.0, 'rows_over': 1}
    pages = [
        _page(1, 'Executive summary', None),
        _page(
            2,
            'Medical — Aetna',
            'medical',
            fit,
            cells=[_cell(1, 0, 'row', 'Office visits', 3), _cell(1, 1, 'row', '$20')],
        ),
        _page(
            3,
            'Medical — Aetna (continued)',
            'medical',
            continued=True,
            cells=[_cell(2, 0, 'band', 'Rates', 1), _cell(3, 0, 'row', 'Employee only')],
        ),
        _page(
            4, 'Dental — Delta', 'dental', dict(fit, outcome='fits', size=12.0), cells=[_cell(1, 0, 'cost', 'Monthly')]
        ),
    ]
    assert fit_report.runs(pages) == [(1, [1, 2]), (3, [3])]
    report = fit_report.of(pages, (1, [1, 2]))
    assert report['outcome'] == 'runs_on' and report['slides'] == [2, 3] and report['money_slide'] == 3
    assert report['tall_rows'] == [{'label': 'Office visits more more', 'lines': 3}]
    assert fit_report.of(pages, (3, [3]))['money_slide'] == 4
    slides = deck.slides(pages)
    assert [s['kind'] for s in slides] == ['page', 'table', 'table', 'table']
    assert slides[1]['fit']['slides'] == [2, 3] and slides[2]['fit'] is None and slides[2]['continued']


def test_S30_J114_the_preview_says_how_a_slide_prints_on_letter(api, gd1):
    body = _preview(api, gd1.deal).json()
    assert body['paper'] == {'scale': 75.0, 'sheet': 'landscape', 'as_is': False, 'inner': 0.9091}
