"""The Q.3 contracts for documents: GETs write nothing (but access rows) and the permission matrix (plan.md §12.3)."""

import pytest

from conftest import check_permissions, sweep_gets

from .helpers import RATES_XLSX_ROWS, stored, xlsx


@pytest.fixture
def world(user, deal):
    return {'deal': deal, 'sheet': stored(user, deal, name='census.xlsx', kind='census', content=xlsx(RATES_XLSX_ROWS))}


def samples(world):
    deal, sheet = world['deal'], world['sheet']
    one = {'document_id': sheet.id}
    return {
        'api/deals/<int:pk>/documents/': {'pk': deal.id},
        'api/documents/<int:document_id>/': one,
        'api/documents/<int:document_id>/archive/': one,
        'api/documents/<int:document_id>/restore/': one,
        'api/documents/<int:document_id>/download/': one,
        'api/documents/<int:document_id>/sheet/': {**one, 'query': {'look': '1'}},
        'api/documents/<int:document_id>/sheet/find/': one,
    }


ALL = {'signed_out': 401, 'producer': 200, 'admin': 200}
MATRIX = [
    ('GET', 'api/deals/<int:pk>/documents/', ALL),
    ('POST', 'api/deals/<int:pk>/documents/', {**ALL, 'producer': 400, 'admin': 400}),  # no file: 400 past the check
    ('PATCH', 'api/documents/<int:document_id>/', ALL, {'carrier': 'Aetna'}),
    ('DELETE', 'api/documents/<int:document_id>/', {'signed_out': 401, 'producer': 403, 'admin': 204}),
    ('POST', 'api/documents/<int:document_id>/archive/', ALL),
    ('POST', 'api/documents/<int:document_id>/restore/', ALL),
    ('GET', 'api/documents/<int:document_id>/download/', ALL),
    ('GET', 'api/documents/<int:document_id>/sheet/', ALL),
    ('POST', 'api/documents/<int:document_id>/sheet/find/', ALL, {'value': '512.34'}),
]


def test_Q3_documents_gets_write_nothing_but_access_rows(admin_api, world):
    sweep_gets(admin_api, ('documents',), samples(world))


def test_Q3_documents_permission_matrix(actors, no_csrf_api, world):
    check_permissions(actors, ('documents',), MATRIX, samples(world), no_csrf_api)


def test_Q3_ids_past_bigint_answer_404(api):
    assert api.get(f'/api/documents/{2**64}/download/').status_code == 404
    assert api.get(f'/api/deals/{2**64}/documents/').status_code == 404
