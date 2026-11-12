"""The Q.3 contracts for rfp (plan.md §12.3): the write path, GETs write nothing, the permission matrix, ids past
bigint, the lock order and a payload that reads in a fixed number of queries."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import check_permissions, make_deal, sweep_gets, write_path_contract
from rfp import services
from rfp.models import RfpRequest

from .roster import family

pytestmark = pytest.mark.django_db


def samples(deal):
    return {
        'api/deals/<int:pk>/rfp/': {'pk': deal.id},
        'api/deals/<int:pk>/rfp/done/': {'pk': deal.id},
        'api/deals/<int:pk>/rfp/files/<str:key>/': {'pk': deal.id, 'key': 'census-uhc'},
        'api/deals/<int:pk>/rfp/files/<str:key>/look/': {'pk': deal.id, 'key': 'census-angle-csv'},
        'api/deals/<int:pk>/rfp/formats/': {'pk': deal.id},
        'api/deals/<int:pk>/rfp/formats/<str:key>/': {'pk': deal.id, 'key': 'census-warner'},
    }


ALL = {'signed_out': 401, 'producer': 200, 'admin': 200}
MATRIX = [
    ('GET', 'api/deals/<int:pk>/rfp/', ALL),
    ('PATCH', 'api/deals/<int:pk>/rfp/', ALL, {'carriers': {'add': ['aetna']}}),
    ('POST', 'api/deals/<int:pk>/rfp/done/', ALL, {'card': 'request', 'done': True}),
    ('GET', 'api/deals/<int:pk>/rfp/files/<str:key>/', ALL),
    ('GET', 'api/deals/<int:pk>/rfp/files/<str:key>/look/', ALL),
    ('GET', 'api/deals/<int:pk>/rfp/formats/', ALL),
    ('GET', 'api/deals/<int:pk>/rfp/formats/<str:key>/', ALL),
]


def test_Q3_rfp_gets_write_nothing_but_the_access_rows(admin_api, user, deal):
    family(user, deal)  # the files are built from a census
    sweep_gets(admin_api, ('rfp',), samples(deal))


def test_Q3_rfp_permission_matrix(actors, no_csrf_api, user, deal):
    family(user, deal)
    check_permissions(actors, ('rfp',), MATRIX, samples(deal), no_csrf_api)


def test_Q3_ids_past_bigint_answer_404(api):
    assert api.get(f'/api/deals/{2**64}/rfp/').status_code == 404
    assert api.get(f'/api/deals/{2**64}/rfp/files/census-uhc/').status_code == 404
    assert api.get(f'/api/deals/{2**64}/rfp/formats/').status_code == 404
    assert api.patch(f'/api/deals/{2**64}/rfp/', {}, format='json').status_code == 404
    assert api.post(f'/api/deals/{2**64}/rfp/done/', {}, format='json').status_code == 404


def test_Q3_settings_write_path(user, deal):
    row = RfpRequest.objects.create(deal=deal)
    write_path_contract(
        user,
        row,
        lambda: services.update(user, deal.id, {'carriers': {'add': ['aetna', 'cigna']}, 'route': 'warner'}),
        lambda r: (r.carriers, r.route),
        lambda: services.update(user, deal.id, {'carriers': {'remove': ['cigna']}}),
    )


def test_Q3_ticks_write_path(user, deal):
    row = RfpRequest.objects.create(deal=deal)
    write_path_contract(
        user,
        row,
        lambda: services.update(user, deal.id, {'include': {'census-uhc': False, 'census-angle-csv': True}}),
        lambda r: r.include,
        lambda: services.update(user, deal.id, {'include': {'census-uhc': None}}),
    )


def test_Q3_mark_write_path(user, deal):
    row = RfpRequest.objects.create(deal=deal)
    write_path_contract(
        user,
        row,
        lambda: services.set_done(user, deal.id, 'request', True),
        lambda r: r.done,
        lambda: services.set_done(user, deal.id, 'request', False),
    )


def test_Q3_writes_lock_the_deal_first_then_the_request(user, deal):
    RfpRequest.objects.create(deal=deal)
    for call in (
        lambda: services.update(user, deal.id, {'carriers': {'add': ['unum']}}),
        lambda: services.set_done(user, deal.id, 'packet', True),
    ):
        with CaptureQueriesContext(connection) as queries:
            call()
        locks = [q['sql'] for q in queries.captured_queries if 'FOR UPDATE' in q['sql']]
        assert '"deals_deal"' in locks[0]
        assert f'"{RfpRequest._meta.db_table}"' in locks[1]


def test_Q3_4_the_page_reads_in_a_fixed_number_of_queries(api, user):
    def queries(deal):
        with CaptureQueriesContext(connection) as captured:
            assert api.get(f'/api/deals/{deal.id}/rfp/').status_code == 200
        return len(captured.captured_queries)

    small = make_deal(user, requested_lines=('medical',))
    services.update(user, small.id, {'carriers': {'add': ['aetna']}})
    services.set_done(user, small.id, 'request', True)
    big = make_deal(user, name='Bigger Co.', requested_lines=('medical', 'dental', 'vision', 'std', 'ltd', 'gap'))
    services.update(user, big.id, {'carriers': {'add': ['aetna', 'cigna', 'unum', 'apl', 'metlife', 'guardian']}})
    for card in ('coverage', 'request', 'checklist', 'packet'):
        services.set_done(user, big.id, card, True)
    assert queries(big) == queries(small)
