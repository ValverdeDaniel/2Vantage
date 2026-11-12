"""The Q.3 contracts for census (plan.md §12.3): GETs write nothing, the permission matrix, locks, key-only Activity
and stored counts equal to a rebuild after every service (Q.3 #9; `manage.py rebuild_facts`)."""

import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from census import facts, services
from census.models import CensusFacts, Member
from conftest import check_permissions, make_deal, sweep_gets
from intake import services as intake

from .helpers import family, import_file, imported, roster, upload, xlsx

pytestmark = pytest.mark.django_db

SMITH = family('E1', 'Smith', tier='ES', deps=[('Spouse', 'Blake', '02/02/1981')])
LEE = family('E3', 'Lee', first='Robin', tier='', plan='')


@pytest.fixture
def world(user):
    deal = make_deal(user, requested_lines=('medical',))
    imported(user, deal, xlsx(roster(SMITH)))
    waiting = import_file(user, deal, xlsx(roster(SMITH, LEE)))
    person = Member.objects.get(deal=deal, kind='employee')
    return {'deal': deal, 'import': waiting, 'file': upload(user, deal, xlsx(roster(LEE))), 'member': person}


def samples(world):
    deal, imp = {'pk': world['deal'].id}, {'import_id': world['import'].id}
    return {
        'api/deals/<int:pk>/census/': deal,
        'api/deals/<int:pk>/census/search/': deal,
        'api/deals/<int:pk>/census/imports/': deal,
        'api/census/imports/<int:import_id>/': imp,
        'api/census/imports/<int:import_id>/apply/': imp,
        'api/census/imports/<int:import_id>/discard/': imp,
        'api/deals/<int:pk>/census/members/': deal,
        'api/census/members/<int:member_id>/': {'member_id': world['member'].id},
        'api/census/members/<int:member_id>/source/': {'member_id': world['member'].id, 'query': {'key': 'first_name'}},
        'api/deals/<int:pk>/census/clear/': deal,
        'api/deals/<int:pk>/census/marks/': deal,
        'api/deals/<int:pk>/census/missing/': deal,
        'api/deals/<int:pk>/census/template/': deal,
        'api/deals/<int:pk>/census/export/': deal,
    }


ALL = {'signed_out': 401, 'producer': 200, 'admin': 200}
MADE = {**ALL, 'producer': 201, 'admin': 201}
GONE = {**ALL, 'producer': 204, 'admin': 204}


def matrix(world):
    return [
        ('GET', 'api/deals/<int:pk>/census/', ALL),
        ('POST', 'api/deals/<int:pk>/census/search/', ALL, {'q': 'Smith'}),
        ('POST', 'api/deals/<int:pk>/census/imports/', MADE, {'document_id': world['file'].id}),
        ('GET', 'api/census/imports/<int:import_id>/', ALL),
        ('PATCH', 'api/census/imports/<int:import_id>/', ALL, {'first_data_row': 3}),
        ('POST', 'api/census/imports/<int:import_id>/apply/', ALL),
        ('POST', 'api/census/imports/<int:import_id>/discard/', GONE),
        ('POST', 'api/deals/<int:pk>/census/members/', MADE, {'kind': 'employee', 'values': {'first_name': 'Quinn'}}),
        ('PATCH', 'api/census/members/<int:member_id>/', ALL, {'values': {'first_name': 'Quinn'}}),
        ('GET', 'api/census/members/<int:member_id>/source/', ALL),
        ('DELETE', 'api/census/members/<int:member_id>/', GONE),
        ('POST', 'api/deals/<int:pk>/census/clear/', GONE, {'confirm': True}),
        ('POST', 'api/deals/<int:pk>/census/marks/', ALL, {'action': 'approve'}),
        ('GET', 'api/deals/<int:pk>/census/missing/', ALL),
        ('GET', 'api/deals/<int:pk>/census/template/', ALL),
        ('GET', 'api/deals/<int:pk>/census/export/', ALL),
    ]


def test_Q3_census_gets_write_nothing_but_their_viewed_rows(admin_api, world):
    sweep_gets(admin_api, ('census',), samples(world))


def test_Q3_census_permission_matrix(actors, no_csrf_api, world):
    check_permissions(actors, ('census',), matrix(world), samples(world), no_csrf_api)


def test_Q3_ids_past_bigint_and_bad_bodies_answer_404_or_400(api, deal):
    assert api.get(f'/api/deals/{2**64}/census/').status_code == 404
    assert api.get(f'/api/census/imports/{2**64}/').status_code == 404
    assert api.post(f'/api/deals/{deal.id}/census/imports/', {'document_id': 'x'}, format='json').status_code == 400
    assert api.post(f'/api/deals/{deal.id}/census/imports/', {'document_id': 2**64}, format='json').status_code == 400
    assert api.get(f'/api/deals/{deal.id}/census/', {'page': 'x'}).status_code == 400
    assert api.get(f'/api/deals/{deal.id}/census/', {'show': 'everyone'}).status_code == 400


def test_Q3_apply_locks_the_deal_the_import_and_the_people(user, world):
    with CaptureQueriesContext(connection) as queries:
        services.apply_import(user, world['import'].id)
    locks = ' '.join(q['sql'] for q in queries.captured_queries if 'FOR UPDATE' in q['sql'])
    for table in ('deals_deal', 'census_censusimport', 'census_member', 'census_censusfacts'):
        assert f'"{table}"' in locks, table


def test_Q3_C17_opening_an_import_is_a_logged_view_of_the_file(user, api, world):
    from deals.models import Activity

    api.get(f'/api/census/imports/{world["import"].id}/')
    viewed = Activity.objects.filter(deal=world['deal'], action='viewed').get()
    assert viewed.document_id == world['import'].document_id
    assert 'synthetic' not in viewed.summary  # the kind, never the file's name


def test_Q3_9_facts_equal_a_rebuild_after_every_service(user, world):
    deal, imp = world['deal'], world['import']
    assert facts.differences(deal.id) == {}
    services.update_import(user, imp.id, {'mapping': [{'column': 7, 'field': ''}]})
    assert facts.differences(deal.id) == {}
    services.apply_import(user, imp.id)
    assert facts.differences(deal.id) == {}
    stored = facts.summary(facts.stored(deal.id))
    assert (stored['employees'], stored['dependents']) == (2, 1)
    other = import_file(user, deal, xlsx(roster(LEE)))
    services.discard_import(user, other.id)
    assert facts.differences(deal.id) == {}


def test_Q3_9_C22_the_lines_to_quote_and_medical_in_force_move_what_is_required(user, world):
    deal = world['deal']
    services.apply_import(user, world['import'].id)  # Robin Lee has no medical tier or plan
    before = facts.stored(deal.id)
    assert before['missing'] == {'medical_tier': 1}
    intake.set_intent(user, deal.id, line='medical', has_today=True)  # medical in force: its current plan is needed
    after = facts.stored(deal.id)
    assert after['missing'] == {'medical_tier': 1, 'medical_plan': 1}
    assert facts.differences(deal.id) == {}
    intake.set_intent(user, deal.id, line='medical', remove=True)
    assert facts.stored(deal.id)['missing'] == {}
    assert facts.differences(deal.id) == {}


def test_C23_census_ok_reaches_intake(user, world):
    from intake import providers

    assert providers.census_state(world['deal'].id) == {'has_roster': True, 'employees': 1, 'errors': 0, 'ok': True}
    services.apply_import(user, world['import'].id)
    assert providers.census_state(world['deal'].id)['ok'] is False  # Robin Lee's medical tier is missing
    assert providers.census_state(0) == {'has_roster': False, 'employees': 0, 'errors': 0, 'ok': False}


def test_Q3_9_rebuild_facts_finds_and_fixes_a_difference(user, world):
    deal = world['deal']
    CensusFacts.objects.filter(deal=deal).update(employees=99)
    with pytest.raises(CommandError):
        call_command('rebuild_facts', stdout=io.StringIO())
    out = io.StringIO()
    call_command('rebuild_facts', '--fix', stdout=out)
    assert f'Deal {deal.id}: census facts differ in employees' in out.getvalue()
    assert facts.differences(deal.id) == {}
    call_command('rebuild_facts', stdout=io.StringIO())


def test_O6_13_removed_people_are_hidden_but_kept(user, world):
    deal = world['deal']
    imported(user, deal, xlsx(roster(LEE)))
    assert list(Member.objects.filter(deal=deal).values_list('values__last_name', flat=True)) == ['Lee']
    assert Member.all_objects.filter(deal=deal, removed_at__isnull=False).count() == 2
    assert list(deal.members.values_list('values__last_name', flat=True)) == ['Lee']
