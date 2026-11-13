"""The Perf lane for the data confidence (plan.md §12.1; Q.7 "Overview, confidence, journey — fixed queries, ≤300 ms";
Q.9 row 64): the confidence read on GD-Big (600 plans, ~19,800 read values, half approved) within 300 ms, in the same
queries as a small deal. `pytest -m perf review` (kept out of the Fast lane); run with `-s` to see the figures."""

import time

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import make_big_deal

pytestmark = [pytest.mark.perf, pytest.mark.django_db]


def test_Q7_the_confidence_of_GD_Big_stays_within_300_ms_in_fixed_queries(api, user, gd_big):
    url = f'/api/deals/{gd_big.id}/confidence/'
    best, response = None, None
    for _ in range(3):  # the best of three: a cold first run measures the machine, not the read
        start = time.perf_counter()
        with CaptureQueriesContext(connection) as big:
            response = api.get(url)
        took = time.perf_counter() - start
        best = took if best is None else min(best, took)
    small = make_big_deal(user, 10, name='Small (synthetic)')
    with CaptureQueriesContext(connection) as few:
        api.get(f'/api/deals/{small.id}/confidence/')
    body = response.json()
    size, queries = len(response.content) / 1000, len(big.captured_queries)
    print(f'\nconfidence, GD-Big ({body["filled"]} values): {best * 1000:.0f} ms, {size:.1f} kB, {queries} queries')
    assert response.status_code == 200 and best <= 0.3
    assert len(big.captured_queries) == len(few.captured_queries)
