"""What Work with Claude is told about the Export viewer (plan.md §10.6, §13.8 row 30; J120: the browser sends the
viewer state; no rebuild per turn)."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from ai import turn_prompt
from proposals.viewer import turn

FIT = {
    'n': 6,
    'title': 'Medical — Replacing: Aetna Open Access HDHP 3300',
    'outcome': 'fits',
    'size': 9,
    'floor': 8,
    'slides': [6],
    'money_slide': 6,
    'tall_rows': [],
}
RUN_ON = dict(FIT, n=9, title='Medical — Cigna', outcome='runs_on', size=8, slides=[9, 10], money_slide=10)
RUN_ON['tall_rows'] = ['Office visits']


def _deck(file, **extra):
    viewer = {
        'file': file,
        'slide': {'n': 6, 'title': FIT['title']},
        'slides': 17,
        'draft': True,
        'fits': [FIT, RUN_ON],
    }
    return {'tab': 'advisor', 'viewer': {**viewer, **extra}}


def test_S30_J120_claude_is_told_the_file_the_slide_and_how_each_table_fitted():
    words = turn.provide(None, _deck('powerpoint'))
    assert words.startswith('<export-viewer>') and words.endswith('</export-viewer>')
    assert "the client PowerPoint's 17 slides" in words and '(a draft, not issued)' in words
    assert f'On screen: slide 6, "{FIT["title"]}".' in words
    assert (
        f'- slide 6 "{FIT["title"]}": fits on one slide at 9 pt; its rates and totals are on the same slide.' in words
    )
    assert 'runs onto 2 slides even at 8 pt; its rates and totals start on slide 10, apart from the benefits' in words
    assert 'rows over two lines: Office visits' in words


def test_S30_J120_on_paper_claude_is_told_the_scale_and_each_tables_printed_type():
    words = turn.provide(None, _deck('paper', paper={'scale': 75, 'sheet': 'landscape'}))
    assert "the client PDF's 17 pages, its pages the PowerPoint's slides one for one" in words
    assert 'at 75% on Letter landscape, inside a half-inch margin' in words
    assert 'fits on one page at 9 pt, printed at 6.8 pt' in words


def test_S30_J120_on_the_spreadsheet_claude_is_told_the_tab():
    words = turn.provide(None, {'tab': 'advisor', 'viewer': {'file': 'excel', 'tab': 'Dynamic Medical Compare'}})
    assert 'the client spreadsheet as it would download now, on the "Dynamic Medical Compare" tab.' in words


def test_S30_J120_what_the_browser_sends_is_data_cut_to_size_and_junk_says_nothing():
    assert turn.provide(None, {'tab': 'advisor'}) == ''
    assert turn.provide(None, {'tab': 'advisor', 'viewer': {'file': 'web'}}) == ''
    assert turn.provide(None, {'tab': 'advisor', 'viewer': 'powerpoint'}) == ''
    junk = turn.provide(
        None, _deck('pdf', slide={'n': 'x'}, fits=[{'n': True}, 'x', dict(FIT, size='huge')], slides=-3)
    )
    assert 'On screen' not in junk and 'pages' in junk and '- page 6' in junk and 'no fit recorded' in junk
    long = turn.provide(None, _deck('pdf', slide={'n': 2, 'title': 'x' * 5000}))
    assert 'x' * turn.MAX_TITLE in long and 'x' * (turn.MAX_TITLE + 1) not in long


@pytest.mark.django_db
def test_S30_J120_the_turn_context_carries_the_viewer_without_building_anything(gd1):
    turn_prompt.context(gd1.deal, {'tab': 'advisor'}, lands='')  # the deal's own rows, read once
    with CaptureQueriesContext(connection) as without:
        turn_prompt.context(gd1.deal, {'tab': 'advisor'}, lands='')
    with CaptureQueriesContext(connection) as queries:
        context = turn_prompt.context(gd1.deal, _deck('powerpoint'), lands='')
    assert '<export-viewer>' in context and 'fits on one slide at 9 pt' in context
    assert len(queries.captured_queries) == len(without.captured_queries)  # told, never rebuilt (J.5 B21)
