"""The Q.3 contracts for proposals (plan.md §12.3): GETs that write nothing (the builder's GET no longer makes the
config row, J.5 B27), the permission matrix and query scaling for the page split (slice 14) and the builder
(slice 25)."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import check_permissions, make_big_deal, make_deal, sweep_gets
from proposals import template_services
from proposals.issues import start as issuing
from proposals.tests import firm_shop
from proposals.tests.test_issue_job import ready_deal
from quotes import services
from quotes.models import Plan


@pytest.fixture
def world(user):
    deal = make_deal(user)
    current = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='Today')
    services.create_plan(
        user, deal, line='medical', role='alternate', carrier='Cigna', name='Quote', replaces_ids=[current.id]
    )
    issued, _quote = ready_deal(user, name='Issued (synthetic)')  # slice 32: v1 issued, for its stored files
    issuing.issue(user, issued)
    # slice 34: an uploaded cover, a team member with a photo and a shared template (firm rows, no deal)
    found = {'cover': firm_shop.cover(user), 'person': firm_shop.person(user)}
    found['template'] = template_services.create(user, {'name': 'Ours', 'kind': 'summary', 'shared': True})
    return {'deal': deal, 'issued': issued, **found}


def samples(world):
    deal = world['deal']
    return {
        'api/deals/<int:pk>/proposal/': {'pk': deal.id},
        'api/deals/<int:pk>/proposal/marks/': {'pk': deal.id},
        'api/deals/<int:pk>/proposal/pages/': {'pk': deal.id, 'query': {'line': 'medical', 'preset': 'all'}},
        'api/deals/<int:pk>/proposal/files/pdf/': {'pk': deal.id},
        'api/deals/<int:pk>/proposal/files/pptx/': {'pk': deal.id},
        'api/deals/<int:pk>/proposal/files/letter/': {'pk': deal.id},
        'api/deals/<int:pk>/proposal/files/xlsx/': {'pk': deal.id},
        'api/deals/<int:pk>/proposal/preview/': {'pk': deal.id, 'query': {'file': 'workbook'}},
        # slice 36: no stop-loss plan here, so the workbook refuses past the permission check (the 200: its own tests)
        'api/deals/<int:pk>/plans/stop-loss/workbook/': {'pk': deal.id, 'expect': 409},
        # slice 32: Issue (refused on `deal`: no recommendation), the issued list and v1's stored files
        'api/deals/<int:pk>/proposal/issue/': {'pk': deal.id},
        'api/deals/<int:pk>/proposal/issues/': {'pk': world['issued'].id},
        'api/deals/<int:pk>/proposal/issues/<int:version>/retry/': {'pk': world['issued'].id, 'version': 1},
        **{
            f'api/deals/<int:pk>/proposal/issues/<int:version>/{file}/': {'pk': world['issued'].id, 'version': 1}
            for file in ('pdf', 'pptx', 'xlsx', 'letter', 'packet')
        },
        # slice 34: the firm's covers, pictures, pages, team and templates
        'api/proposal/cover-images/<int:image_id>/': {'image_id': world['cover'].id},
        'api/proposal/cover-images/<int:image_id>/thumb/': {'image_id': world['cover'].id},
        'api/proposal/pictures/<str:key>/thumb/': {'key': 'blue_light'},
        'api/proposal/team/<int:member_id>/': {'member_id': world['person'].id},
        'api/proposal/team/<int:member_id>/photo/': {'member_id': world['person'].id},
        'api/proposal/templates/': {'query': {'kind': 'layout'}},
        'api/proposal/templates/<int:template_id>/': {'template_id': world['template'].id},
    }


ALL = {'signed_out': 401, 'producer': 200, 'admin': 200}
MADE = {'signed_out': 401, 'producer': 201, 'admin': 201}
GONE = {'signed_out': 401, 'producer': 204, 'admin': 204}
BAD = {'signed_out': 401, 'producer': 400, 'admin': 400}
MATRIX = [
    ('GET', 'api/deals/<int:pk>/proposal/', ALL),
    ('PATCH', 'api/deals/<int:pk>/proposal/', ALL, {'title': 'Plan comparison'}),
    ('POST', 'api/deals/<int:pk>/proposal/marks/', ALL, {'card': 'quotes', 'line': 'medical', 'done': True}),
    ('GET', 'api/deals/<int:pk>/proposal/pages/', ALL),
    ('GET', 'api/deals/<int:pk>/proposal/files/pdf/', ALL),
    ('GET', 'api/deals/<int:pk>/proposal/files/pptx/', ALL),
    ('GET', 'api/deals/<int:pk>/proposal/files/letter/', ALL),
    ('GET', 'api/deals/<int:pk>/proposal/files/xlsx/', ALL),
    ('GET', 'api/deals/<int:pk>/proposal/preview/', ALL),
    ('GET', 'api/deals/<int:pk>/plans/stop-loss/workbook/', {'signed_out': 401, 'producer': 409, 'admin': 409}),
    # slice 32: Issue refuses an uncovered line (409); Retry refuses an issued version (409)
    ('POST', 'api/deals/<int:pk>/proposal/issue/', {'signed_out': 401, 'producer': 409, 'admin': 409}),
    ('GET', 'api/deals/<int:pk>/proposal/issues/', ALL),
    (
        'POST',
        'api/deals/<int:pk>/proposal/issues/<int:version>/retry/',
        {'signed_out': 401, 'producer': 409, 'admin': 409},
    ),
    *[
        ('GET', f'api/deals/<int:pk>/proposal/issues/<int:version>/{file}/', ALL)
        for file in ('pdf', 'pptx', 'xlsx', 'letter', 'packet')
    ],
    # slice 34: firm rows, open to every user (a file-less upload is a 400; the template is the producer's, shared)
    ('GET', 'api/proposal/covers/', ALL),
    ('GET', 'api/proposal/cover-images/', ALL),
    ('POST', 'api/proposal/cover-images/', BAD, {'label': 'No file'}),
    ('DELETE', 'api/proposal/cover-images/<int:image_id>/', GONE),
    ('GET', 'api/proposal/cover-images/<int:image_id>/thumb/', ALL),
    ('GET', 'api/proposal/pictures/<str:key>/thumb/', ALL),
    ('GET', 'api/proposal/firm-pages/', ALL),
    ('PATCH', 'api/proposal/firm-pages/', ALL, {'about_text': 'Brokers since 1990.'}),
    ('GET', 'api/proposal/team/', ALL),
    ('POST', 'api/proposal/team/', MADE, {'name': 'Lee Park (synthetic)'}),
    ('PATCH', 'api/proposal/team/<int:member_id>/', ALL, {'title': 'Account manager'}),
    ('DELETE', 'api/proposal/team/<int:member_id>/', GONE),
    ('GET', 'api/proposal/team/<int:member_id>/photo/', ALL),
    ('POST', 'api/proposal/team/<int:member_id>/photo/', BAD),
    ('DELETE', 'api/proposal/team/<int:member_id>/photo/', ALL),
    ('GET', 'api/proposal/templates/', ALL),
    ('POST', 'api/proposal/templates/', MADE, {'name': 'Short summary', 'kind': 'summary', 'config': {}}),
    ('PATCH', 'api/proposal/templates/<int:template_id>/', ALL, {'description': 'For renewals'}),
    ('DELETE', 'api/proposal/templates/<int:template_id>/', GONE),
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
