"""The Perf lane for the shell and the Work queue (plan.md §12.1, Q.7; Q.9 row 61): the journey on GD-Big ≤100 ms, the
Work queue with 300 open deals ≤1 s; the client's Agenda on GD-Big's client ≤300 ms, Q.7's agenda-read budget (slice
68; its queries stay fixed at any size, test_client_agenda). `pytest -m perf agenda` (kept out of the Fast lane by
pytest.ini's addopts); run with `-s` to see the measured figures. The 300 deals are bulk-made as `create_client`
leaves them: synthetic names."""

import time

import pytest

from conftest import make_big_deal
from deals import lifecycle
from deals.models import Client, Deal

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


def test_Q7_the_journey_of_GD_Big_stays_within_100_ms(api, gd_big):
    took, response = timed(lambda: api.get(f'/api/deals/{gd_big.id}/journey/'))
    print(f'\njourney, GD-Big (600 plans): {took * 1000:.0f} ms')
    assert response.status_code == 200 and took <= 0.1


def test_Q9_68_the_client_agenda_of_GD_Big_stays_within_300_ms(api, gd_big):
    took, response = timed(lambda: api.get(f'/api/clients/{gd_big.client_id}/agenda/'))
    print(f'\nclient agenda, GD-Big (600 plans): {took * 1000:.0f} ms, {len(response.content) / 1000:.1f} kB')
    assert response.status_code == 200 and took <= 0.3


def test_Q7_the_work_queue_of_300_open_deals_stays_within_1_s(api, user):
    clients = Client.objects.bulk_create(
        Client(name=f'Perf Group {n} (synthetic)', relationship=lifecycle.PROSPECT, owner=user, created_by=user)
        for n in range(300)
    )
    Deal.objects.bulk_create(
        Deal(client=client, opened_as=lifecycle.PROSPECT, owner=user, created_by=user, requested_lines=['medical'])
        for client in clients
    )
    for n in range(5):
        make_big_deal(user, plans=24, name=f'Perf Busy {n} (synthetic)')
    took, response = timed(lambda: api.get('/api/work-queue/'))
    print(f'\nwork queue, 305 open deals: {took:.2f} s, {len(response.content) / 1000:.0f} kB')
    assert response.status_code == 200 and len(response.json()['rows']) >= 300 and took <= 1.0
