"""Q.3 #8 for the intent door: two gestures on different lines at once both survive. The lines to quote are one JSON
list on the Deal, so a writer that read it unlocked would drop the other's line (the old app's three writers)."""

import threading
import time
from unittest import mock

import pytest
from django.db import connection

from conftest import make_deal
from deals.models import Deal
from intake.services import intent, rows

pytestmark = pytest.mark.django_db(transaction=True)


def test_B17_Q3_two_lines_shopped_at_once_both_stay(user):
    deal = make_deal(user, requested_lines=())
    real = rows.lock_coverage

    def slow(deal_id, ids=None):
        found = real(deal_id, ids)
        time.sleep(0.2)  # hold the Deal between reading the lines and writing them
        return found

    def shop(line):
        try:
            intent.set_intent(user, deal.id, line=line, shop=True)
        finally:
            connection.close()

    with mock.patch.object(rows, 'lock_coverage', slow):
        threads = [threading.Thread(target=shop, args=(line,)) for line in ('dental', 'medical')]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert Deal.objects.get(pk=deal.pk).requested_lines == ['medical', 'dental']
