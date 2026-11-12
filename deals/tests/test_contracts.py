"""The Q.3 contracts for deals: the write path, GETs that write nothing and the permission matrix (plan.md §12.3)."""

from decimal import Decimal

import pytest

from conftest import check_permissions, make_deal, sweep_gets
from contract_helpers import assert_write_path
from deals import services
from deals.models import Activity


@pytest.fixture
def world(user):
    deal = make_deal(user)
    services.update_deal(user, deal.id, stage='quoting')
    row = Activity.objects.filter(deal=deal).latest('id')
    note = services.add_note(user, deal.id, body='A note to edit')
    contact = services.create_contact(user, deal.client_id, name='Rae Example')
    return {'deal': deal, 'client': deal.client, 'row': row, 'note': note, 'contact': contact}


def samples(world):
    deal, client, row = world['deal'], world['client'], world['row']
    return {
        'api/clients/<int:pk>/': {'pk': client.id},
        'api/clients/<int:pk>/status/': {'pk': client.id},
        'api/clients/<int:pk>/archive/': {'pk': client.id},
        'api/clients/<int:pk>/contacts/': {'pk': client.id},
        'api/contacts/<int:pk>/': {'pk': world['contact'].id},
        'api/deals/<int:pk>/': {'pk': deal.id},
        'api/deals/<int:pk>/lost/': {'pk': deal.id},
        'api/deals/<int:pk>/reopen/': {'pk': deal.id},
        'api/deals/<int:pk>/notes/': {'pk': deal.id},
        'api/notes/<int:pk>/': {'pk': world['note'].id},
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
    ('DELETE', 'api/clients/<int:pk>/', {**ALL, 'producer': 405, 'admin': 405}),  # archived, never deleted (M104)
    ('POST', 'api/clients/<int:pk>/archive/', ALL, {'archived': False}),
    ('GET', 'api/archived/', ALL),
    ('GET', 'api/clients/<int:pk>/contacts/', ALL),
    ('POST', 'api/clients/<int:pk>/contacts/', {**ALL, 'producer': 201, 'admin': 201}, {'name': 'Second'}),
    ('PATCH', 'api/contacts/<int:pk>/', ALL, {'title': 'HR lead'}),
    ('DELETE', 'api/contacts/<int:pk>/', {**ALL, 'producer': 204, 'admin': 204}),
    ('GET', 'api/deals/<int:pk>/', ALL),
    ('PATCH', 'api/deals/<int:pk>/', ALL, {'stage': 'proposal'}),
    ('POST', 'api/deals/<int:pk>/lost/', ALL, {'reason': 'Went elsewhere'}),
    ('POST', 'api/deals/<int:pk>/reopen/', ALL),
    ('GET', 'api/deals/<int:pk>/notes/', ALL),
    ('POST', 'api/deals/<int:pk>/notes/', {**ALL, 'producer': 201, 'admin': 201}, {'body': 'Called the HR lead'}),
    ('PATCH', 'api/notes/<int:pk>/', ALL, {'pinned': True}),  # the producer is its author; an admin may too
    ('DELETE', 'api/notes/<int:pk>/', ALL),  # {activity_id}: the Undo's row
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


# Each changing service call of deals, with the row it changes; the reverting ones also pass the whole contract in
# their own tests (test_archive, test_notes, test_facts; contacts keep keys only, test_contacts).
WRITES = {
    'deal stage': ('deal', lambda user, w: services.update_deal(user, w['deal'].id, stage='proposal')),
    'deal size': ('deal', lambda user, w: services.update_deal(user, w['deal'].id, deal_size=Decimal('9000'))),
    'deal owner': ('deal', lambda user, w: services.set_owner(user, None, deal_id=w['deal'].id)),
    'client notes': ('client', lambda user, w: services.update_client(user, w['client'].id, notes='Brief')),
    'client status': ('client', lambda user, w: services.set_status(user, w['client'].id, 'new_client')),
    'client archive': ('client', lambda user, w: services.set_archived(user, w['client'].id, True)),
    'note pin': ('note', lambda user, w: services.update_note(user, w['note'].id, pinned=True)),
}


@pytest.mark.parametrize('target, write', WRITES.values(), ids=WRITES.keys())
def test_Q3_deals_write_path(user, world, target, write):
    assert_write_path(lambda: write(user, world), world[target])


def test_Q3_mark_lost_twice_is_refused_and_changes_nothing(user, world):
    assert_write_path(lambda: _lost_once(user, world['deal'].id), world['deal'])


def _lost_once(user, deal_id):
    from deals import activity

    try:
        services.mark_lost(user, deal_id, 'Went elsewhere')
    except activity.Refused:
        pass  # the second call: 409, nothing written (M3)


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
