"""The Perf lane for "What the client will see" (plan.md §12.1, Q.7; slice 14): GD-Big's 600 medical plans, as built
(starred) and with nothing starred, when every plan prints and the pages hold all 600. Q.7's comparison budget applies
(3 MB raw, 2.5 s). `pytest -m perf proposals -s` prints the figures."""

import time

import pytest

from quotes.models import Plan

pytestmark = [pytest.mark.perf, pytest.mark.django_db]

MB = 1_000_000


def pages(api, deal):
    best, response = None, None
    for _ in range(3):  # the best of three: a cold first run measures the machine, not the read
        start = time.perf_counter()
        response = api.get(f'/api/deals/{deal.id}/proposal/pages/', {'line': 'medical', 'preset': 'all'})
        took = time.perf_counter() - start
        best = took if best is None else min(best, took)
    assert response.status_code == 200
    return best, response


@pytest.mark.parametrize('nothing_starred', [False, True])
def test_Q7_F37_pages_of_600_plans_stay_within_3_MB_and_2_5_s(api, gd_big, nothing_starred):
    if nothing_starred:  # rolled back with the test
        Plan.objects.filter(deal=gd_big).update(starred=False, recommended=False)
    took, response = pages(api, gd_big)
    body = response.json()
    print(f'\npages, 600 plans, nothing starred {nothing_starred}: {len(response.content) / MB:.2f} MB, {took:.2f} s')
    assert len(body['plans']) + len(body['others']) == 600
    assert len(response.content) <= 3 * MB and took <= 2.5
