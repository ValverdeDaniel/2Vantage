"""The Perf lane for the Overview (plan.md §12.1, Q.7: "Overview, confidence, journey — fixed queries, ≤300 ms"): the
deal Overview's read on GD-Big (600 plans) within 300 ms. `pytest -m perf overview` (kept out of the Fast lane by
pytest.ini's addopts); run with `-s` to see the measured figure."""

import time

import pytest

pytestmark = [pytest.mark.perf, pytest.mark.django_db]


def timed(call, repeat=3):
    """The best of `repeat` runs (a cold first run measures the machine, not the read) and the last result."""
    best, result = None, None
    for _ in range(repeat):
        start = time.perf_counter()
        result = call()
        took = time.perf_counter() - start
        best = took if best is None else min(best, took)
    return best, result


def test_Q7_the_overview_of_GD_Big_stays_within_300_ms(api, gd_big):
    took, response = timed(lambda: api.get(f'/api/deals/{gd_big.id}/overview/'))
    print(f'\noverview, GD-Big (600 plans): {took * 1000:.0f} ms, {len(response.content) / 1000:.1f} kB')
    assert response.status_code == 200 and took <= 0.3
