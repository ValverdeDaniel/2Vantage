"""The read's batch scope (`deals/batch.py`; plan.md §5.10, Q.3 #4; slice 61): inside a scope a per-deal read is made
once for every deal the scope holds; outside one, or for a deal it does not hold, each call reads its own deal; a scope
over deals an open scope holds reuses it. Factory deals; synthetic names only."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import make_deal
from deals import batch
from deals.models import AgencySettings

pytestmark = pytest.mark.django_db


def counting(calls):
    def load(ids):
        calls.append(sorted(ids))
        return {deal_id: f'value of {deal_id}' for deal_id in ids}

    return load


def test_Q3_4_a_scope_reads_each_per_deal_fact_once_for_all_its_deals():
    calls = []
    load = counting(calls)
    with batch.scope([3, 1, 2]):
        assert batch.per_deal('demo', 1, load) == 'value of 1'
        assert batch.per_deal('demo', 2, load) == 'value of 2'
        assert batch.per_deal('demo', 9, load) == 'value of 9'  # not held: read on its own
    assert calls == [[1, 2, 3], [9]]
    assert batch.per_deal('demo', 1, load) == 'value of 1'  # outside: one deal at a time
    assert calls[-1] == [1]


def test_Q3_4_a_scope_inside_one_that_holds_its_deals_reuses_it():
    calls = []
    load = counting(calls)
    with batch.scope([1, 2, 3]) as outer:
        with batch.scope([2, 3]) as inner:
            assert inner is outer
            batch.per_deal('demo', 2, load)
        batch.per_deal('demo', 3, load)
    assert calls == [[1, 2, 3]]


def test_Q3_4_memo_works_a_value_out_once_per_deal_in_a_scope():
    worked = []

    def compute():
        worked.append(1)
        return {'figures': 3}

    with batch.scope([7]):
        assert batch.memo('demo', 7, compute) is batch.memo('demo', 7, compute)
    batch.memo('demo', 7, compute)
    assert len(worked) == 2


def test_Q3_4_the_deals_and_the_agency_are_read_once_in_a_scope(user):
    deals = [make_deal(user, name=f'Batch {n} (synthetic)') for n in range(3)]

    def reads(ids):
        with batch.scope(ids), CaptureQueriesContext(connection) as found:
            names = [batch.deal(deal_id).client.name for deal_id in ids]
            AgencySettings.get()
            AgencySettings.get()
        return names, len(found.captured_queries)

    names, many = reads([deal.id for deal in deals])
    assert names == [f'Batch {n} (synthetic)' for n in range(3)]
    assert reads([deals[0].id])[1] == many
    assert batch.deal(10**9) is None
    copy = batch.deal(deals[0].id)
    copy.stage = 'quoting'
    assert batch.deal(deals[0].id).stage == 'intake'  # each caller gets its own copy
