"""Q.3 #8 for the client-level writes of slice 38: two people marking different contacts primary at once leave exactly
one primary (the Client row serializes them), and an edit beside an archive both survive."""

import threading

import pytest
from django.db import close_old_connections

from conftest import make_deal
from deals import services
from deals.models import Client, Contact

pytestmark = pytest.mark.django_db(transaction=True)


def _together(*calls):
    barrier = threading.Barrier(len(calls))
    errors = []

    def run(call):
        try:
            barrier.wait(timeout=5)
            call()
        except Exception as exc:  # noqa: BLE001 (reported below)
            errors.append(exc)
        finally:
            close_old_connections()

    threads = [threading.Thread(target=run, args=(call,)) for call in calls]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return errors


def test_Q3_8_M30_two_primaries_at_once_leave_one(user):
    deal = make_deal(user, requested_lines=())
    first = services.create_contact(user, deal.client_id, name='One')
    second = services.create_contact(user, deal.client_id, name='Two', role='benefit_admin')
    errors = _together(
        lambda: services.update_contact(user, first.id, is_primary=True),
        lambda: services.update_contact(user, second.id, is_primary=True),
    )
    assert errors == []
    assert Contact.objects.filter(client_id=deal.client_id, is_primary=True).count() == 1


def test_Q3_8_A18_a_rename_beside_an_archive_both_survive(user):
    deal = make_deal(user, requested_lines=())
    errors = _together(
        lambda: services.set_archived(user, deal.client_id, True),
        lambda: services.update_client(user, deal.client_id, name='Renamed Co.'),
    )
    assert errors == []
    client = Client.objects.get(pk=deal.client_id)
    assert client.name == 'Renamed Co.' and client.archived_at is not None
