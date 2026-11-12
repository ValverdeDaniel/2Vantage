"""Chat turns (plan.md §10.6; D7, D77–D79, D81, D83, D90, D91, D24, D105; slice 24), run inline with the fake client:
a scripted turn calls a test tool, reads its answer and replies. The tools of the apps to the right (set_board,
propose_changes, update_client_guidance) are tested in their own apps."""

import re

import pytest

from accounts.models import Profile
from ai import kinds, land, pricing, registry, services, tools
from ai.models import Chat, ChatMessage, DealAi, Job
from ai.registry import Tool
from ai.testing import text_block, tool_block, turn_key
from deals import activity

NOTE = 'Write the note "hello"'


def note_tool(turn, data):
    words = tools.text(data.get('words'), 'words', 60)
    if words == 'no':
        raise tools.ToolRefused('Not that one.')
    turn.add({'owner': 'testnote', 'op': 'note', 'new': words, 'label': f'Note {words}'})
    return f'Noted {words}.'


def revert_note(row, user):
    return [activity.change(f'deal:{row.deal_id}', {'note': ['hello', '']})]


def apply_note(user, deal, job, items):
    row = activity.record(
        deal,
        user,
        'testnote',
        'updated',
        'Wrote a note',
        changes=[activity.change(f'deal:{deal.id}', {'note': ['', 'hello']})],
    )
    return {'activity_ids': [row.id], 'plan_ids': [], 'areas': ['activity'], 'summary': 'wrote a note'}


@pytest.fixture
def note_owner():
    tool = Tool('write_note', 'testnote', 90, 'Write a note.', tools.schema({'words': {'type': 'string'}}), note_tool)
    registry.register_tool(tool)
    registry.register_turn_owner('testnote', apply_note, order=90)
    activity.reverters['testnote'] = revert_note
    yield
    registry.tools.pop('write_note')
    registry.turn_owners.pop('testnote')
    activity.reverters.pop('testnote')


@pytest.fixture
def direct(db):
    from django.contrib.auth import get_user_model

    person = get_user_model().objects.create_user('dee', 'dee@example.com', 'pw-Example-1')
    Profile.objects.create(user=person, claude_direct=True)
    return person


def script(fake, words, *rounds):
    for number, (blocks, extra) in enumerate(rounds, start=1):
        fake.record(turn_key(words, number), content=blocks, **extra)


def write_note(fake, words='hello'):
    script(
        fake,
        NOTE,
        ([text_block('Writing it.'), tool_block('write_note', {'words': words})], {}),
        ([text_block('I wrote the note.')], {}),
    )


def send(person, deal, text=NOTE, **options):
    chat, message, job = services.send_message(person, deal, text=text, **options)
    job.refresh_from_db()
    return chat, message, job


def test_D77_D90_a_turn_answers_in_the_chat_lane_and_its_reply_is_the_next_message(user, deal, fake_claude, note_owner):
    write_note(fake_claude)
    chat, message, job = send(user, deal, tab='advisor')
    assert (job.kind, job.lane, job.status) == (kinds.TURN, kinds.CHAT, kinds.DONE)
    assert job.chat_id == chat.id and message.job_id == job.id
    reply = ChatMessage.objects.get(chat=chat, role=ChatMessage.ASSISTANT)
    assert reply.text == 'I wrote the note.' and reply.job_id == job.id
    assert job.result['items'][0]['label'] == 'Note hello' and job.result['reply_id'] == reply.id
    assert job.cost_usd > 0 and job.usage['calls'] == 2  # every round priced (D90)
    sent = fake_claude.log[-1]['params']
    assert sent['tool_choice'] == {'type': 'auto'} and all(tool['strict'] for tool in sent['tools'])
    assert sent['thinking'] == {'type': 'adaptive'} and sent['output_config'] == {'effort': 'low'}
    assert 'temperature' not in sent


def test_D83_the_cache_holds_the_prompt_the_newest_message_and_the_last_answers(user, deal, fake_claude, note_owner):
    write_note(fake_claude)
    send(user, deal)
    second = fake_claude.log[-1]['params']
    marks = [
        block
        for message in second['messages']
        if isinstance(message['content'], list)
        for block in message['content']
        if 'cache_control' in block
    ]
    assert second['system'][0]['cache_control'] == {'type': 'ephemeral'}
    assert len(marks) == 2  # the newest message's end, then the last tool answer (4 breakpoints at most)
    assert second['messages'][-1]['content'][-1]['type'] == 'tool_result'
    first = fake_claude.log[0]['params']['messages'][-1]['content']
    assert first[-1]['text'] == f'dana: {NOTE}' or first[-1]['text'].endswith(NOTE)
    assert '<deal>' in first[-2]['text'] and '<plans>' in first[-2]['text']


def test_D71_a_producers_turn_waits_and_a_direct_persons_lands_with_undo(user, direct, deal, fake_claude, note_owner):
    write_note(fake_claude)
    _chat, _message, job = send(user, deal)
    assert (job.land, job.resolution) == (land.STAGED, '')
    applied, landed = services.apply(user, job.id)
    assert applied.resolution == 'applied' and landed['summary'] == 'Wrote a note'

    write_note(fake_claude)
    _chat, _message, job = send(direct, deal)
    assert (job.land, job.resolution) == (land.AUTO, 'applied') and job.result['landed']['auto']
    row = job.result['landed']['activity_ids'][0]
    undone, changed = services.undo(direct, job.id)
    assert changed and undone.resolution == 'undone'
    assert activity.Activity.objects.get(pk=row).reverted_at is not None


def test_D104_a_locked_table_holds_a_direct_persons_changes_for_review(direct, deal, fake_claude, note_owner):
    services.set_lock(direct, deal, True)
    write_note(fake_claude)
    _chat, _message, job = send(direct, deal)
    assert (job.land, job.wait_reason) == (land.STAGED, land.TURN_LOCKED)
    assert 'locked from Claude' in fake_claude.log[0]['params']['messages'][-1]['content'][-2]['text']


def test_D81_a_refused_tool_answers_claude_in_words(user, deal, fake_claude, note_owner):
    write_note(fake_claude, words='no')
    _chat, _message, job = send(user, deal)
    answer = fake_claude.log[-1]['params']['messages'][-1]['content'][0]
    assert answer == {
        'type': 'tool_result',
        'tool_use_id': 'toolu_write_note',
        'content': 'Not that one.',
        'is_error': True,
        'cache_control': {'type': 'ephemeral'},
    }
    assert job.result['items'] == []


def test_D81_string_tool_inputs_are_parsed():
    assert tools.integer('41', 'id') == 41 and tools.integer(41.0, 'id') == 41
    assert tools.number('$40,000', 'cap') == 40000 and tools.number('2,000.5', 'cap') == 2000.5
    assert tools.integers('[41, 42]', 'ids') == [41, 42] and tools.integers('41, 42', 'ids') == [41, 42]
    assert tools.objects('[{"a": 1}]', 'rules') == [{'a': 1}] and tools.boolean('true', 'on') is True
    with pytest.raises(tools.ToolRefused):
        tools.integer('forty', 'id')
    with pytest.raises(tools.ToolRefused):
        tools.number(True, 'cap')


def test_D83_a_turn_stops_after_eight_rounds(user, deal, fake_claude, note_owner):
    words = 'Keep going'
    for number in range(1, 9):
        fake_claude.record(
            turn_key(words, number), content=[tool_block('write_note', {'words': f'n{number}'}, f'toolu_{number}')]
        )
    _chat, _message, job = send(user, deal, text=words)
    assert job.result['rounds'] == 8 and len(job.result['items']) == 8
    assert 'used its 8 rounds' in ChatMessage.objects.get(job=job, role=ChatMessage.ASSISTANT).text


def test_D91_a_refused_round_tries_once_on_opus_for_a_direct_person_only(user, direct, deal, fake_claude, note_owner):
    words = 'Read this'
    fake_claude.record(turn_key(words, 1), content=[text_block('')], fault='refusal', fault_on=pricing.SONNET)
    fake_claude.record(turn_key(words, 2), content=[text_block('Here it is.')])
    _chat, _message, job = send(direct, deal, text=words)
    assert [entry['params']['model'] for entry in fake_claude.log] == [pricing.SONNET, pricing.OPUS]
    assert job.model == pricing.OPUS and ChatMessage.objects.get(job=job, role='assistant').text == 'Here it is.'

    fake_claude.log.clear()
    fake_claude.record(turn_key(words, 2), content=[text_block('Never sent.')])
    _chat, _message, job = send(user, deal, text=words)
    assert len(fake_claude.log) == 1 and 'declined' in ChatMessage.objects.get(job=job, role='assistant').text


def test_D24_D99_a_turn_past_the_deals_budget_asks_nothing_until_run_anyway(
    admin_user, user, deal, fake_claude, note_owner
):
    DealAi.objects.create(deal=deal, budget_usd=0)
    write_note(fake_claude)
    _chat, message, job = send(user, deal)
    assert (job.land, job.result['over']) == ('budget', 'deal') and not fake_claude.log
    with pytest.raises(activity.Refused):
        services.retry(user, job.id, budget_override=True)  # only admins and direct people run anyway
    again, created = services.retry(admin_user, job.id, budget_override=True)
    assert created and again.status == kinds.DONE and again.params['retry_of'] == job.id
    message.refresh_from_db()
    assert message.job_id == again.id and len(fake_claude.log) == 2


def test_D105_stop_mid_turn_keeps_what_claude_proposed_for_review(direct, deal, fake_claude, note_owner, monkeypatch):
    monkeypatch.setattr('ai.progress.BEAT_SECONDS', 0)
    words = 'Two notes'
    fake_claude.record(turn_key(words, 1), content=[tool_block('write_note', {'words': 'one'})])

    def press_stop():
        Job.objects.filter(kind=kinds.TURN).update(cancel_requested_at='2026-11-12T10:00:00Z')

    fake_claude.record(turn_key(words, 2), content=[text_block('Done')], during=press_stop)
    _chat, _message, job = send(direct, deal, text=words)
    assert (job.status, job.resolution, job.land) == (kinds.CANCELLED, kinds.STOPPED, land.STAGED)
    assert [item['new'] for item in job.result['items']] == ['one']
    assert ChatMessage.objects.get(job=job, role='assistant').text.startswith('Stopped')
    assert services.apply(direct, job.id)[1]['summary'] == 'Wrote a note'  # used by hand, as a read's change set


def test_D7_D79_chats_number_on_their_first_message_and_remember_thirty(user, deal, fake_claude, note_owner):
    for words in ('first', 'second', 'last'):
        fake_claude.record(turn_key(words, 1), content=[text_block('Fine.')])
    chat, _m, _j = send(user, deal, text='first')
    other, _m, _j = send(user, deal, text='second')
    assert (chat.number, other.number) == (1, 2) and DealAi.objects.get(deal=deal).next_chat == 3
    for n in range(35):
        ChatMessage.objects.create(chat=chat, role='user' if n % 2 else 'assistant', text=f'm{n}', author=user)
    fake_claude.log.clear()
    send(user, deal, text='last', chat_id=chat.id)
    sent = fake_claude.log[0]['params']['messages']
    said = ' '.join(m['content'] if isinstance(m['content'], str) else m['content'][-1]['text'] for m in sent)
    # the last 30 messages: m6 on (m6 itself, Claude's, cannot open a request), never m5 or before
    assert re.search(r'\bm7\b', said) and re.search(r'\bm34\b', said) and not re.search(r'\bm[0-6]\b', said)
    assert services.rename_chat(user, chat.id, '  Aetna  fixes ')[0].title == 'Aetna fixes'
    assert Chat.objects.get(pk=chat.id).title == 'Aetna fixes'
