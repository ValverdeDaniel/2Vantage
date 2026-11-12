"""One census cell's source for ↗ and the Documents station (plan.md §7.7, §10.7; E18, E43; slice 65): a cell the
import read opens at its own cell of the file; a hand edit keeps the file (E66); SSNs stay masked and the file bar's
words name the column, never the person (rule 10). Read only."""

import pytest

from census import services
from census.models import Member
from conftest import make_deal
from deals.models import Activity

from .helpers import family, imported, roster, xlsx

pytestmark = pytest.mark.django_db

SMITH = family('E1', 'Smith', tier='ES', deps=[('Spouse', 'Blake', '02/02/1981')])


@pytest.fixture
def world(user):
    deal = make_deal(user, requested_lines=('medical',))
    imported(user, deal, xlsx(roster(SMITH)))
    return {'deal': deal, 'avery': Member.objects.get(deal=deal, kind='employee')}


def source(api, member, key):
    return api.get(f'/api/census/members/{member.id}/source/', {'key': key})


def test_E43_a_read_cell_opens_at_its_own_cell_of_the_census_file(api, world):
    avery = world['avery']
    before = Activity.objects.count()
    body = source(api, avery, 'last_name').json()
    entry = avery.sources['last_name']
    assert body['source']['doc'] == entry['doc'] and body['source']['cell'] == entry['cell']
    assert body['source']['cell'].startswith('Census!') and body['source']['origin'] == 'import'
    assert (body['member_id'], body['key'], body['value']) == (avery.id, 'last_name', 'Smith')
    assert body['what'] == body['label'] == 'Last Name' and 'Smith' not in body['what']
    assert Activity.objects.count() == before  # a GET writes nothing


def test_E43_E66_a_hand_edit_keeps_its_file_and_a_blank_has_no_source(user, api, world):
    avery = world['avery']
    services.edit_values(user, avery.id, {'last_name': 'Smyth'})
    body = source(api, avery, 'last_name').json()
    assert body['value'] == 'Smyth' and body['source']['origin'] == 'typed'
    assert body['source']['doc'] == avery.sources['last_name']['doc'] and body['source']['cell']
    assert source(api, avery, 'job_title').json()['source'] is None


def test_E43_an_ssn_stays_masked_and_bad_asks_are_refused(user, api, world):
    avery = world['avery']
    services.edit_values(user, avery.id, {'ssn': '123-45-6789'})
    assert source(api, avery, 'ssn').json()['value'].endswith('6789')
    assert '123-45' not in source(api, avery, 'ssn').json()['value']
    assert source(api, avery, 'not_a_column').status_code == 400
    assert source(api, avery, '').status_code == 400
    assert api.get(f'/api/census/members/{2**64}/source/', {'key': 'last_name'}).status_code == 404
    services.remove_member(user, avery.id)
    assert source(api, avery, 'last_name').status_code == 404
