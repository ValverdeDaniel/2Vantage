"""The Q.3 contracts for proposals (plan.md §12.3): GETs that write nothing (the builder's GET no longer makes the
config row, J.5 B27), the permission matrix and query scaling for the page split (slice 14) and the builder
(slice 25)."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import check_permissions, make_big_deal, make_deal, sweep_gets
from quotes import services
from quotes.models import Plan


@pytest.fixture
def world(user):
    deal = make_deal(user)
    current = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='Today')
    services.create_plan(
        user, deal, line='medical', role='alternate', carrier='Cigna', name='Quote', replaces_ids=[current.id]
    )
    return {'deal': deal}


def samples(world):
    deal = world['deal']
    return {
        'api/deals/<int:pk>/proposal/': {'pk': deal.id},
        'api/deals/<int:pk>/proposal/marks/': {'pk': deal.id},
        'api/deals/<int:pk>/proposal/pages/': {'pk': deal.id, 'query': {'line': 'medical', 'preset': 'all'}},
        'api/deals/<int:pk>/proposal/files/pdf/': {'pk': deal.id},
        'api/deals/<int:pk>/proposal/files/pptx/': {'pk': deal.id},
        'api/deals/<int:pk>/proposal/files/letter/': {'pk': deal.id},
        # slice 36: no stop-loss plan here, so the workbook refuses past the permission check (the 200: its own tests)
        'api/deals/<int:pk>/plans/stop-loss/workbook/': {'pk': deal.id, 'expect': 409},
        'api/deals/<int:pk>/proposal/files/xlsx/': {'pk': deal.id},
        'api/deals/<int:pk>/proposal/preview/': {'pk': deal.id, 'query': {'file': 'workbook'}},
    }


ALL = {'signed_out': 401, 'producer': 200, 'admin': 200}
MATRIX = [
    ('GET', 'api/deals/<int:pk>/proposal/', ALL),
    ('PATCH', 'api/deals/<int:pk>/proposal/', ALL, {'title': 'Plan comparison'}),
    ('POST', 'api/deals/<int:pk>/proposal/marks/', ALL, {'card': 'quotes', 'line': 'medical', 'done': True}),
    ('GET', 'api/deals/<int:pk>/proposal/pages/', ALL),
    ('GET', 'api/deals/<int:pk>/proposal/files/pdf/', ALL),
    ('GET', 'api/deals/<int:pk>/proposal/files/pptx/', ALL),
    ('GET', 'api/deals/<int:pk>/proposal/files/letter/', ALL),
    ('GET', 'api/deals/<int:pk>/plans/stop-loss/workbook/', {'signed_out': 401, 'producer': 409, 'admin': 409}),
    ('GET', 'api/deals/<int:pk>/proposal/files/xlsx/', ALL),
    ('GET', 'api/deals/<int:pk>/proposal/preview/', ALL),
]


def test_Q3_proposals_gets_write_nothing(admin_api, world):
    sweep_gets(admin_api, ('proposals',), samples(world))


def test_Q3_proposals_permission_matrix(actors, no_csrf_api, world):
    check_permissions(actors, ('proposals',), MATRIX, samples(world), no_csrf_api)


def _queries(api, deal, nothing_starred):
    if nothing_starred:  # every plan prints; GD-Big's shape comes starred
        Plan.objects.filter(deal=deal).update(starred=False, recommended=False)
    with CaptureQueriesContext(connection) as queries:
        response = api.get(f'/api/deals/{deal.id}/proposal/pages/', {'line': 'medical', 'preset': 'all'})
    assert response.status_code == 200
    return len(queries)


@pytest.mark.parametrize('nothing_starred', [False, True])
def test_Q3_4_F37_pages_read_the_same_queries_at_ten_and_two_hundred_plans(api, user, nothing_starred):
    small, big = make_big_deal(user, 10, name='Small (synthetic)'), make_big_deal(user, 200, name='Big (synthetic)')
    assert _queries(api, small, nothing_starred) == _queries(api, big, nothing_starred)


def _builder_queries(api, deal):
    with CaptureQueriesContext(connection) as queries:
        response = api.get(f'/api/deals/{deal.id}/proposal/')
    assert response.status_code == 200
    return len(queries)


def test_Q3_4_J17_the_builder_reads_the_same_queries_at_ten_and_two_hundred_plans(api, user):
    small, big = make_big_deal(user, 10, name='Small (synthetic)'), make_big_deal(user, 200, name='Big (synthetic)')
    assert _builder_queries(api, small) == _builder_queries(api, big)
