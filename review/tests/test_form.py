"""The Ask card's Update link (plan.md §5.8, §7.13 `POST review/requests/{rid}/form/`; L36, L42, L59, L64; Q.9 row 57,
done when "the Ask card changes an open link"): one locked write that changes what an open link asks — removals, the
level, the drafts, then each person's settings — and its dry run, which writes nothing."""

from datetime import timedelta

import pytest
from django.contrib.auth.hashers import check_password
from django.db import connection
from django.test.utils import CaptureQueriesContext

from deals import clock
from deals.models import Activity
from review.models import ClientLink, ClientRequest, ReviewNote
from review.services import form, tray

from .portal_world import client, field, make_request, page, person

pytestmark = pytest.mark.django_db

INTAKE = {'intake': {'scope': 'selected', 'keys': ['fein', 'dba'], 'blocks': []}}


def url(deal, request_id, dry=False):
    return f'/api/deals/{deal.id}/review/requests/{request_id}/form/' + ('?dry_run=1' if dry else '')


def sent(link):
    ClientLink.objects.filter(pk=link.pk).update(sent_at=clock.now())
    return link


def test_L42_done_when_the_ask_card_changes_an_open_link(api, user, deal):
    link, token, _pin = make_request(user, deal, INTAKE)
    sent(link)
    before = ClientRequest.objects.get(pk=link.request_id).form_version
    draft = tray.ask(user, deal.id, ['intake:website'], request_id=link.request_id).drafts[0]
    body = {'ids': [draft.id], 'off': {'refs': ['intake:dba']}, 'on': {'census_file': True}}
    answer = api.post(url(deal, link.request_id), body, format='json')
    assert answer.status_code == 200, answer.content
    request = ClientRequest.objects.get(pk=link.request_id)
    assert request.asks['intake']['keys'] == ['fein', 'website'] and request.asks['census']['file'] is True
    assert request.form_version == before + 1 and answer.json()['sent'] == 1
    assert ReviewNote.objects.get(pk=draft.id).sent_at is not None
    shown = page(client(), token).json()
    assert field(shown, 'website') and not field(shown, 'dba') and shown['census_file'] is not None
    row = Activity.objects.get(pk=answer.json()['activity_id'])
    assert row.area == 'review' and row.action == 'updated' and not row.revertible


def test_L42_the_dry_run_says_what_changes_and_writes_nothing(api, user, deal):
    link, _token, _pin = make_request(user, deal, INTAKE)
    body = {'off': {'refs': ['intake:dba']}, 'on': {'intake': 'missing'}}
    with CaptureQueriesContext(connection) as queries:
        answer = api.post(url(deal, link.request_id, dry=True), body, format='json')
    assert answer.status_code == 200, answer.content
    found = answer.json()
    assert found['refused'] == '' and 'Intake gaps' in found['adds'] and '2 intake questions' in found['offs']
    assert found['numbers']['intake'] > 0 and found['floor']['level'] == 'link'
    assert not [q for q in queries.captured_queries if q['sql'].startswith(('INSERT', 'UPDATE', 'DELETE'))]
    assert ClientRequest.objects.get(pk=link.request_id).asks['intake']['keys'] == ['fein', 'dba']


def test_L42_L64_census_on_a_private_link_waits_for_a_person_to_raise_it(api, user, deal):
    link, token, _pin = make_request(user, deal, INTAKE)
    sent(link)
    body = {'on': {'census': 'missing'}}
    refused = api.post(url(deal, link.request_id), body, format='json')
    assert refused.status_code == 409 and refused.json()['needs_level'] == 'pin'
    dry = api.post(url(deal, link.request_id, dry=True), body, format='json').json()
    assert dry['owed'] and dry['floor']['level'] == 'pin' and 'Census needs at least a PIN' in dry['refused']
    assert ClientRequest.objects.get(pk=link.request_id).asks['census']['scope'] == 'none'
    raised = api.post(url(deal, link.request_id), {**body, 'security': 'pin'}, format='json')
    assert raised.status_code == 200, raised.content
    (pin,) = raised.json()['pins']
    fresh = ClientLink.objects.get(pk=link.pk)
    assert fresh.security == 'pin' and check_password(pin['pin'], fresh.pin_hash)
    assert page(client(), token).status_code == 428  # the next open asks for the PIN


def test_L64_a_level_falls_once_what_needed_it_comes_off(api, user, deal):
    link, _token, _pin = make_request(user, deal, {'census': {'scope': 'missing'}}, security='pin')
    early = api.post(url(deal, link.request_id), {'security': 'link'}, format='json')
    assert early.status_code == 409
    lowered = api.post(url(deal, link.request_id), {'security': 'link', 'off': {'parts': ['census']},
                                                     'on': {'census_file': True}}, format='json')  # fmt: skip
    assert lowered.status_code == 200, lowered.content
    fresh = ClientLink.objects.get(pk=link.pk)
    assert (fresh.security, fresh.pin_hash) == ('link', '')


def test_L59_a_question_a_scope_carries_is_refused_by_name(api, user, deal):
    link, _token, _pin = make_request(user, deal, {'intake': {'scope': 'all'}})
    answer = api.post(url(deal, link.request_id), {'off': {'refs': ['intake:fein']}}, format='json')
    assert answer.status_code == 409
    assert 'FEIN' in answer.json()['detail'] and 'the intake' in answer.json()['detail']


def test_L42_taking_an_ask_off_closes_what_went_out_on_it(api, user, deal):
    link, _token, _pin = make_request(user, deal, INTAKE)
    sent(link)
    draft = tray.ask(user, deal.id, ['intake:website'], request_id=link.request_id).drafts[0]
    api.post(url(deal, link.request_id), {'ids': [draft.id]}, format='json')
    answer = api.post(url(deal, link.request_id), {'off': {'refs': ['intake:website']}}, format='json')
    assert answer.status_code == 200 and answer.json()['closed'] == 1
    assert ReviewNote.objects.get(pk=draft.id).resolved_at is not None


def test_L39_settings_go_with_update_link_and_never_change_what_it_asks(api, user, deal):
    link, _token, _pin = make_request(user, deal, INTAKE)
    asks = ClientRequest.objects.get(pk=link.request_id).asks
    day = (clock.today() + timedelta(days=5)).isoformat()
    nudge = (clock.today() + timedelta(days=2)).isoformat()
    body = {'settings': {str(link.id): {'blank': True, 'expires_on': day, 'nudge_on': nudge}}, 'message': 'Thanks!'}
    answer = api.post(url(deal, link.request_id), body, format='json')
    assert answer.status_code == 200, answer.content
    fresh = ClientLink.objects.get(pk=link.pk)
    assert fresh.blank and not fresh.slides and clock.local(fresh.expires_at).date().isoformat() == day
    assert fresh.nudge['on'] == nudge and fresh.nudge['by'] == user.id
    request = ClientRequest.objects.get(pk=link.request_id)
    assert request.asks == asks and request.message == 'Thanks!'
    stranger = api.post(url(deal, link.request_id), {'settings': {'999999': {'blank': True}}}, format='json')
    assert stranger.status_code == 400


def test_L42_a_closed_request_or_a_lost_deal_refuses(api, user, deal):
    link, _token, _pin = make_request(user, deal, INTAKE)
    ClientRequest.objects.filter(pk=link.request_id).update(closed_at=clock.now())
    assert api.post(url(deal, link.request_id), {'on': {'census_file': True}}, format='json').status_code == 409


def test_Q3_update_link_locks_the_deal_then_the_request_then_its_links(user, deal):
    link, _token, _pin = make_request(user, deal, INTAKE, people=[{'name': 'Dana'}, {'name': 'Lee'}])
    with CaptureQueriesContext(connection) as queries:
        form.update(user, deal.id, link.request_id, {'on': {'census_file': True}})
    locks = [q['sql'] for q in queries.captured_queries if 'FOR UPDATE' in q['sql']]
    assert '"deals_deal"' in locks[0] and '"review_clientrequest"' in locks[1] and '"review_clientlink"' in locks[2]


def test_L42_a_census_value_drafted_for_a_pin_link_goes_on(api, user, deal):
    avery = person(user, deal, 'Avery', 'Synthetic')
    link, _token, _pin = make_request(user, deal, {'census': {'scope': 'missing'}}, security='pin')
    draft = tray.ask(user, deal.id, [f'census:{avery.id}:dob'], request_id=link.request_id).drafts[0]
    answer = api.post(url(deal, link.request_id), {'ids': [draft.id]}, format='json')
    assert answer.status_code == 200, answer.content
    assert [avery.id, 'dob'] in ClientRequest.objects.get(pk=link.request_id).asks['census']['cells']


def test_L42_the_request_page_names_what_the_picked_link_carries(api, user, deal):
    link, _token, _pin = make_request(user, deal, INTAKE)
    draft = tray.ask(user, deal.id, ['intake:website'], request_id=link.request_id).drafts[0]
    answer = api.get(f'/api/deals/{deal.id}/review/request/', {'pane': 'intake', 'request': link.request_id})
    assert answer.status_code == 200, answer.content
    target = answer.json()['target']
    assert target['request_id'] == link.request_id and target['link_ids'] == [link.id]
    assert {'intake:fein', 'intake:dba'} <= set(target['on_link']) and target['drafted'] == {'intake:website': draft.id}
    assert target['parts']['intake'] == 'selected' and target['security'] == 'link'
    assert api.get(f'/api/deals/{deal.id}/review/request/', {'request': 'x'}).status_code == 400
    assert api.get(f'/api/deals/{deal.id}/review/request/', {'request': 99999999}).json()['target'] is None
