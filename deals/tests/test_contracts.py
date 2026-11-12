"""The Q.3 contracts for deals: the write path, GETs that write nothing and the permission matrix (plan.md §12.3)."""

import pytest

from conftest import check_permissions, make_deal, sweep_gets
from contract_helpers import assert_write_path
from deals import services
from deals.models import Activity


@pytest.fixture
def world(user):
    deal = make_deal(user)
    services.update_deal(user, deal.id, stage='quoting')
    return {'deal': deal, 'client': deal.client, 'row': Activity.objects.filter(deal=deal).latest('id')}


def samples(world):
    deal, client, row = world['deal'], world['client'], world['row']
    return {
        'api/clients/<int:pk>/': {'pk': client.id},
        'api/clients/<int:pk>/status/': {'pk': client.id},
        'api/deals/<int:pk>/': {'pk': deal.id},
        'api/deals/<int:pk>/lost/': {'pk': deal.id},
        'api/deals/<int:pk>/reopen/': {'pk': deal.id},
        'api/deals/<int:pk>/activity/': {'pk': deal.id},
        'api/activity/<int:pk>/revert/': {'pk': row.id},
        'api/agency/logo/': {'expect': 404},  # no logo uploaded
    }


ALL = {'signed_out': 401, 'producer': 200, 'admin': 200}
MATRIX = [
    ('GET', 'api/clients/', ALL),
    ('POST', 'api/clients/', {**ALL, 'producer': 201, 'admin': 201}, {'name': 'Second Co.'}),
    ('GET', 'api/clients/<int:pk>/', ALL),
    ('PATCH', 'api/clients/<int:pk>/', ALL, {'notes': 'Standing brief'}),
    ('POST', 'api/clients/<int:pk>/status/', ALL, {'to': 'new_client'}),
    ('DELETE', 'api/clients/<int:pk>/', {'signed_out': 401, 'producer': 403, 'admin': 204}),
    ('GET', 'api/deals/<int:pk>/', ALL),
    ('PATCH', 'api/deals/<int:pk>/', ALL, {'stage': 'proposal'}),
    ('POST', 'api/deals/<int:pk>/lost/', ALL, {'reason': 'Went elsewhere'}),
    ('POST', 'api/deals/<int:pk>/reopen/', ALL),
    ('GET', 'api/deals/<int:pk>/activity/', ALL),
    # The sample row is a stage move, which deals cannot revert yet: 409 with its sentence, past the permission check.
    ('POST', 'api/activity/<int:pk>/revert/', {**ALL, 'producer': 409, 'admin': 409}),
    ('GET', 'api/users/', ALL),
    ('GET', 'api/agency/', ALL),
    ('GET', 'api/agency/logo/', {**ALL, 'producer': 404, 'admin': 404}),
]


def test_Q3_deals_gets_write_nothing(admin_api, world):
    sweep_gets(admin_api, ('deals',), samples(world))


def test_Q3_deals_permission_matrix(actors, no_csrf_api, world):
    check_permissions(actors, ('deals',), MATRIX, samples(world), no_csrf_api)


# Each changing service call of deals, with the row it changes. mark_lost is left out until slice 38: today it
# re-stamps a lost deal (M.5 B33), so the same call twice is not yet a no-op.
WRITES = {
    'deal stage': ('deal', lambda user, deal: services.update_deal(user, deal.id, stage='proposal')),
    'client notes': ('client', lambda user, deal: services.update_client(user, deal.client_id, notes='Brief')),
    'client status': ('client', lambda user, deal: services.set_status(user, deal.client_id, 'new_client')),
}


@pytest.mark.parametrize('target, write', WRITES.values(), ids=WRITES.keys())
def test_Q3_deals_write_path(user, world, target, write):
    assert_write_path(lambda: write(user, world['deal']), world[target])


def test_Q3_the_helpers_fail_on_a_route_with_no_sample_or_no_matrix_row(admin_api, actors, no_csrf_api, world):
    with pytest.raises(AssertionError, match='api/deals/<int:pk>/: no sample arguments'):
        sweep_gets(admin_api, ('deals',), {})
    with pytest.raises(AssertionError, match='GET api/users/: no row in the permission matrix'):
        check_permissions(
            actors, ('deals',), [row for row in MATRIX if row[1] != 'api/users/'], samples(world), no_csrf_api
        )


def test_Q3_the_sweep_fails_on_a_get_that_writes(admin_api, world, monkeypatch):
    from deals import selectors

    def writing_agency():
        services.update_client(None, world['client'].id, notes='Written by a GET')
        return {}

    monkeypatch.setattr(selectors, 'agency', writing_agency)
    with pytest.raises(AssertionError, match='GET /api/agency/ wrote: UPDATE "deals_client"'):
        sweep_gets(admin_api, ('deals',), samples(world))
