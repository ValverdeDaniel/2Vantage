"""Q.3 #8 for the link services (B14: almost no old link write locked a row): two people acting on one request at
once, each in their own transaction, both survive, and closing the request beside a link action never deadlocks."""

import threading
import time
from unittest import mock

import pytest
from django.db import connection

from review import services
from review.models import ClientLink, ClientRequest
from review.services import common

pytestmark = pytest.mark.django_db(transaction=True)


def _race(calls):
    real = common.locked_request

    def slow(request_id):
        found = real(request_id)
        time.sleep(0.2)  # hold the Deal's and the request's locks before the write
        return found

    errors = []

    def run(call):
        try:
            call()
        except Exception as exc:  # noqa: BLE001 (reported below)
            errors.append(exc)
        finally:
            connection.close()

    with mock.patch.object(common, 'locked_request', slow):
        threads = [threading.Thread(target=run, args=(call,)) for call in calls]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert errors == []


def test_L8_Q3_8_copying_one_link_and_turning_off_its_sibling_both_stay(user, deal):
    made = services.create(
        user, deal.id, {'asks': {'intake': {'scope': 'all'}}, 'people': [{'name': 'A'}, {'name': 'B'}]}
    )
    first, second = (link for link, _path, _pin in made.links)
    _race([lambda: services.mark_sent(user, first.id, copied=True), lambda: services.revoke(user, second.id)])
    assert ClientLink.objects.get(pk=first.id).sent_at is not None
    assert ClientLink.objects.get(pk=second.id).revoked_at is not None


def test_L70_Q3_8_closing_beside_turning_a_link_off_never_deadlocks(user, deal):
    made = services.create(user, deal.id, {'asks': {'intake': {'scope': 'all'}}, 'people': [{'name': 'A'}]})
    link = made.links[0][0]
    _race([lambda: services.close(user, made.request.id, 'cancelled'), lambda: services.revoke(user, link.id)])
    assert ClientRequest.objects.get(pk=made.request.id).closed_at is not None
    assert ClientLink.objects.get(pk=link.id).revoked_at is not None


def test_L51_B7_Q3_8_two_asks_for_one_item_at_once_leave_one_draft(user, deal):
    from review.models import ReviewNote
    from review.services import tray

    real = tray.locked_deal

    def slow(deal_id):
        found = real(deal_id)
        time.sleep(0.2)  # hold the Deal's lock before reading the drafts
        return found

    errors = []

    def run():
        try:
            tray.ask(user, deal.id, ['intake:fein'])
        except Exception as exc:  # noqa: BLE001 (reported below)
            errors.append(exc)
        finally:
            connection.close()

    with mock.patch.object(tray, 'locked_deal', slow):
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert errors == []
    assert ReviewNote.objects.filter(deal=deal, key='fein', sent_at__isnull=True).count() == 1
