"""The portal's threads (plan.md §7.14 `questions/`, `seen/`; L81, L101, L103, L106; rule 11; slice 56): a client asks
about what their page asks and nothing else, a staff session cannot, a bad token is 404 and an ended link 410; the
follow-up cards carry only allowlisted keys, never a team note, a draft or a staff name; the page's stamp moves when
we write to them; their last look only moves forward."""

import pytest

from deals.models import Activity
from review.models import ClientLink, ReviewNote, Seen
from review.services import notes, questions, send, tray

from .portal_world import client, make_request, page, url, verified

pytestmark = pytest.mark.django_db

CANARY = 'Zqcanaryteam'
CARD_KEYS = {'ref', 'title', 'needs_answer', 'answered', 'question_open', 'new', 'replied', 'thread'}
ENTRY_KEYS = {'who', 'kind', 'text', 'plain', 'at'}


def _sent(user, deal, asks=None, **kwargs):
    link, token, pin = make_request(
        user, deal, asks or {'intake': {'scope': 'all'}, 'census': {'file': True}}, **kwargs
    )
    ClientLink.objects.filter(pk=link.pk).update(sent_at=link.created_at)
    return link, token, pin


def _ask(api, token, questions, **headers):
    return api.post(url(token, 'questions/'), {'questions': questions}, format='json', **headers)


def test_L101_a_client_asks_about_what_their_page_asks(user, deal):
    link, token, _pin = _sent(user, deal)
    api = client()
    answer = _ask(api, token, [{'ref': 'intake:fein', 'text': 'Which number?'}, {'ref': 'census:file', 'text': 'CSV?'}])
    assert answer.status_code == 201, answer.content
    cards = answer.json()['follow_ups']
    assert {card['ref'] for card in cards} == {'intake:fein', 'census:file'}
    assert all(card['question_open'] and card['thread'][0]['who'] == 'you' for card in cards)
    made = ReviewNote.objects.filter(deal=deal, kind='question')
    assert made.count() == 2 and {note.link_id for note in made} == {link.id}
    row = Activity.objects.get(deal=deal, action='client_asked')
    assert row.actor_kind == 'client' and 'Which number' not in str(row.changes) + row.summary
    for header in ('Cache-Control', 'Referrer-Policy', 'X-Robots-Tag'):
        assert answer.has_header(header)


def test_L101_a_question_off_the_page_or_too_long_refuses_the_whole_post(user, deal):
    _link, token, _pin = _sent(user, deal, {'intake': {'scope': 'selected', 'keys': ['fein']}})
    api = client()
    for sent in (
        [{'ref': 'intake:fein', 'text': 'ok'}, {'ref': 'intake:dba', 'text': 'not on this page'}],
        [{'ref': 'intake:fein', 'text': 'x' * 1001}],
        [{'ref': 'intake:fein', 'text': ''}],
        [{'ref': 'intake:fein', 'text': 'q'}] * 21,
        'everything',
    ):
        assert _ask(api, token, sent).status_code == 400
    assert not ReviewNote.objects.filter(deal=deal).exists()


def test_rule_11_questions_and_seen_refuse_staff_bad_tokens_ended_links_and_a_missing_pin(api, user, deal):
    link, token, _pin = _sent(user, deal)
    question = [{'ref': 'intake:fein', 'text': 'Hello'}]
    assert _ask(api, token, question).status_code == 403  # a staff session
    assert api.post(url(token, 'seen/'), {}, format='json').status_code == 403
    assert _ask(client(), 'x' * 43, question).status_code == 404
    ClientLink.objects.filter(pk=link.pk).update(revoked_at=link.created_at)
    assert _ask(client(), token, question).status_code == 410
    member_ask = {'census': {'scope': 'all'}}
    _plink, ptoken, pin = _sent(user, deal, member_ask, people=[{'name': 'Pat'}])
    anon = client()
    assert _ask(anon, ptoken, [{'ref': 'census:file', 'text': 'x'}]).status_code == 428
    headers = verified(anon, ptoken, pin)
    assert anon.post(url(ptoken, 'seen/'), {}, format='json', **headers).status_code == 200
    assert not ReviewNote.objects.filter(deal=deal).exists()


def test_L108_the_cards_carry_only_allowlisted_keys_never_a_team_note_or_a_draft(user, deal):
    _link, token, _pin = _sent(user, deal)
    notes.add(user, deal.id, 'intake:fein', CANARY, audience='team')
    tray.ask(user, deal.id, ['intake:dba'], kind='sendback', text=CANARY)  # still in the tray
    tray.ask(user, deal.id, ['intake:website'], kind='sendback', text='Please check')
    send.send(user, deal.id, ids=[ReviewNote.objects.get(key='website').id])
    body = page(client(), token)
    assert CANARY not in body.content.decode() and user.username not in body.content.decode()
    (card,) = body.json()['follow_ups']
    assert set(card) == CARD_KEYS and set(card['thread'][0]) == ENTRY_KEYS
    assert (card['ref'], card['needs_answer'], card['thread'][0]['who']) == ('intake:website', True, 'agency')


def test_L66_a_blank_link_sees_only_its_own_questions(user, deal):
    own, own_token, _pin = _sent(user, deal, blank=True, people=[{'name': 'A'}, {'name': 'B'}])
    sibling = ClientLink.objects.filter(request_id=own.request_id).exclude(pk=own.pk).get()
    ClientLink.objects.filter(pk=sibling.pk).update(sent_at=sibling.created_at)
    questions.ask(sibling.id, [{'ref': 'intake:fein', 'text': 'From the colleague'}])
    assert page(client(), own_token).json()['follow_ups'] == []


def test_L103_the_stamp_moves_when_we_write_and_seen_only_moves_forward(user, deal):
    link, token, _pin = _sent(user, deal)
    api = client()
    before = api.get(url(token, 'stamp/')).json()['form_stamp']
    (question,) = questions.ask(link.id, [{'ref': 'intake:fein', 'text': 'Which?'}])
    notes.reply(user, deal.id, question.id, 'The nine digits on your IRS letter.')
    assert api.get(url(token, 'stamp/')).json()['form_stamp'] != before
    card = page(api, token).json()['follow_ups'][0]
    assert card['new'] and card['replied']
    first = api.post(url(token, 'seen/'), {}, format='json')
    assert first.status_code == 200
    stamp = Seen.objects.get(link=link).seen_at
    api.post(url(token, 'seen/'), {}, format='json')
    assert Seen.objects.get(link=link).seen_at >= stamp
    assert not page(api, token).json()['follow_ups'][0]['new']
