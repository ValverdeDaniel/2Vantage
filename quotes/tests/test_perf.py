"""The Perf lane (plan.md §12.1, Q.7): time and size budgets on GD-Big. `pytest -m perf` (kept out of the Fast lane by
pytest.ini's addopts). Each budget is Q.7's; run with `-s` to see the measured figures."""

import time

import pytest

from conftest import make_big_deal
from quotes.selectors import deal_state

pytestmark = [pytest.mark.perf, pytest.mark.django_db]

MB = 1_000_000


def timed(call, repeat=3):
    """The best of `repeat` runs (a cold first run measures the machine, not the read) and the last result."""
    best, result = None, None
    for _ in range(repeat):
        start = time.perf_counter()
        result = call()
        took = time.perf_counter() - start
        best = took if best is None else min(best, took)
    return best, result


def comparison(api, deal):
    response = api.get(f'/api/deals/{deal.id}/plans/', {'line': 'medical'})
    assert response.status_code == 200
    return response


def test_Q7_the_comparison_of_600_plans_stays_within_3_MB_and_2_5_s(api, gd_big):
    took, response = timed(lambda: comparison(api, gd_big))
    size = len(response.content)
    print(f'\ncomparison, 600 plans: {size / MB:.2f} MB raw, {took:.2f} s')
    assert len(response.json()['plans']) == 600
    assert size <= 3 * MB and took <= 2.5


def test_Q7_the_comparison_of_400_plans_stays_within_2_MB_and_1_7_s(api, user):
    deal = make_big_deal(user, 400)
    took, response = timed(lambda: comparison(api, deal))
    size = len(response.content)
    print(f'\ncomparison, 400 plans: {size / MB:.2f} MB raw, {took:.2f} s')
    assert size <= 2 * MB and took <= 1.7


def test_Q7_deal_state_and_plan_lines_stay_within_300_ms(api, gd_big):
    state_took, _ = timed(lambda: deal_state(gd_big))
    lines_took, response = timed(lambda: api.get(f'/api/deals/{gd_big.id}/plans/lines/'))
    print(f'\ndeal_state, 600 plans: {state_took * 1000:.0f} ms; plans/lines/: {lines_took * 1000:.0f} ms')
    assert response.status_code == 200
    assert state_took <= 0.3 and lines_took <= 0.3


def test_Q7_the_station_list_of_600_plans_pages_within_the_comparisons_budget(api, gd_big):
    """The station's List (slice 17) sorts every value of GD-Big's files on the server and sends 200 a page; Q.7 has
    no row of its own for it, so it is held to the comparison's 600-plan budget."""
    took, response = timed(lambda: api.get(f'/api/deals/{gd_big.id}/plans/sources/'))
    size = len(response.content)
    body = response.json()
    print(f'\nstation List, 600 plans: {body["total"]} values, a page {size / MB:.2f} MB, {took:.2f} s')
    assert len(body['rows']) == body['page_size'] and size <= 3 * MB and took <= 2.5
