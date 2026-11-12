"""Q.3 #8 for the agreed rates (H.6 "Concurrency": concurrent edits to two lines' rates both survive; bug 17, the old
PATCH sent the whole map), also as the first writes on a deal with no Commission row yet."""

import threading
import time
from unittest import mock

import pytest
from django.db import connection

from commission.models import Commission
from commission.services import rates
from conftest import make_deal

pytestmark = pytest.mark.django_db(transaction=True)


def _race(user, deal, changes):
    real = rates.commission_row

    def slow(found_deal):
        row = real(found_deal)
        time.sleep(0.2)  # hold the locks between reading the row and writing it
        return row

    def edit(change):
        try:
            rates.update(user, deal.id, change)
        finally:
            connection.close()

    with mock.patch.object(rates, 'commission_row', slow):
        threads = [threading.Thread(target=edit, args=(change,)) for change in changes]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    return Commission.objects.get(deal=deal)


def test_H5_Q3_two_lines_rates_at_once_on_a_new_deal_both_stay(user):
    deal = make_deal(user)
    row = _race(user, deal, [{'rates': {'medical': '5'}}, {'rates': {'dental': '15'}}])
    assert row.rates == {'medical': {'type': 'pct', 'value': '5'}, 'dental': {'type': 'pct', 'value': '15'}}


def test_H5_Q3_a_rate_and_the_year_at_once_both_stay(user):
    deal = make_deal(user)
    rates.update(user, deal.id, {'rates': {'vision': '8'}})
    row = _race(user, deal, [{'rates': {'medical': '5'}}, {'year_number': 2}])
    assert set(row.rates) == {'vision', 'medical'} and row.year_number == 2
