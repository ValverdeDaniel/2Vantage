"""The Q.3 contracts for review (plan.md §12.3): GETs write nothing, the permission matrix, ids past bigint and on the
wrong deal, the lock order, and the Board and the facts in a fixed number of queries (Q.3 #4)."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import check_permissions, make_deal, sweep_gets
from review import services, summary
from review.models import ClientLink, ClientRequest

pytestmark = pytest.mark.django_db

ASK = {
    'asks': {'intake': {'scope': 'missing', 'blocks': ['bor']}, 'census': {'file': True}},
    'people': [{'name': 'Dana'}],
}


@pytest.fixture
def made(user, deal):
    return services.create(user, deal.id, ASK)


def samples(deal, made):
    token = made.links[0][1].rsplit('/', 1)[1]
    return {
        'api/deals/<int:pk>/review/board/': {'pk': deal.id},
        'api/deals/<int:pk>/review/queue/': {'pk': deal.id},
        'api/deals/<int:pk>/review/approve/': {'pk': deal.id},
        'api/deals/<int:pk>/review/reject/': {'pk': deal.id},
        'api/deals/<int:pk>/review/undo/': {'pk': deal.id},
        'api/deals/<int:pk>/review/requests/': {'pk': deal.id},
        'api/deals/<int:pk>/review/requests/<int:rid>/close/': {'pk': deal.id, 'rid': made.request.id},
        'api/links/<int:lid>/': {'lid': made.links[0][0].id},
        'api/links/<int:lid>/preview/': {'lid': made.links[0][0].id},
        **{route: {'token': token} for route in PORTAL},
    }


ALL = {'signed_out': 401, 'producer': 200, 'admin': 200}
# The portal (rule 11): public; a staff session reads it and every write answers 403.
PUBLIC_READ = {'signed_out': 200, 'producer': 200, 'admin': 200}
PUBLIC_WRITE = {'signed_out': 200, 'producer': 403, 'admin': 403}
PORTAL = [
    'api/portal/<str:token>/',
    'api/portal/<str:token>/verify/',
    'api/portal/<str:token>/save/',
    'api/portal/<str:token>/submit/',
    'api/portal/<str:token>/files/',
    'api/portal/<str:token>/people/',
    'api/portal/<str:token>/sign/',
    'api/portal/<str:token>/stamp/',
    'api/portal/<str:token>/census-template/',
]
MATRIX = [
    ('GET', 'api/deals/<int:pk>/review/board/', ALL),
    ('GET', 'api/deals/<int:pk>/review/queue/', ALL),
    ('POST', 'api/deals/<int:pk>/review/approve/', ALL, {'refs': ['intake:fein']}),
    ('POST', 'api/deals/<int:pk>/review/reject/', ALL, {'refs': ['intake:fein']}),
    ('POST', 'api/deals/<int:pk>/review/undo/', ALL, {'refs': ['intake:fein']}),
    ('POST', 'api/deals/<int:pk>/review/requests/', {**ALL, 'producer': 201, 'admin': 201}, ASK),
    ('POST', 'api/deals/<int:pk>/review/requests/<int:rid>/close/', ALL, {'reason': 'cancelled'}),
    ('PATCH', 'api/links/<int:lid>/', ALL, {'action': 'mark_sent', 'copied': True}),
    ('GET', 'api/links/<int:lid>/preview/', ALL),
    ('GET', 'api/portal/moved/', PUBLIC_READ),
    ('GET', 'api/portal/<str:token>/', PUBLIC_READ),
    ('GET', 'api/portal/<str:token>/stamp/', PUBLIC_READ),
    ('GET', 'api/portal/<str:token>/census-template/', PUBLIC_READ),
    # A link that asks for no PIN: verify answers as proved; a staff session never proves one (403).
    ('POST', 'api/portal/<str:token>/verify/', PUBLIC_WRITE, {'pin': '000000'}),
    ('POST', 'api/portal/<str:token>/save/', PUBLIC_WRITE, {'answers': {}}),
    ('POST', 'api/portal/<str:token>/submit/', PUBLIC_WRITE, {'answers': {}}),
    ('POST', 'api/portal/<str:token>/sign/', PUBLIC_WRITE, {'name': 'Jordan Example'}),
    ('POST', 'api/portal/<str:token>/people/', {**PUBLIC_WRITE, 'signed_out': 400}, {'people': []}),
    ('POST', 'api/portal/<str:token>/files/', {**PUBLIC_WRITE, 'signed_out': 400}, {'slot': 'census_file'}),
]


def test_Q3_review_gets_write_nothing(admin_api, deal, made):
    sweep_gets(admin_api, ('review',), samples(deal, made))


def test_Q3_review_permission_matrix(actors, no_csrf_api, deal, made):
    check_permissions(actors, ('review',), MATRIX, samples(deal, made), no_csrf_api)


def test_B4_ids_past_bigint_or_on_another_deal_answer_404(api, user, deal, made):
    big = 2**64
    assert api.get(f'/api/deals/{big}/review/board/').status_code == 404
    assert api.post(f'/api/deals/{big}/review/requests/', ASK, format='json').status_code == 404
    assert api.post(f'/api/deals/{deal.id}/review/requests/{big}/close/', {}, format='json').status_code == 404
    assert api.patch(f'/api/links/{big}/', {'action': 'revoke'}, format='json').status_code == 404
    other = make_deal(user, name='Other Co.')
    url = f'/api/deals/{other.id}/review/requests/{made.request.id}/close/'
    assert api.post(url, {'reason': 'cancelled'}, format='json').status_code == 404
    assert ClientRequest.objects.get(pk=made.request.id).closed_at is None


def test_B4_a_bad_action_answers_400_and_writes_nothing(api, made):
    link = made.links[0][0]
    answer = api.patch(f'/api/links/{link.id}/', {'action': 'delete_everything'}, format='json')
    assert answer.status_code == 400 and 'action' in answer.json()
    assert api.patch(f'/api/links/{link.id}/', ['revoke'], format='json').status_code == 400
    assert ClientLink.objects.get(pk=link.id).revoked_at is None


def test_Q3_writes_lock_the_deal_first_then_the_request_then_the_link(user, made):
    link = made.links[0][0]
    for call in (
        lambda: services.mark_sent(user, link.id),
        lambda: services.revoke(user, link.id),
        lambda: services.close(user, made.request.id, 'cancelled'),
    ):
        with CaptureQueriesContext(connection) as queries:
            call()
        locks = [q['sql'] for q in queries.captured_queries if 'FOR UPDATE' in q['sql']]
        assert '"deals_deal"' in locks[0] and 'deals_client' not in locks[0].split('FOR UPDATE')[1]
        assert '"review_clientrequest"' in locks[1]
        assert all('"review_clientlink"' in sql for sql in locks[2:])


def _queries(read):
    with CaptureQueriesContext(connection) as captured:
        read()
    return len(captured.captured_queries)


def test_Q3_4_the_board_reads_in_a_fixed_number_of_queries(api, user):
    small = make_deal(user, name='Small Co.')
    services.create(user, small.id, ASK)
    big = make_deal(user, name='Big Co.')
    for n in range(4):
        made = services.create(user, big.id, {**ASK, 'people': [{'name': f'P{n}'}, {'name': f'Q{n}'}]})
        services.mark_sent(user, made.links[0][0].id)

    def board(deal):
        return lambda: api.get(f'/api/deals/{deal.id}/review/board/')

    assert _queries(board(big)) == _queries(board(small))


def test_Q3_4_the_facts_read_one_deal_and_four_in_the_same_queries(user):
    deals = [make_deal(user, name=f'Deal {n} Co.') for n in range(4)]
    for deal in deals:
        services.create(user, deal.id, ASK)
    assert _queries(lambda: summary.facts([deals[0].id])) == _queries(lambda: summary.facts([d.id for d in deals]))
