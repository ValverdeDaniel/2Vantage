"""The page a link opens (plan.md §7.14, §8.20; L76–L94, L105, L108; Q.9 row 54): exactly the allowlisted keys, only
what the link asks, SSN never, a blank link's own answers only, the open recorded once by the client's GET alone, and
a lost deal still readable."""

from datetime import timedelta
from unittest import mock

import pytest

from deals import clock
from deals.models import Activity
from deals.services import mark_lost
from intake.services import update_answers
from review.portal import payload as portal_payload

from .portal_world import cell, client, field, fresh, make_request, page, person, save, verified

pytestmark = pytest.mark.django_db

INTAKE = {'intake': {'scope': 'missing'}}


def test_L76_the_page_carries_exactly_the_allowlisted_keys(user, deal):
    _link, token, _pin = make_request(user, deal, INTAKE)
    answer = page(client(), token)
    assert answer.status_code == 200
    body = answer.json()
    assert tuple(body) == portal_payload.KEYS
    assert set(body['agency']) == {'name', 'phone', 'email', 'color'}
    assert body['account_name'] == deal.client.name
    assert body['can_write'] is True and body['staff'] is False and body['preview'] is False


def test_B43_intake_shows_only_the_questions_the_link_asks(user, deal):
    update_answers(user, deal.id, {'legal_name': 'Example Co. LLC'})
    _link, token, _pin = make_request(user, deal, {'intake': {'scope': 'selected', 'keys': ['fein', 'dba']}})
    body = page(client(), token).json()
    keys = [entry['key'] for section in body['intake']['sections'] for entry in section['fields']]
    assert keys == ['dba', 'fein']
    assert field(body, 'legal_name') is None
    assert body['people'] == [] and body['documents'] == [] and body['census_file'] is None


def test_B43_a_typed_answer_is_on_file_and_locked_on_the_whole_form(user, deal):
    update_answers(user, deal.id, {'legal_name': 'Example Co. LLC'})
    _link, token, _pin = make_request(user, deal, {'intake': {'scope': 'all'}})
    body = page(client(), token).json()
    named = field(body, 'legal_name')
    assert (named['value'], named['locked']) == ('Example Co. LLC', True)
    assert field(body, 'fein')['locked'] is False


def test_OQ16_census_people_never_carry_ssn(user, deal):
    member = person(user, deal, 'Avery', 'Synthetic', ssn='123-45-6789', dob='')
    _link, token, pin = make_request(user, deal, {'census': {'scope': 'all'}})
    api = client()
    body = page(api, token, **verified(api, token, pin)).json()
    columns = {entry['column'] for entry in body['people'][0]['fields']}
    assert 'ssn' not in columns and 'subscriber_ssn' not in columns
    assert '6789' not in str(body)
    assert body['people'][0]['title'] == 'Avery Synthetic'
    assert cell(body, member.id, 'dob')['value'] == ''


def test_L66_a_blank_link_shows_only_its_own_answers(user, deal):
    update_answers(user, deal.id, {'dba': 'Example Trading'})
    rules = {'intake': {'scope': 'selected', 'keys': ['dba', 'fein']}}
    _link, token, _pin = make_request(user, deal, rules, blank=True)
    api = client()
    body = page(api, token).json()
    assert field(body, 'dba')['value'] == ''
    assert 'Example Trading' not in str(body)


def test_L79_the_clients_get_records_the_open_once_in_30_minutes(user, deal):
    link, token, _pin = make_request(user, deal, INTAKE)
    api = client()
    page(api, token)
    page(api, token, QUERY_STRING='refresh=1')
    page(api, token, QUERY_STRING='preview=1')
    stamped = fresh(link)
    assert stamped.open_count == 1 and stamped.opened_at is not None
    assert Activity.objects.filter(area='review', action='client_opened', actor_kind='client').count() == 1
    later = clock.now() + timedelta(minutes=31)
    with mock.patch.object(clock, 'now', return_value=later):
        page(api, token)
    again = fresh(link)
    assert again.open_count == 2 and again.opened_at == stamped.opened_at
    assert Activity.objects.filter(area='review', action='client_opened').count() == 1


def test_L78_a_staff_session_sees_the_page_records_no_open_and_cannot_write(user, deal, api):
    link, token, _pin = make_request(user, deal, INTAKE)
    answer = page(api, token)
    assert answer.status_code == 200 and answer.json()['staff'] is True and answer.json()['can_write'] is False
    assert fresh(link).open_count == 0
    refused = save(api, token, {'intake:fein': {'value': '12-3456789', 'base': ''}})
    assert refused.status_code == 403
    assert fresh(link).last_saved_at is None


def test_L105_a_lost_deal_stays_readable_and_its_writes_answer_410(user, deal):
    _link, token, _pin = make_request(user, deal, INTAKE)
    mark_lost(user, deal.id, reason='other')
    api = client()
    body = page(api, token)
    assert body.status_code == 200 and body.json()['can_write'] is False
    refused = save(api, token, {'intake:fein': {'value': '12-3456789', 'base': ''}})
    assert refused.status_code == 410
    assert refused.json()['agency']['name']
