"""The Board endpoint and slice 53's "done when" through the API (plan.md §13.10 row 53; L1, L2, L7, L8, L28): a link
is created, copied and revoked; the Waiting lane and the pills count it. GD6 reads its own readiness."""

import pytest

from deals import activity
from deals.services import mark_lost
from review.models import ClientLink

pytestmark = pytest.mark.django_db

ASK = {'asks': {'intake': {'scope': 'missing'}, 'census': {'file': True}}, 'people': [{'name': 'Dana Example'}]}


def board(api, deal):
    answer = api.get(f'/api/deals/{deal.id}/review/board/')
    assert answer.status_code == 200
    return answer.json()


def test_S53_done_when_a_link_is_created_copied_and_revoked_and_the_lane_counts_it(api, user, deal):
    empty = board(api, deal)
    assert empty['lanes']['waiting'] == [] and empty['counts']['waiting'] == 0 and empty['asks_closed'] is None

    created = api.post(f'/api/deals/{deal.id}/review/requests/', ASK, format='json')
    assert created.status_code == 201
    made = created.json()
    (link,) = made['links']
    assert link['path'].startswith('/portal/') and link['pin'] == '' and link['security'] == 'link'
    assert made['request']['asks'] == ['The census file', 'Intake gaps'] and made['request']['state'] == 'draft'

    drawn = board(api, deal)
    (row,) = drawn['lanes']['waiting']
    (person,) = row['recipients']
    assert drawn['counts']['waiting'] == 1
    assert (person['name'], person['state'], person['path']) == ('Dana Example', 'draft', link['path'])

    copied = api.patch(f'/api/links/{link["link_id"]}/', {'action': 'mark_sent', 'copied': True}, format='json')
    assert copied.status_code == 200
    assert copied.json()['link']['state'] == 'waiting' and copied.json()['request']['state'] == 'waiting'
    assert board(api, deal)['lanes']['waiting'][0]['recipients'][0]['sent']

    revoked = api.patch(f'/api/links/{link["link_id"]}/', {'action': 'revoke'}, format='json')
    assert revoked.status_code == 200 and revoked.json()['link']['state'] == 'off'
    after = board(api, deal)
    assert after['lanes']['waiting'] == [] and after['counts']['waiting'] == 0

    activity.revert(revoked.json()['activity_id'], user)  # the toast's Undo turns it back on
    assert board(api, deal)['lanes']['waiting'][0]['recipients'][0]['state'] == 'waiting'


def test_L64_a_new_pin_comes_back_once_and_never_in_the_board(api, user, deal):
    body = {'asks': {'census': {'scope': 'missing'}}, 'people': [{'name': 'Dana'}]}
    made = api.post(f'/api/deals/{deal.id}/review/requests/', body, format='json').json()
    (link,) = made['links']
    assert link['security'] == 'pin' and len(link['pin']) == 6
    again = api.patch(f'/api/links/{link["link_id"]}/', {'action': 'new_pin'}, format='json').json()
    assert len(again['pin']) == 6
    assert again['pin'] not in str(board(api, deal)) and link['pin'] not in str(board(api, deal))


def test_L40_the_dry_run_answers_the_floor(api, deal):
    body = {'asks': {'census': {'scope': 'missing'}}, 'people': [], 'security': 'link'}
    answer = api.post(f'/api/deals/{deal.id}/review/requests/?dry_run=1', body, format='json')
    assert answer.status_code == 200
    found = answer.json()
    numbers = found.pop('numbers')  # the builder's live numbers (slice 57): no census yet, so nothing to ask
    assert found == {
        'floor': {'level': 'pin', 'because': ['Census']},
        'security': 'pin',
        'people': 0,
        'asks': ['The census gaps'],
    }
    assert numbers['values'] == 0 and numbers['total'] == 0
    assert not ClientLink.objects.exists()


def test_L129_a_lost_deal_reads_but_refuses_new_asks_with_409(api, user, deal):
    mark_lost(user, deal.id, reason='Went elsewhere')
    assert 'marked lost' in board(api, deal)['asks_closed']
    answer = api.post(f'/api/deals/{deal.id}/review/requests/', ASK, format='json')
    assert answer.status_code == 409 and 'marked lost' in answer.json()['detail']


def test_L55_bad_bodies_answer_400_by_field(api, deal):
    answer = api.post(f'/api/deals/{deal.id}/review/requests/', {'asks': {}, 'security': 'x'}, format='json')
    assert answer.status_code == 400 and set(answer.json()) == {'asks', 'security'}
    assert api.post(f'/api/deals/{deal.id}/review/requests/', ['x'], format='json').status_code == 400


def test_L70_close_answers_the_request_closed(api, deal):
    made = api.post(f'/api/deals/{deal.id}/review/requests/', ASK, format='json').json()
    answer = api.post(
        f'/api/deals/{deal.id}/review/requests/{made["request"]["id"]}/close/', {'reason': 'superseded'}, format='json'
    ).json()
    assert answer['request']['state'] == 'closed'
    assert answer['request']['close_reason_label'] == 'Replaced by a newer request'
    assert answer['request']['recipients'][0]['path'] is None  # a closed request's link is never copied again
    assert board(api, deal)['lanes']['waiting'] == []


def test_L2_Q9_GD6_reads_its_intake_readiness_and_needs_a_pin_for_census_people(api, gd6):
    drawn = board(api, gd6.deal)
    assert drawn['readiness']['state'] == 'blocked' and 0 < drawn['readiness']['pct'] <= 100
    assert drawn['counts'] == {'to_send': 0, 'to_review': 0, 'waiting': 0, 'questions': 0}
    body = {'asks': {'census': {'scope': 'all', 'columns': ['dob']}}, 'people': [{'name': 'HR'}]}
    answer = api.post(f'/api/deals/{gd6.deal.id}/review/requests/?dry_run=1', body, format='json').json()
    assert answer['security'] == 'pin'


def test_L133_the_words_come_from_meta(api):
    found = api.get('/api/meta/').json()['review']
    assert [level['key'] for level in found['levels']] == ['link', 'pin']
    assert {'key': 'off', 'label': 'Turned off'} in found['link_states']
    assert found['life_days'] == 7 and found['ceiling_days'] == 30
