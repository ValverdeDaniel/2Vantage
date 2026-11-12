"""Q.3 #8 for the census apply: two imports applied at once on one deal queue on the Deal's lock — neither deadlocks,
the second one matches the people the first wrote (nobody is created twice), and the stored counts equal a rebuild."""

import threading
import time
from unittest import mock

import pytest
from django.db import connection

from census import facts, services
from census.models import CensusImport, Member
from census.services import rows as census_rows
from conftest import make_deal

from .helpers import family, import_file, roster, upload, xlsx

pytestmark = pytest.mark.django_db(transaction=True)


def test_C17_Q3_two_applies_at_once_queue_and_match(user):
    deal = make_deal(user, requested_lines=('medical',))
    smith = family('E1', 'Smith', tier='ES', deps=[('Spouse', 'Blake', '02/02/1981')])
    lee = family('E3', 'Lee', first='Robin')
    first = import_file(user, deal, xlsx(roster(smith)))
    second = CensusImport.objects.create(
        deal=deal,
        document=upload(user, deal, xlsx(roster(smith, lee))),
        sheet_name=first.sheet_name,
        header_row=1,
        first_data_row=2,
        headers=first.headers,
        mapping=first.mapping,
    )
    real = census_rows.lock_members
    failures = []

    def slow(deal_id):
        found = real(deal_id)
        time.sleep(0.2)  # hold the locks while the other apply waits
        return found

    def run(import_id):
        try:
            services.apply_import(user, import_id)
        except Exception as error:  # noqa: BLE001 - a deadlock or a refusal fails the test below
            failures.append(repr(error))
        finally:
            connection.close()

    with mock.patch.object(census_rows, 'lock_members', slow):
        threads = [threading.Thread(target=run, args=(imp.id,)) for imp in (first, second)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert failures == []
    for first_name in ('Avery', 'Blake'):  # whichever ran first, Smith and Blake exist once
        assert Member.all_objects.filter(deal=deal, values__first_name=first_name).count() == 1
    assert facts.differences(deal.id) == {}


def test_Q3_8_two_hand_edits_on_two_people_at_once_both_survive(user):
    deal = make_deal(user, requested_lines=('medical',))
    first = import_file(user, deal, xlsx(roster(family('E1', 'Smith'), family('E3', 'Lee', first='Robin'))))
    services.apply_import(user, first.id)
    avery, robin = (
        Member.objects.get(deal=deal, values__first_name='Avery'),
        Member.objects.get(deal=deal, values__first_name='Robin'),
    )
    failures = []
    start = threading.Barrier(2)

    def run(member_id, values):
        try:
            start.wait()
            services.edit_values(user, member_id, values)
        except Exception as error:  # noqa: BLE001 - a deadlock or a lost write fails the test below
            failures.append(repr(error))
        finally:
            connection.close()

    threads = [
        threading.Thread(target=run, args=(avery.id, {'zip': '02139'})),
        threading.Thread(target=run, args=(robin.id, {'hours_per_week': '20'})),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert failures == []
    avery.refresh_from_db()
    robin.refresh_from_db()
    assert (avery.values['zip'], robin.values['hours_per_week']) == ('02139', '20')
    assert facts.differences(deal.id) == {}
