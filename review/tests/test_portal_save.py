"""Save and Submit through a link (plan.md §5.8, §7.14; L.6 `portal/save`, L83–L90, L95–L98, L116; OQ84, OQ85;
Q.9 row 54): answers wait as pending entries and touch no stored value, all or nothing, only what the link asks,
unchanged slots write nothing, stale bases conflict while the same value twice does not, the slide on save, Submit's
stamps, and the key-only Activity that coalesces per link."""

from datetime import timedelta
from unittest import mock

import pytest

from census.models import CensusFacts, Member
from deals import clock
from deals.models import Activity, Contact
from deals.services import create_contact
from intake.models import CurrentCoverage, Intake
from intake.selectors import answers_of
from intake.services import create_coverage, update_answers

from .portal_world import cell, client, field, fresh, make_request, page, person, save, verified

pytestmark = pytest.mark.django_db

CANARY = 'Zqcanaryvalue'


def _opened(user, deal, asks, **kwargs):
    link, token, pin = make_request(user, deal, asks, **kwargs)
    api = client()
    headers = verified(api, token, pin) if pin else {}
    return link, token, api, headers, page(api, token, **headers).json()


def test_L85_OQ84_intake_answers_wait_and_never_touch_the_stored_values(user, deal):
    link, token, api, _h, body = _opened(user, deal, {'intake': {'scope': 'missing'}})
    base = field(body, 'fein')['base']
    answer = save(api, token, {'intake:fein': {'value': '123456789', 'base': base}})
    assert answer.status_code == 200, answer.content
    assert answer.json()['saved'] == ['intake:fein']
    intake = Intake.objects.get(deal=deal)
    entry = intake.client['fein']
    assert (entry['value'], entry['status'], entry['link']) == ('12-3456789', 'pending', link.id)
    assert 'fein' not in intake.answers and 'fein' not in intake.sources
    assert answers_of(deal, intake).get('fein') is None  # OQ85: what prints reads stored values only
    again = page(api, token).json()
    assert field(again, 'fein')['value'] == '12-3456789'
    assert fresh(link).last_saved_at is not None


def test_L95_all_or_nothing_a_refused_value_saves_nothing(user, deal):
    _link, token, api, _h, body = _opened(user, deal, {'intake': {'scope': 'missing'}})
    answers = {
        'intake:fein': {'value': '123456789', 'base': field(body, 'fein')['base']},
        'intake:years_in_business': {'value': 'many', 'base': field(body, 'years_in_business')['base']},
    }
    answer = save(api, token, answers)
    assert answer.status_code == 400
    assert set(answer.json()['answers']) == {'intake:years_in_business'}
    assert not Intake.objects.filter(deal=deal).exclude(client={}).exists()


def test_B43_a_ref_the_link_does_not_ask_refuses_the_save(user, deal):
    _link, token, api, _h, body = _opened(user, deal, {'intake': {'scope': 'selected', 'keys': ['fein']}})
    answer = save(api, token, {'intake:dba': {'value': 'Sneaky', 'base': ''}})
    assert answer.status_code == 400 and answer.json()['answers'] == {'intake:dba': 'This link does not ask that.'}
    other = person(user, deal, 'Other', 'Synthetic')
    assert save(api, token, {f'census:{other.id}:dob': {'value': '01/01/1980', 'base': ''}}).status_code == 400
    assert save(api, token, ['intake:fein']).status_code == 400
    assert not Intake.objects.filter(deal=deal).exclude(client={}).exists()


def test_L96_a_stale_base_conflicts_and_the_same_value_twice_does_not(user, deal):
    rules = {'intake': {'scope': 'selected', 'keys': ['fein', 'dba']}}
    _link, token, api, _h, body = _opened(user, deal, rules)
    old_base = field(body, 'fein')['base']
    assert save(api, token, {'intake:fein': {'value': '11-1111111', 'base': old_base}}).status_code == 200
    stale = save(api, token, {'intake:fein': {'value': '22-2222222', 'base': old_base}})
    assert stale.status_code == 409
    conflict = stale.json()['conflicts'][0]
    assert (conflict['ref'], conflict['theirs']) == ('intake:fein', '11-1111111') and conflict['base']
    assert Intake.objects.get(deal=deal).client['fein']['value'] == '11-1111111'
    same = save(api, token, {'intake:fein': {'value': '11-1111111', 'base': old_base}})
    assert same.status_code == 200 and same.json()['saved'] == []
    both = save(api, token, {'intake:dba': {'value': 'Ok', 'base': field(body, 'dba')['base']},
                             'intake:fein': {'value': '33-3333333', 'base': old_base}})  # fmt: skip
    assert both.status_code == 409
    assert 'dba' not in Intake.objects.get(deal=deal).client  # all or nothing


def test_L95_an_unchanged_answer_writes_nothing_and_stamps_nothing(user, deal):
    update_answers(user, deal.id, {'dba': 'Example Trading'})
    link, token, api, _h, body = _opened(user, deal, {'intake': {'scope': 'all'}})
    answer = save(api, token, {'intake:dba': {'value': 'Example Trading', 'base': field(body, 'dba')['base']}})
    assert answer.json()['saved'] == []
    assert fresh(link).last_saved_at is None
    assert not Activity.objects.filter(action='client_saved').exists()


def test_L62_a_save_slides_the_expiry_at_most_once_a_day(user, deal):
    link, token, api, _h, body = _opened(user, deal, {'intake': {'scope': 'missing'}})
    first_expiry = fresh(link).expires_at
    later = clock.now() + timedelta(days=3)
    with mock.patch.object(clock, 'now', return_value=later):
        save(api, token, {'intake:fein': {'value': '123456789', 'base': field(body, 'fein')['base']}})
    slid = fresh(link).expires_at
    assert slid > first_expiry and slid <= fresh(link).ceiling_at


def test_L116_saves_coalesce_per_link_key_only_with_no_values(user, deal):
    link, token, api, _h, body = _opened(user, deal, {'intake': {'scope': 'missing'}})
    save(api, token, {'intake:dba': {'value': CANARY, 'base': field(body, 'dba')['base']}})
    save(api, token, {'intake:fein': {'value': '123456789', 'base': field(body, 'fein')['base']}})
    rows = Activity.objects.filter(action='client_saved')
    assert rows.count() == 1
    row = rows.get()
    assert row.actor_id is None and row.actor_kind == 'client' and row.summary == 'Client saved 2 answers'
    assert row.changes == [{'t': f'link:{link.id}', 'k': ['intake:dba', 'intake:fein']}]
    assert CANARY not in str(list(Activity.objects.values()))


def test_OQ84_contacts_coverage_and_lines_wait_for_a_person(user, deal):
    create_contact(user, deal.client_id, role='hr_admin', name='Riley Example', email='riley@example.test')
    create_coverage(user, deal.id, {'line': 'medical', 'carrier': 'Old Carrier', 'in_force': True})
    asks = {'intake': {'scope': 'selected', 'keys': ['fein'], 'blocks': ['contacts', 'coverage', 'lines']}}
    _link, token, api, _h, body = _opened(user, deal, asks)
    blocks = body['intake']['blocks']
    assert blocks['contacts']['value'][0]['name'] == 'Riley Example'
    assert 'commission' not in str(blocks['coverage']) and 'on_proposal' not in str(blocks['coverage'])
    contacts = [*blocks['contacts']['value'], {'role': 'owner', 'name': 'Jordan Example', 'email': 'j@example.test'}]
    coverage = [{**blocks['coverage']['value'][0], 'carrier': 'New Carrier'}]
    answer = save(api, token, {
        'intake:block:contacts': {'value': contacts, 'base': blocks['contacts']['base']},
        'intake:block:coverage': {'value': coverage, 'base': blocks['coverage']['base']},
        'intake:block:lines': {'value': ['medical', 'dental', 'std'], 'base': blocks['lines']['base']},
    })  # fmt: skip
    assert answer.status_code == 200, answer.content
    assert Contact.objects.filter(client_id=deal.client_id).count() == 1
    assert CurrentCoverage.objects.get(deal=deal).carrier == 'Old Carrier'
    deal.refresh_from_db()
    assert 'std' not in deal.requested_lines
    waiting = Intake.objects.get(deal=deal).client
    assert waiting['block:lines']['value'] == ['medical', 'dental', 'std']
    assert waiting['block:contacts']['status'] == 'pending'


def test_C35_census_answers_wait_with_their_prior_and_rollups_read_stored_values(user, deal):
    member = person(user, deal, 'Avery', 'Synthetic', zip='33101')
    _link, token, api, headers, body = _opened(user, deal, {'census': {'scope': 'all'}})
    before = CensusFacts.objects.get(deal=deal).rollup
    answers = {
        f'census:{member.id}:zip': {'value': '33602', 'base': cell(body, member.id, 'zip')['base']},
        f'census:{member.id}:dob': {'value': '1/2/1985', 'base': cell(body, member.id, 'dob')['base']},
    }
    answer = save(api, token, answers, **headers)
    assert answer.status_code == 200, answer.content
    stored = Member.objects.get(pk=member.id)
    assert stored.values['zip'] == '33101' and 'dob' not in stored.values
    assert stored.client['zip']['prior'] == '33101' and stored.client['dob']['value'] == '1985-01-02'
    facts = CensusFacts.objects.get(deal=deal)
    assert facts.pending_answers == 2 and facts.rollup == before
    shown = page(api, token, **headers).json()
    assert cell(shown, member.id, 'dob')['value'] == '01/02/1985'


def test_OQ16_an_ssn_is_never_taken_on_a_link(user, deal):
    member = person(user, deal, 'Avery', 'Synthetic')
    _link, token, api, headers, _body = _opened(user, deal, {'census': {'scope': 'all'}})
    answer = save(api, token, {f'census:{member.id}:ssn': {'value': '123-45-6789', 'base': ''}}, **headers)
    assert answer.status_code == 400
    assert Member.objects.get(pk=member.id).client == {}


def test_L98_submit_keeps_the_first_submission_and_attests_the_form_once(user, deal):
    link, token, api, _h, body = _opened(user, deal, {'intake': {'scope': 'missing'}})
    first = api.post(f'/api/portal/{token}/submit/', {'answers': {}}, format='json')
    assert first.status_code == 200
    stamped = fresh(link)
    expires = stamped.expires_at
    later = clock.now() + timedelta(days=2)
    with mock.patch.object(clock, 'now', return_value=later):
        again = api.post(f'/api/portal/{token}/submit/', {'answers': {}}, format='json')
    assert again.status_code == 200
    final = fresh(link)
    assert final.first_submitted_at == stamped.first_submitted_at and final.submitted_at > stamped.submitted_at
    assert final.attested_form_version == link.request.form_version
    assert final.expires_at == expires  # submitting never slides it (L62)
    assert Activity.objects.filter(action='client_submitted', actor_kind='client').count() == 2


def test_L70_a_link_closed_meanwhile_refuses_the_save(user, deal):
    from review import services

    link, token, api, _h, body = _opened(user, deal, {'intake': {'scope': 'missing'}})
    services.close(user, link.request_id, 'cancelled')
    answer = save(api, token, {'intake:fein': {'value': '123456789', 'base': field(body, 'fein')['base']}})
    assert answer.status_code == 410
    assert not Intake.objects.filter(deal=deal).exclude(client={}).exists()
