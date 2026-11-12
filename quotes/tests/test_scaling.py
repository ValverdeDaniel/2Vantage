"""Query scaling (plan.md §12.2, Q.3 #4): the Advisor's reads and `deal_state` (one grouped read) run the same
queries at 10 plans and at GD-Big's 600. Two sizes compared, never a pinned number."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import make_big_deal
from quotes.selectors import deal_state

pytestmark = pytest.mark.django_db

READS = ['plans/?line=medical', 'plans/lines/', 'plans/packages/?line=medical', 'plans/find/', 'plans/sources/']


def queries(call):
    with CaptureQueriesContext(connection) as captured:
        call()
    return len(captured.captured_queries)


def get(api, deal, path):
    def call():
        response = api.get(f'/api/deals/{deal.id}/{path}')
        assert response.status_code == 200

    return call


def test_Q3_4_advisor_reads_run_the_same_queries_at_10_and_600_plans(api, user, gd_big):
    small = make_big_deal(user, 10)
    for path in READS:
        assert queries(get(api, small, path)) == queries(get(api, gd_big, path)), path
    assert queries(lambda: deal_state(small)) == queries(lambda: deal_state(gd_big)), 'deal_state'
