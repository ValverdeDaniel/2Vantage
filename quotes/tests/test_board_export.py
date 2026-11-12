"""⤓ Export, the board as Excel (plan.md §9.14; F93, J98, J153, J167; Q.9 row 9): the file read back equals the
comparison payload it was built from — the same plans in the order drawn, the same columns and the same figures —
current plans ride along as baselines, a subset says so, text stays text, and a file that prints lasers is a logged
download. GD1's export is in test_golden_advisor.py (the module that builds GD1 once)."""

import io

import pytest
from openpyxl import load_workbook

from conftest import make_deal
from deals.models import Activity
from quotes import board_presets, services
from quotes.selectors import comparison

pytestmark = pytest.mark.django_db

URL = '/api/deals/{}/plans/board-export/'


def read(response):
    assert response.status_code == 200, response.content
    assert response['Content-Disposition'].startswith('attachment;')
    sheet = load_workbook(io.BytesIO(b''.join(response.streaming_content))).active
    return [[cell.value for cell in row] for row in sheet.iter_rows()]


@pytest.fixture
def board(user):
    deal = make_deal(user)
    plan = lambda **kw: services.create_plan(user, deal, line='medical', **kw)  # noqa: E731
    current = plan(
        role='current', carrier='Aetna', name='HMO 1500', values={'deductible_single': '1500', 'rate_ee': '500'}
    )
    renewal = plan(role='renewal', carrier='Aetna', name='HMO 1500', renews_id=current.id, values={'rate_ee': '540'})
    quote = plan(role='alternate', carrier='Cigna', name='=1+1', replaces_ids=[current.id], values={'rate_ee': '480'})
    services.set_enrollment(user, deal, 'medical', plans=[{'id': current.id, 'enrollment': {'EE': 10}}])
    return deal, current, renewal, quote


def test_F93_the_export_equals_the_payload(api, board):
    deal, current, renewal, quote = board
    keys = ['total', 'delta', 'deductible_single', 'rate_ee', 'network_type', 'flags']
    rows = read(api.get(URL.format(deal.id), {'line': 'medical', 'columns': ','.join(keys)}))
    assert rows[0][0] == f'{deal.client.name} — Medical Quote Comparison'
    header, body = rows[4], rows[5:]
    labels = {d['key']: d['label'] for d in board_presets.DERIVED}
    assert header == [
        '★',
        'Carrier',
        'Plan',
        'Status',
        labels['total'],
        labels['delta'],
        'Deductible (Single)',
        'Rate — EE',
        labels['network_type'],
    ]  # Flags is a screen nag: it does not travel
    payload = comparison(deal, 'medical')
    assert [row[2] for row in body] == [plan['name'] for plan in payload['plans']]
    for row, plan in zip(body, payload['plans'], strict=True):
        assert row[1] == plan['carrier']
        assert row[4] == plan['premium']['monthly']
        assert row[5] == ('baseline' if plan['role'] == 'current' else plan['change']['pct'])
        assert row[7] == float(plan['values']['rate_ee'])
    assert body[0][3] == 'CURRENT'
    assert body[0][6] == 1500


def test_F93_the_file_keeps_the_screen_order_and_pins_the_current_plans(api, board):
    deal, current, renewal, quote = board
    rows = read(api.get(URL.format(deal.id), {'line': 'medical', 'plans': f'{quote.id},999999', 'columns': 'rate_ee'}))
    assert [row[2] for row in rows[5:]] == ['HMO 1500', '=1+1']  # the current plan first, an unknown id dropped
    assert '1 of 2 quoted plans — filtered on the advisor board' in rows[2][0]
    assert 'current plan included as the baseline' in rows[2][0]
    reordered = read(
        api.get(URL.format(deal.id), {'line': 'medical', 'plans': f'{current.id},{quote.id},{renewal.id}'})
    )
    assert [row[2] for row in reordered[5:]] == ['HMO 1500', '=1+1', 'HMO 1500']


def test_F34_F93_transposed_is_the_same_board_turned(api, board):
    deal = board[0]
    query = {'line': 'medical', 'columns': 'total,delta,rate_ee'}
    rows = read(api.get(URL.format(deal.id), query))
    turned = read(api.get(URL.format(deal.id), {**query, 'orientation': 'cols'}))
    grid = [row for row in rows[4:]]
    assert [row[: len(grid) + 1] for row in turned[4:]] == [list(col) for col in zip(*grid, strict=True)]


def test_J153_text_written_into_the_file_stays_text(api, board):
    deal = board[0]
    response = api.get(URL.format(deal.id), {'line': 'medical'})
    sheet = load_workbook(io.BytesIO(b''.join(response.streaming_content))).active
    cell = next(c for row in sheet.iter_rows() for c in row if c.value == '=1+1')
    assert cell.data_type == 's'


def test_F93_a_column_the_line_lacks_and_screen_only_keys_are_dropped(api, board):
    deal = board[0]
    rows = read(
        api.get(URL.format(deal.id), {'line': 'medical', 'columns': 'star,carrier,den_annual_max,nope,rate_ee'})
    )
    assert rows[4] == ['★', 'Carrier', 'Plan', 'Status', 'Rate — EE']


def test_F93_bad_ids_and_lines_answer_400(api, board):
    deal = board[0]
    assert api.get(URL.format(deal.id), {'line': 'medical', 'plans': '12,abc'}).status_code == 400
    assert api.get(URL.format(deal.id), {'line': 'nope'}).status_code == 400


def test_J98_a_board_that_prints_lasers_is_a_logged_download(api, user):
    deal = make_deal(user)
    services.create_plan(
        user,
        deal,
        line='stop_loss',
        role='current',
        carrier='Sun Life',
        name='Spec 50k',
        values={'sl_lasers': 'Synthetic-1 80000'},
    )
    plain = api.get(URL.format(deal.id), {'line': 'stop_loss', 'columns': 'sl_spec_deductible'})
    assert plain.status_code == 200
    assert not Activity.objects.filter(deal=deal, action='downloaded').exists()
    with_lasers = api.get(URL.format(deal.id), {'line': 'stop_loss', 'columns': 'sl_lasers'})
    assert with_lasers.status_code == 200
    row = Activity.objects.get(deal=deal, action='downloaded')
    assert row.area == 'quotes' and 'Synthetic' not in row.summary


def test_J98_the_plan_template_download_is_logged(api, board):
    deal = board[0]
    before = Activity.objects.filter(deal=deal).exclude(action='downloaded').count()
    assert api.get(f'/api/deals/{deal.id}/plans/template/').status_code == 200
    assert Activity.objects.filter(deal=deal, action='downloaded', area='quotes').count() == 1
    assert Activity.objects.filter(deal=deal).exclude(action='downloaded').count() == before
