"""Q.3 #8 for the request (K.6 tests: "two concurrent toggles both survive, also as the first writes on a new deal"):
the old page sent the whole carrier list from stale props and merged without a lock (K.5 #1, #2)."""

import threading
import time
from unittest import mock

import pytest
from django.db import connection

from conftest import make_deal
from rfp import services
from rfp.models import RfpRequest

pytestmark = pytest.mark.django_db(transaction=True)


def _race(user, deal, changes):
    real = services._locked

    def slow(deal_id):
        found = real(deal_id)
        time.sleep(0.2)  # hold the locks between reading the request and writing it
        return found

    def click(change):
        try:
            services.update(user, deal.id, change)
        finally:
            connection.close()

    with mock.patch.object(services, '_locked', slow):
        threads = [threading.Thread(target=click, args=(change,)) for change in changes]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    return RfpRequest.objects.get(deal=deal)


def test_K25_Q3_two_carrier_clicks_on_a_new_deal_both_stay(user):
    deal = make_deal(user)
    row = _race(user, deal, [{'carriers': {'add': ['aetna']}}, {'carriers': {'add': ['unum']}}])
    assert row.carriers == ['aetna', 'unum']


def test_K25_Q3_a_chip_and_the_notes_at_once_both_stay(user):
    deal = make_deal(user)
    services.update(user, deal.id, {'carriers': {'add': ['cigna']}})
    row = _race(user, deal, [{'funding': {'remove': ['level_funded']}}, {'notes': 'Match the PPO.'}])
    assert (row.carriers, row.funding, row.notes) == (['cigna'], ['fully_insured'], 'Match the PPO.')
