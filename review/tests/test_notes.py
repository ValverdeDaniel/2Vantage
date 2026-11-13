"""Notes and threads (plan.md §5.8, §7.13 `review/notes/`; L22; slice 56): a team note never reaches the client, a note
to the client goes now on the link that asks the item (joining it when it does not), a reply answers and closes their
question, Resolve closes by hand, and Activity never holds a note's words."""

import pytest

from deals.models import Activity
from review.models import ClientLink, ClientRequest, ReviewNote
from review.services import notes, questions

from .portal_world import client, make_request, page

pytestmark = pytest.mark.django_db

CANARY = 'Zqcanarythread'


def _note(api, deal, body):
    return api.post(f'/api/deals/{deal.id}/review/notes/', body, format='json')


def _open_link(user, deal, asks=None):
    link, token, _pin = make_request(user, deal, asks or {'intake': {'scope': 'all'}})
    ClientLink.objects.filter(pk=link.pk).update(sent_at=link.created_at)
    return link, token


def test_L22_a_team_note_stays_with_the_team(api, user, deal):
    _link, token = _open_link(user, deal)
    answer = _note(api, deal, {'kind': 'note', 'ref': 'intake:fein', 'text': CANARY, 'audience': 'team'})
    assert answer.status_code == 201, answer.content
    note = answer.json()['note']
    assert (note['audience'], note['ref'], note['by']) == ('team', 'intake:fein', user.get_full_name() or user.username)
    assert CANARY not in page(client(), token).content.decode()
    assert CANARY not in str(list(Activity.objects.filter(deal=deal).values('summary', 'changes')))


def test_L22_a_note_to_the_client_goes_now_and_joins_the_item_to_their_link(api, user, deal):
    link, token = _open_link(user, deal, {'intake': {'scope': 'required'}})
    answer = _note(api, deal, {'kind': 'note', 'ref': 'intake:website', 'text': 'Is this right?', 'audience': 'client'})
    assert answer.status_code == 201, answer.content
    assert answer.json()['note']['request_id'] == link.request_id
    assert 'website' in ClientRequest.objects.get(pk=link.request_id).asks['intake']['keys']
    cards = page(client(), token).json()['follow_ups']
    assert [(card['ref'], card['new'], card['thread'][0]['text']) for card in cards] == [
        ('intake:website', True, 'Is this right?')
    ]


def test_L22_a_note_to_the_client_with_no_open_link_is_refused(api, deal):
    answer = _note(api, deal, {'kind': 'note', 'ref': 'intake:fein', 'text': 'Hello', 'audience': 'client'})
    assert answer.status_code == 409 and 'Ask for it instead' in answer.json()['detail']
    assert not ReviewNote.objects.filter(deal=deal).exists()


def test_L22_a_reply_answers_their_question_and_closes_it(api, user, deal):
    link, token = _open_link(user, deal)
    (question,) = questions.ask(link.id, [{'ref': 'intake:fein', 'text': 'Where do I find it?'}])
    answer = _note(api, deal, {'kind': 'reply', 'question_id': question.id, 'text': 'On your IRS letter.'})
    assert answer.status_code == 201, answer.content
    assert ReviewNote.objects.get(pk=question.id).resolved_at is not None
    card = next(card for card in page(client(), token).json()['follow_ups'] if card['ref'] == 'intake:fein')
    assert [entry['who'] for entry in card['thread']] == ['you', 'agency']
    assert card['replied'] and not card['question_open']


def test_L22_resolve_closes_a_question_and_refuses_a_note(api, user, deal):
    link, _token = _open_link(user, deal)
    (question,) = questions.ask(link.id, [{'ref': 'intake:fein', 'text': 'Which one?'}])
    url = f'/api/deals/{deal.id}/review/notes/{question.id}/'
    first = api.patch(url, {'action': 'resolve'}, format='json')
    assert first.status_code == 200 and first.json()['note']['resolved_at']
    assert api.patch(url, {'action': 'resolve'}, format='json').json()['activity_id'] is None  # once
    team = notes.add(user, deal.id, 'intake:fein', 'For us', audience='team').note
    assert (
        api.patch(f'/api/deals/{deal.id}/review/notes/{team.id}/', {'action': 'resolve'}, format='json').status_code
        == 409
    )


def test_L22_bad_notes_answer_400_and_unknown_ones_404(api, user, deal):
    assert _note(api, deal, {'kind': 'note', 'ref': 'intake:fein', 'text': ''}).status_code == 400
    assert _note(api, deal, {'kind': 'note', 'ref': 'intake:nope', 'text': 'x'}).status_code == 400
    assert _note(api, deal, {'kind': 'note', 'ref': 'intake:fein', 'text': 'x' * 1001}).status_code == 400
    assert _note(api, deal, {'kind': 'shout', 'ref': 'intake:fein', 'text': 'x'}).status_code == 400
    assert _note(api, deal, {'kind': 'reply', 'question_id': 'x', 'text': 'x'}).status_code == 404
    assert (
        api.patch(f'/api/deals/{deal.id}/review/notes/{2**64}/', {'action': 'resolve'}, format='json').status_code
        == 404
    )


def test_L5_the_board_lists_the_clients_open_questions_oldest_first(api, user, deal):
    from intake import form

    link, _token = _open_link(user, deal)
    questions.ask(link.id, [{'ref': 'intake:fein', 'text': 'x' * 200}, {'ref': 'intake:dba', 'text': 'And this?'}])
    board = api.get(f'/api/deals/{deal.id}/review/board/').json()
    assert board['questions_total'] == 2 and board['counts']['questions'] == 2
    first = board['questions'][0]
    assert (first['ref'], first['section'], first['who']) == ('intake:fein', 'Intake', 'Casey (synthetic)')
    assert first['where'] == form.BY_KEY['fein']['label'] and len(first['excerpt']) == 140
    assert first['fix'] == {'tab': 'review', 'view': 'request', 'pane': 'intake'}
