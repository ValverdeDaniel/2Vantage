"""Giving someone else access (L72) and edit mode (L34, L35; plan.md §7.13 `requests/{rid}/people/`, `enter/`,
`census-blanks/`): a new link on the same request at its level, with its PIN once; answers read over the phone go
through the owners' typed writes as the client's (relay) or ours (typed), and an unchanged value writes nothing."""

import pytest
from django.contrib.auth.hashers import check_password

from census.models import Member
from deals.models import Activity
from deals.services import create_contact
from intake.models import Intake
from review.models import ClientLink

from .decision_world import cell_entry, census_answers, link_on
from .portal_world import make_request, person

pytestmark = pytest.mark.django_db


def people_url(deal, link):
    return f'/api/deals/{deal.id}/review/requests/{link.request_id}/people/'


def test_L72_someone_else_gets_their_own_link_at_the_requests_level(api, user, deal):
    link, _token, _pin = make_request(user, deal, {'census': {'scope': 'missing'}}, security='pin')
    lee = create_contact(user, deal.client_id, name='Lee Example', email='lee@example.com', role='hr_admin')
    answer = api.post(people_url(deal, link), {'people': [{'contact_id': lee.id}]}, format='json')
    assert answer.status_code == 201, answer.content
    (made,) = answer.json()['links']
    new = ClientLink.objects.get(pk=made['link_id'])
    assert (new.request_id, new.contact_id, new.security) == (link.request_id, lee.id, 'pin')
    assert check_password(made['pin'], new.pin_hash)
    row = Activity.objects.get(pk=answer.json()['activity_id'])
    assert 'Lee' not in row.summary + str(row.changes)
    again = api.post(people_url(deal, link), {'people': [{'contact_id': lee.id}]}, format='json')
    assert again.status_code == 400  # they already hold a link here
    assert api.post(people_url(deal, link), {'people': []}, format='json').status_code == 400


def test_L35_relayed_answers_are_saved_as_the_clients_entered_by_us(api, user, deal):
    avery = person(user, deal, 'Avery', 'Synthetic')
    body = {'answers': {'intake:dba': 'Example Trading', f'census:{avery.id}:zip': '32801'}, 'origin': 'relay'}
    answer = api.post(f'/api/deals/{deal.id}/review/enter/', body, format='json')
    assert answer.status_code == 200, answer.content
    assert sorted(answer.json()['saved']) == sorted(body['answers'])
    intake = Intake.objects.get(deal=deal)
    assert intake.answers['dba'] == 'Example Trading' and intake.sources['dba']['origin'] == 'relay'
    member = Member.objects.get(pk=avery.pk)
    assert member.values['zip'] == '32801' and member.sources['zip']['origin'] == 'relay'
    again = api.post(f'/api/deals/{deal.id}/review/enter/', body, format='json')
    assert again.json() == {'saved': [], 'activity_ids': []}  # unchanged: nothing written


def test_L35_typed_and_a_waiting_client_answer_is_replaced(api, user, deal):
    avery = person(user, deal, 'Avery', 'Synthetic')
    link = link_on(user, deal)
    census_answers(deal, link, {(avery.id, 'zip'): '32789'})
    body = {'answers': {f'census:{avery.id}:zip': '32801'}, 'origin': 'typed'}
    assert api.post(f'/api/deals/{deal.id}/review/enter/', body, format='json').status_code == 200
    assert Member.objects.get(pk=avery.pk).sources['zip']['origin'] == 'typed'
    assert cell_entry(avery, 'zip')['status'] == 'replaced'


@pytest.mark.parametrize(
    'ref', ['intake:block:contacts', 'census:999999:zip', 'census:1:ssn', 'doc:claims', 'intake:not_a_question']
)
def test_L35_edit_mode_refuses_what_it_cannot_take(api, deal, ref):
    answer = api.post(f'/api/deals/{deal.id}/review/enter/', {'answers': {ref: 'x'}}, format='json')
    assert answer.status_code == 400


def test_L35_census_blanks_list_people_required_first_and_never_ssn(api, user, deal):
    person(user, deal, 'Avery', 'Synthetic')
    answer = api.get(f'/api/deals/{deal.id}/review/census-blanks/')
    assert answer.status_code == 200 and answer['Cache-Control'] == 'private, no-store'
    found = answer.json()
    ((avery,),) = [found['people']]
    columns = [cell['column'] for cell in avery['cells']]
    flags = [cell['required'] for cell in avery['cells']]
    assert 'ssn' not in columns and flags == sorted(flags, reverse=True)
    required = api.get(f'/api/deals/{deal.id}/review/census-blanks/?required=1').json()
    assert all(cell['required'] for row in required['people'] for cell in row['cells'])
