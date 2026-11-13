"""The Q.3 contracts for overview (plan.md §12.3): its GETs write nothing, the permission matrix, ids past bigint, and
the deal's read and the client's (slice 67; Q.9 row 67) run the same queries for a deal of 10 plans and one of 60
(Q.3 #4; M.6 "a fixed number of queries")."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import check_permissions, make_big_deal, sweep_gets
from deals.services import add_note, create_contact

pytestmark = pytest.mark.django_db

BIG = 2**63


def samples(deal):
    return {
        'api/deals/<int:pk>/overview/': {'pk': deal.id},
        'api/deals/<int:pk>/overview/feed/': {'pk': deal.id},
        'api/clients/<int:pk>/overview/': {'pk': deal.client_id},
        'api/clients/<int:pk>/activity/': {'pk': deal.client_id},
    }


def test_Q3_2_overview_gets_write_nothing(api, user, deal):
    add_note(user, deal.id, body='Called HR (synthetic)', kind='call')
    create_contact(user, deal.client_id, name='Casey HR (synthetic)')
    sweep_gets(api, ['overview'], samples(deal))


def test_Q3_3_the_permission_matrix(actors, no_csrf_api, deal):
    matrix = [
        ('GET', 'api/deals/<int:pk>/overview/', {'signed_out': 401, 'producer': 200, 'admin': 200}),
        ('GET', 'api/deals/<int:pk>/overview/feed/', {'signed_out': 401, 'producer': 200, 'admin': 200}),
        ('GET', 'api/clients/<int:pk>/overview/', {'signed_out': 401, 'producer': 200, 'admin': 200}),
        ('GET', 'api/clients/<int:pk>/activity/', {'signed_out': 401, 'producer': 200, 'admin': 200}),
    ]
    check_permissions(actors, ['overview'], matrix, samples(deal), no_csrf_api)


@pytest.mark.parametrize(
    'path',
    [f'/api/deals/{BIG}/overview/', '/api/deals/999999/overview/', f'/api/deals/{BIG}/overview/feed/',
     '/api/deals/999999/overview/feed/', f'/api/clients/{BIG}/overview/', '/api/clients/999999/overview/',
     f'/api/clients/{BIG}/activity/', '/api/clients/999999/activity/'],
)  # fmt: skip
def test_Q3_ids_past_bigint_or_unknown_are_404_never_500(api, path):
    assert api.get(path).status_code == 404


def test_Q3_4_the_overview_reads_in_the_same_queries_at_10_and_60_plans(api, user):
    small, big = make_big_deal(user, plans=10, name='Small (synthetic)'), make_big_deal(user, plans=60, name='Big')

    def queries(deal):
        with CaptureQueriesContext(connection) as found:
            assert api.get(f'/api/deals/{deal.id}/overview/').status_code == 200
        return len(found.captured_queries)

    assert queries(small) == queries(big)


def test_Q9_67_the_client_overview_reads_in_the_same_queries_at_10_and_60_plans(api, user):
    small, big = make_big_deal(user, plans=10, name='Small (synthetic)'), make_big_deal(user, plans=60, name='Big')

    def queries(deal):
        with CaptureQueriesContext(connection) as found:
            assert api.get(f'/api/clients/{deal.client_id}/overview/').status_code == 200
        return len(found.captured_queries)

    assert queries(small) == queries(big)
