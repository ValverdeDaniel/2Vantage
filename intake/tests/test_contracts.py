"""The Q.3 contracts for intake (plan.md §12.3): the write path, GETs write nothing, the permission matrix."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import check_permissions, sweep_gets, write_path_contract
from intake import services
from intake.models import CurrentCoverage, Intake

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(user, deal):
    row = services.create_coverage(user, deal.id, {'line': 'medical', 'carrier': 'Aetna'}).row
    return {'deal': deal, 'row': row}


def samples(world):
    deal = {'pk': world['deal'].id}
    return {
        'api/deals/<int:pk>/intake/': deal,
        'api/deals/<int:pk>/intake/intent/': deal,
        'api/deals/<int:pk>/intake/intent/confirm/': deal,
        'api/deals/<int:pk>/intake/intent/reopen/': deal,
        'api/deals/<int:pk>/coverage/': deal,
        'api/coverage/<int:coverage_id>/': {'coverage_id': world['row'].id},
    }


ALL = {'signed_out': 401, 'producer': 200, 'admin': 200}
MADE = {**ALL, 'producer': 201, 'admin': 201}
GONE = {**ALL, 'producer': 204, 'admin': 204}
MATRIX = [
    ('GET', 'api/deals/<int:pk>/intake/', ALL),
    ('POST', 'api/deals/<int:pk>/intake/intent/', ALL, {'line': 'dental', 'has_today': True}),
    ('POST', 'api/deals/<int:pk>/intake/intent/confirm/', ALL),
    ('POST', 'api/deals/<int:pk>/intake/intent/reopen/', ALL),
    ('GET', 'api/deals/<int:pk>/coverage/', ALL),
    ('POST', 'api/deals/<int:pk>/coverage/', MADE, {'line': 'vision'}),
    ('PATCH', 'api/coverage/<int:coverage_id>/', ALL, {'notes': 'Renews in March'}),
    ('DELETE', 'api/coverage/<int:coverage_id>/', GONE),
]


def test_Q3_intake_gets_write_nothing(admin_api, world):
    sweep_gets(admin_api, ('intake',), samples(world))


def test_Q3_intake_permission_matrix(actors, no_csrf_api, world):
    check_permissions(actors, ('intake',), MATRIX, samples(world), no_csrf_api)


def test_Q3_ids_past_bigint_answer_404(api):
    assert api.get(f'/api/deals/{2**64}/intake/').status_code == 404
    assert api.patch(f'/api/coverage/{2**64}/', {}, format='json').status_code == 404


def test_Q3_coverage_edit_write_path(user, world):
    row = world['row']
    write_path_contract(
        user,
        row,
        lambda: services.update_coverage(user, row.id, {'carrier': 'Cigna', 'renewal_date': '2027-01-01'}),
        lambda r: (r.carrier, r.renewal_date),
        lambda: services.update_coverage(user, row.id, {'carrier': 'UnitedHealthcare'}),
    )


def test_Q3_set_intent_write_path(user, world):
    deal_id = world['deal'].id
    write_path_contract(
        user,
        world['row'],
        lambda: services.set_intent(user, deal_id, line='medical', this_year='off'),
        lambda r: (r.in_force, r.on_proposal),
        lambda: services.set_intent(user, deal_id, line='medical', this_year='market'),
    )


def test_Q3_confirmation_write_path(user, world):
    deal_id = world['deal'].id
    intake = Intake.objects.create(deal_id=deal_id)
    write_path_contract(
        user,
        intake,
        lambda: services.confirm_intent(user, deal_id),
        lambda r: r.intent_confirmed,
        lambda: services.reopen_intent(user, deal_id),
    )


def test_Q3_the_intent_door_locks_the_deal_first_then_the_rows(user, world):
    with CaptureQueriesContext(connection) as queries:
        services.set_intent(user, world['deal'].id, lines=['medical', 'dental'], has_today=True)
    locks = [q['sql'] for q in queries.captured_queries if 'FOR UPDATE' in q['sql']]
    assert '"deals_deal"' in locks[0]
    assert any(f'"{CurrentCoverage._meta.db_table}"' in sql for sql in locks[1:])


def test_Q3_the_intake_payload_reads_in_a_fixed_number_of_queries(api, user, deal):
    def queries():
        with CaptureQueriesContext(connection) as captured:
            assert api.get(f'/api/deals/{deal.id}/intake/').status_code == 200
        return len(captured.captured_queries)

    services.create_coverage(user, deal.id, {'line': 'medical'})
    one = queries()
    for line in ('dental', 'vision', 'basic_life_add', 'std', 'ltd', 'eap', 'hsa', 'fsa', 'pet'):
        services.create_coverage(user, deal.id, {'line': line, 'carrier': 'Carrier'})
    assert queries() == one
