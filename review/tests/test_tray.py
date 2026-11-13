"""The request tray (plan.md §5.8, §7.13 `review/tray/`; L49–L53, L58; B7, B12; OQ87; Q.9 row 56: "two asks leave one
draft"; done when "asks gathered in the tray go out on one link"): asks wait in the tray, one draft per item, each
says where it goes, and sending puts them on the client's open link, or on one new link."""

from datetime import timedelta
from unittest import mock

import pytest

from deals import clock
from deals.models import Activity
from intake.services import update_answers
from review.models import ClientLink, ClientRequest, ReviewNote
from review.rules import tray as tray_rules
from review.services import send, tray

from .portal_world import client, field, make_request, page, person

pytestmark = pytest.mark.django_db

CANARY = 'Zqcanarynote'


def _tray(api, deal):
    answer = api.get(f'/api/deals/{deal.id}/review/tray/')
    assert answer.status_code == 200, answer.content
    return answer.json()


def _sent_request(user, deal, asks=None):
    link, token, _pin = make_request(user, deal, asks or {'intake': {'scope': 'required'}})
    ClientLink.objects.filter(pk=link.pk).update(sent_at=link.created_at)
    return link, token


def test_L51_B7_one_draft_per_item_and_asking_again_keeps_its_note(api, user, deal):
    body = {'refs': ['intake:fein'], 'text': 'Your FEIN, please.'}
    first = api.post(f'/api/deals/{deal.id}/review/tray/', body, format='json')
    assert first.status_code == 201, first.content
    again = api.post(f'/api/deals/{deal.id}/review/tray/', {'refs': ['intake:fein', 'doc:claims']}, format='json')
    body = again.json()
    assert body['tray']['count'] == 2 and body['added'] == 2
    drafts = ReviewNote.objects.filter(deal=deal, sent_at__isnull=True)
    assert drafts.count() == 2
    assert drafts.get(key='fein').text == 'Your FEIN, please.'  # a bulk ask with no note keeps the draft's own


def test_L51_a_ref_not_on_the_deal_refuses_the_whole_ask(api, user, deal):
    other = person(user, deal, 'Avery', 'Synthetic')
    answer = api.post(
        f'/api/deals/{deal.id}/review/tray/', {'refs': ['intake:fein', f'census:{other.id}:ssn']}, format='json'
    )
    assert answer.status_code == 400 and 'refs' in answer.json()
    assert not ReviewNote.objects.filter(deal=deal).exists()


def test_L51_B10_a_lost_deal_takes_no_ask(api, user, deal):
    deal.stage = 'lost'
    deal.save(update_fields=['stage'])
    answer = api.post(f'/api/deals/{deal.id}/review/tray/', {'refs': ['intake:fein']}, format='json')
    assert answer.status_code == 409
    assert not ReviewNote.objects.filter(deal=deal).exists()


def test_L49_L52_each_item_says_where_it_goes_or_why_it_cannot(api, user, deal):
    member = person(user, deal, 'Avery', 'Synthetic')
    tray.ask(user, deal.id, ['intake:fein', f'census:{member.id}:dob'])
    found = _tray(api, deal)
    assert {row['why'] for row in found['items']} == {tray_rules.NEEDS_LINK}
    assert sorted(found['needs_new']) == sorted(row['id'] for row in found['items'])
    _sent_request(user, deal)
    found = _tray(api, deal)
    by_ref = {row['ref']: row for row in found['items']}
    assert by_ref['intake:fein']['target']['names'] == ['Casey (synthetic)']
    assert by_ref['intake:fein']['target']['days_left'] >= 6
    assert by_ref[f'census:{member.id}:dob']['why'] == tray_rules.NEEDS_PIN  # a private link takes no census values
    assert by_ref[f'census:{member.id}:dob']['title'] == 'Date of Birth — Avery Synthetic'
    assert found['links'][0]['names'] == ['Casey (synthetic)']


def test_L53_asks_gathered_in_the_tray_go_out_on_one_link(api, user, deal):
    update_answers(user, deal.id, {'website': 'https://example.test'})
    link, token = _sent_request(user, deal, {'intake': {'scope': 'required'}})
    request = link.request
    tray.ask(user, deal.id, ['intake:website'], kind='sendback', text='Is this still your site?')
    tray.ask(user, deal.id, ['doc:claims', 'census:file', 'intake:block:bor'])
    answer = api.post(f'/api/deals/{deal.id}/review/tray/send/', {}, format='json')
    assert answer.status_code == 200, answer.content
    body = answer.json()
    assert body['sent'] == 4 and body['waiting'] == [] and len(body['targets']) == 1
    assert body['targets'][0]['request_id'] == request.id and body['tray']['count'] == 0
    request = ClientRequest.objects.get(pk=request.id)
    assert request.form_version == 2
    assert request.asks['intake']['keys'] == ['website'] and request.asks['intake']['blocks'] == ['bor']
    assert request.asks['documents']['slots'] == ['claims'] and request.asks['census']['file'] is True
    assert ReviewNote.objects.filter(deal=deal, request=request, sent_at__isnull=False).count() == 4
    portal = page(client(), token).json()
    website = field(portal, 'website')
    assert website['value'] == 'https://example.test' and website['locked'] is False  # the send-back reopens it
    assert [slot['slot'] for slot in portal['documents']] == ['claims'] and portal['census_file'] is not None
    cards = {card['ref']: card for card in portal['follow_ups']}
    assert cards['intake:website']['needs_answer'] and cards['intake:website']['thread'][0]['who'] == 'agency'
    assert 'doc:claims' not in cards  # an ask with no words of its own is the form asking more
    rail = {item['key']: item for item in portal['checklist']['items']}
    assert (rail['followups']['filled'], rail['followups']['total'], rail['followups']['done']) == (0, 1, False)


def test_L53_with_no_open_link_choose_who_makes_one_new_link_for_the_tray(api, user, deal):
    tray.ask(user, deal.id, ['intake:fein', 'doc:claims'])
    answer = api.post(f'/api/deals/{deal.id}/review/tray/send/', {'new': {'people': [{'name': 'Dana'}]}}, format='json')
    assert answer.status_code == 200, answer.content
    body = answer.json()
    assert body['sent'] == 2 and len(body['links']) == 1 and body['links'][0]['path'].startswith('/portal/')
    made = ClientRequest.objects.get(pk=body['request']['id'])
    assert made.asks['intake'] == {'scope': 'selected', 'keys': ['fein'], 'blocks': []}
    assert made.asks['documents']['slots'] == ['claims']
    assert not ReviewNote.objects.filter(deal=deal, sent_at__isnull=True).exists()


def test_L52_B18_a_census_value_waits_for_a_pin_link_and_says_why(user, deal):
    member = person(user, deal, 'Avery', 'Synthetic')
    _sent_request(user, deal)
    tray.ask(user, deal.id, [f'census:{member.id}:dob', 'intake:fein'])
    done = send.send(user, deal.id)
    assert done.sent == 1 and len(done.waiting) == 1
    assert list(done.whys.values()) == [tray_rules.NEEDS_PIN]
    pinned = send.send(user, deal.id, new={'people': [{'name': 'Dana'}]})
    assert pinned.created.links[0][0].security == 'pin' and pinned.created.links[0][2]  # its PIN, shown once


def test_L58_sending_brings_a_lapsed_link_back_within_its_ceiling(user, deal):
    link, _token = _sent_request(user, deal)
    ran_out = link.created_at + timedelta(days=1)
    ClientLink.objects.filter(pk=link.pk).update(expires_at=ran_out)
    later = clock.now() + timedelta(days=3)
    with mock.patch.object(clock, 'now', return_value=later):
        tray.ask(user, deal.id, ['intake:fein'])
        done = send.send(user, deal.id)
    assert done.sent == 1
    assert ClientLink.objects.get(pk=link.pk).expires_at > later + timedelta(days=6)


def test_L51_remove_takes_out_drafts_only_and_activity_never_holds_a_note(api, user, deal):
    _sent_request(user, deal)
    kept = tray.ask(user, deal.id, ['doc:claims'], text=CANARY).drafts[0]
    send.send(user, deal.id)
    draft = tray.ask(user, deal.id, ['intake:fein'], text=CANARY).drafts[0]
    answer = api.post(f'/api/deals/{deal.id}/review/tray/remove/', {'ids': [draft.id, kept.id]}, format='json')
    assert answer.json()['removed'] == [draft.id]
    assert ReviewNote.objects.filter(pk=kept.id).exists() and not ReviewNote.objects.filter(pk=draft.id).exists()
    assert CANARY not in str(list(Activity.objects.filter(deal=deal).values('summary', 'changes')))
    assert api.delete(f'/api/deals/{deal.id}/review/notes/{kept.id}/').status_code == 409


def test_L54_ask_census_asks_each_blank_in_the_columns_and_leaves_what_is_out(api, user, deal):
    person(user, deal, 'Avery', 'Synthetic')
    person(user, deal, 'Blake', 'Synthetic', dob='1980-01-02')
    body = {'census': {'columns': ['dob'], 'scope': 'blank'}}
    first = api.post(f'/api/deals/{deal.id}/review/tray/', body, format='json')
    assert first.status_code == 201 and first.json()['added'] == 1
    assert api.post(f'/api/deals/{deal.id}/review/tray/', body, format='json').json()['added'] == 0
    bad = api.post(f'/api/deals/{deal.id}/review/tray/', {'census': {'columns': ['ssn']}}, format='json')
    assert bad.status_code == 400
