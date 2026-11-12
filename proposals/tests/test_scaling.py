"""Query scaling of the Proposal tab (plan.md §12.2, Q.3 #4): one `deal_state` read, the same queries at 10 plans and
at GD-Big's 600. Two sizes compared, never a pinned number."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import make_big_deal

pytestmark = pytest.mark.django_db


def queries(api, deal):
    api.get(f'/api/deals/{deal.id}/proposal/')  # the first GET still creates the config row (until slice 25)
    with CaptureQueriesContext(connection) as captured:
        assert api.get(f'/api/deals/{deal.id}/proposal/').status_code == 200
    return len(captured.captured_queries)


def test_Q3_4_the_proposal_runs_the_same_queries_at_10_and_600_plans(api, user, gd_big):
    assert queries(api, make_big_deal(user, 10)) == queries(api, gd_big)
