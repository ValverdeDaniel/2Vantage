"""One intake answer's source for ↗ and the Documents station's intake view (plan.md §7.6, §10.7; E18, E44; slice 65):
an answer read from a file opens on its page there; the deal's effective date answers as the form shows it; a GET
writes nothing; a question the form does not ask is refused."""

import pytest

from deals.models import Activity
from intake.models import Intake

pytestmark = pytest.mark.django_db


@pytest.fixture
def read(deal):
    return Intake.objects.create(
        deal=deal,
        answers={'legal_name': 'Example Co.', 'dba': 'Ex'},
        sources={
            'legal_name': {'origin': 'ai', 'doc': 7, 'page': 2, 'line': 'Legal name: Example Co.', 'low': 'faint'},
            'dba': {'origin': 'typed'},
        },
    )


def source(api, deal, key):
    return api.get(f'/api/deals/{deal.id}/intake/source/', {'key': key})


def test_E44_an_answer_read_from_a_file_opens_on_its_page(api, deal, read):
    before = Activity.objects.count()
    body = source(api, deal, 'legal_name').json()
    assert (body['key'], body['value'], body['what']) == ('legal_name', 'Example Co.', body['label'])
    assert {k: body['source'][k] for k in ('origin', 'doc', 'page', 'line', 'low')} == {
        'origin': 'ai',
        'doc': 7,
        'page': 2,
        'line': 'Legal name: Example Co.',
        'low': 'faint',
    }
    assert source(api, deal, 'dba').json()['source']['doc'] is None
    assert Activity.objects.count() == before


def test_E44_unanswered_and_unknown_questions(api, deal, read):
    body = source(api, deal, 'atne').json()
    assert (body['value'], body['source'], body['what']) == ('', None, body['label'])
    assert source(api, deal, 'not_a_question').status_code == 400
    assert api.get(f'/api/deals/{2**64}/intake/source/', {'key': 'dba'}).status_code == 404
