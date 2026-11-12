"""The chat API and the deal's AI settings (plan.md §7.5; D7, D19, D25, D100, D104, OQ34; slice 24)."""

import pytest

from ai.models import DealAi
from ai.testing import text_block, turn_key
from deals.models import Activity
from documents.tests.helpers import stored


def test_D7_D25_a_message_starts_a_turn_and_the_chat_lists_both(api, user, deal, fake_claude):
    fake_claude.record(turn_key('Hello Claude', 1), content=[text_block('Hello Dana.')])
    sent = api.post(f'/api/deals/{deal.id}/ai/messages/', {'text': 'Hello Claude', 'tab': 'advisor'}, format='json')
    assert sent.status_code == 201
    body = sent.json()
    assert body['message']['text'] == 'Hello Claude' and body['job']['kind'] == 'turn'
    chats = api.get(f'/api/deals/{deal.id}/ai/chats/').json()
    assert chats['open'] == body['chat_id'] and chats['window'] == 30
    assert chats['chats'][0] | {'last_used_at': None, 'created_at': None} == {
        'id': body['chat_id'],
        'number': 1,
        'title': 'Chat 1',
        'named': False,
        'tab': 'advisor',
        'created_at': None,
        'last_used_at': None,
        'last_used_by': chats['chats'][0]['last_used_by'],
        'messages': 2,
    }
    page = api.get(f'/api/ai/chats/{body["chat_id"]}/messages/').json()
    assert [(m['role'], m['text']) for m in page['messages']] == [
        ('user', 'Hello Claude'),
        ('assistant', 'Hello Dana.'),
    ]
    assert page['messages'][1]['turn']['status'] == 'done' and page['more'] is False
    renamed = api.patch(f'/api/ai/chats/{body["chat_id"]}/', {'title': 'Greetings'}, format='json').json()
    assert renamed == {'id': body['chat_id'], 'title': 'Greetings', 'named': True}


@pytest.mark.parametrize(
    'body',
    [
        {'text': '   '},
        {'text': 'x' * 8001},
        {'text': 'Hi', 'chat_id': 'abc'},
        {'text': 'Hi', 'chat_id': 2**64},
        {'text': 'Hi', 'document_ids': ['x']},
        {'text': 'Hi', 'tab': 'nowhere'},
        {'text': 'Hi', 'board': ['not', 'an', 'object']},
    ],
)
def test_D19_a_message_is_checked_before_claude_is_asked(api, deal, fake_claude, body):
    assert api.post(f'/api/deals/{deal.id}/ai/messages/', body, format='json').status_code == 400
    assert fake_claude.log == []


def test_D82_D111_at_most_three_files_and_none_that_list_members(api, user, deal, fake_claude):
    files = [stored(user, deal, name=f'q{n}.pdf', kind='quote') for n in range(4)]
    census = stored(user, deal, name='people.pdf', kind='census')
    url = f'/api/deals/{deal.id}/ai/messages/'
    assert api.post(url, {'text': 'Hi', 'document_ids': [f.id for f in files]}, format='json').status_code == 400
    assert api.post(url, {'text': 'Hi', 'document_ids': [census.id]}, format='json').status_code == 400


def test_D9_opus_and_run_anyway_are_for_admins_and_direct_people(api, deal, fake_claude):
    url = f'/api/deals/{deal.id}/ai/messages/'
    assert api.post(url, {'text': 'Hi', 'model': 'claude-opus-5-5'}, format='json').status_code == 409
    assert api.post(url, {'text': 'Hi', 'budget_override': True}, format='json').status_code == 409


def test_D100_OQ34_only_an_admin_changes_a_deals_budget_and_undo_puts_it_back(api, admin_api, deal):
    url = f'/api/deals/{deal.id}/ai/'
    assert api.patch(url, {'budget_usd': '40'}, format='json').status_code == 403
    assert admin_api.patch(url, {'budget_usd': 'lots'}, format='json').status_code == 400
    body = admin_api.patch(url, {'budget_usd': '40'}, format='json').json()
    assert body['spend'] | {'usd': None} == {'usd': None, 'budget_usd': '40.00', 'own_budget': True}
    assert admin_api.patch(url, {'budget_usd': '40.00'}, format='json').json()['activity_ids'] == []
    row = Activity.objects.get(area='ai', action='budget')
    assert admin_api.post(f'/api/activity/{row.id}/revert/').status_code == 200
    assert DealAi.objects.get(deal=deal).budget_usd is None


def test_D104_F113_anyone_locks_the_table_and_the_state_says_who(api, user, deal):
    url = f'/api/deals/{deal.id}/ai/'
    assert api.patch(url, {'locked': 'yes'}, format='json').status_code == 400
    assert api.patch(url, {'nothing': 1}, format='json').status_code == 400
    body = api.patch(url, {'locked': True}, format='json').json()
    assert body['lock']['by']['id'] == user.id and len(body['activity_ids']) == 1
    assert api.patch(url, {'locked': True}, format='json').json()['activity_ids'] == []  # unchanged: no row
    row = Activity.objects.get(pk=body['activity_ids'][0])
    assert (row.action, row.changes[0]['k']) == ('locked', {'locked': [False, True]})
    assert api.post(f'/api/activity/{row.id}/revert/').status_code == 200
    assert api.get(url).json()['lock'] is None


def _queries(api, url):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as queries:
        assert api.get(url).status_code == 200
    return len(queries.captured_queries)


def test_Q3_chats_and_messages_read_the_same_queries_for_one_or_many(api, user, deal):
    from ai.models import Chat, ChatMessage, Job

    first = Chat.objects.create(deal=deal, number=1, created_by=user)
    job = Job.objects.create(deal=deal, lane='chat', kind='turn', created_by=user, chat=first)
    ChatMessage.objects.create(chat=first, role='user', text='one', author=user, job=job)
    lists, pages = (
        _queries(api, f'/api/deals/{deal.id}/ai/chats/'),
        _queries(api, f'/api/ai/chats/{first.id}/messages/'),
    )
    for n in range(2, 8):
        Chat.objects.create(deal=deal, number=n, created_by=user)
        ChatMessage.objects.create(chat=first, role='assistant', text=f'm{n}', job=job)
        ChatMessage.objects.create(chat=first, role='user', text=f'u{n}', author=user)
    assert _queries(api, f'/api/deals/{deal.id}/ai/chats/') == lists
    assert _queries(api, f'/api/ai/chats/{first.id}/messages/') == pages
