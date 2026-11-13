"""Sending an answer back (plan.md §8.8; L14, L16, L17, L22, L120; slice 56): X in the queue puts a send-back in the
tray; the answer leaves To review for Going back while it waits or once it went out, and comes back when the client
answers again; "Approve N ready" leaves it be; an approval closes what was sent back; the section bar and the export
check count it; the queue's items carry their threads."""

import pytest

from review import summary
from review.export_check import problems
from review.models import ReviewNote
from review.services import decisions, send, tray

from .decision_world import census_answers, employee, intake_answers, link_on, submitted

pytestmark = pytest.mark.django_db


def _queue(api, deal, **params):
    answer = api.get(f'/api/deals/{deal.id}/review/queue/', params)
    assert answer.status_code == 200, answer.content
    return answer.json()


def test_L16_a_send_back_moves_the_answer_to_going_back_until_they_answer_again(api, user, deal):
    link = link_on(user, deal)
    intake_answers(deal, link, {'website': 'https://example.test', 'dba': 'Example'})
    submitted(link, hours_ago=1)
    sent = api.post(
        f'/api/deals/{deal.id}/review/notes/',
        {'kind': 'sendback', 'ref': 'intake:website', 'text': 'Is the address right?'},
        format='json',
    )
    assert sent.status_code == 201, sent.content
    found = _queue(api, deal, surface='intake')
    assert found['phases'] == {'to_review': 1, 'in_progress': 0, 'going_back': 1}
    back = _queue(api, deal, surface='intake', phase='going_back')['items'][0]
    assert back['ref'] == 'intake:website' and back['draft_id'] is not None
    assert back['thread'][0]['kind'] == 'sendback' and back['thread'][0]['text'] == 'Is the address right?'
    send.send(user, deal.id)
    assert _queue(api, deal, surface='intake')['phases']['going_back'] == 1
    facts = summary.facts([deal.id])[deal.id]['sections']['intake']
    assert (facts['going_back'], facts['to_review']) == (1, 1)
    assert decisions.section_refs(deal.id, 'intake') == ['intake:dba']
    intake_answers(deal, link, {'website': 'https://example.test/new'})
    submitted(link)
    assert _queue(api, deal, surface='intake')['phases'] == {'to_review': 2, 'in_progress': 0, 'going_back': 0}


def test_L17_an_approval_closes_what_was_sent_back(user, deal):
    link = link_on(user, deal)
    intake_answers(deal, link, {'website': 'https://example.test'})
    submitted(link, hours_ago=1)
    tray.ask(user, deal.id, ['intake:website'], kind='sendback')
    send.send(user, deal.id)
    decisions.approve(user, deal.id, refs=['intake:website'])
    assert ReviewNote.objects.get(deal=deal, key='website').resolved_at is not None


def test_L120_the_export_check_counts_census_answers_going_back(user, deal):
    member = employee(user, deal)
    link = link_on(user, deal)
    census_answers(deal, link, {(member.id, 'zip'): '33606'})
    submitted(link, hours_ago=1)
    assert {problem['code'] for problem in problems(deal)} == {'client_waiting'}
    tray.ask(user, deal.id, [f'census:{member.id}:zip'], kind='sendback')
    assert {problem['code'] for problem in problems(deal)} == {'going_back'}
