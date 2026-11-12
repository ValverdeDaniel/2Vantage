"""The roster's name search posts its value (plan.md §3.8, E28; Q.8; slice 47): a person's name never rides a URL,
where every request log keeps it. `POST deals/{id}/census/search/` narrows the roster to the families with that first
or last name; the page's GET ignores a `q`, so an old client cannot narrow (or leak) by URL. A refusal never repeats
the name, and the search writes nothing."""

import logging

import pytest

from census.models import CensusFacts, Member
from deals.models import Activity

from .helpers import family, imported, roster, xlsx

pytestmark = pytest.mark.django_db

SMITH = family('E1', 'Smith', tier='ES', deps=[('Spouse', 'Blake', '02/02/1981')])
QUILL = family('E2', 'Vexcanary', first='Quillonia')


@pytest.fixture
def census(user, deal):
    imported(user, deal, xlsx(roster(SMITH, QUILL)))
    return deal


def last_names(answer):
    return sorted({member['values']['last_name'] for member in answer.json()['members']})


def test_E28_Q8_a_name_search_posts_its_value_and_narrows_the_roster(api, census):
    url = f'/api/deals/{census.id}/census/search/'
    found = api.post(url, {'q': 'vexCAN'}, format='json')
    assert found.status_code == 200 and last_names(found) == ['Vexcanary']
    assert found.json()['page']['employees'] == 1
    spouse = api.post(url, {'q': 'Blake', 'show': 'all', 'page': 1, 'page_size': 50}, format='json')
    assert last_names(spouse) == ['Smith']  # a dependent's name finds the family
    everyone = api.post(url, {}, format='json')
    assert last_names(everyone) == ['Smith', 'Vexcanary']
    assert everyone.json()['summary'] == api.get(f'/api/deals/{census.id}/census/').json()['summary']


def test_E28_the_page_read_ignores_a_name_in_its_url(api, census):
    answer = api.get(f'/api/deals/{census.id}/census/', {'q': 'Vexcanary'})
    assert answer.status_code == 200 and last_names(answer) == ['Smith', 'Vexcanary']


def test_E28_Q8_a_refused_search_never_repeats_the_name_and_nothing_is_written(api, census, caplog):
    caplog.set_level(logging.DEBUG)
    url = f'/api/deals/{census.id}/census/search/'
    log, facts = list(Activity.objects.values()), list(CensusFacts.objects.values())
    people = list(Member.objects.values())
    refused = [
        api.post(url, {'q': ['Quillonia']}, format='json'),
        api.post(url, {'q': 'Quillonia', 'page': 'Quillonia'}, format='json'),
        api.post(url, {'q': 'Quillonia', 'show': 'Quillonia'}, format='json'),
        api.post(url, ['Quillonia'], format='json'),
    ]
    assert [answer.status_code for answer in refused] == [400, 400, 400, 400]
    for answer in refused:
        assert 'quillonia' not in answer.content.decode().lower()
    assert api.post(url, {'q': 'Quillonia'}, format='json').status_code == 200
    assert 'quillonia' not in caplog.text.lower()
    assert list(Activity.objects.values()) == log and list(CensusFacts.objects.values()) == facts
    assert list(Member.objects.values()) == people
