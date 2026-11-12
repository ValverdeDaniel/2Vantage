"""The client's contacts and the one primary-contact rule (plan.md §4.6, §6.2, §7.3; B13, M30, OQ106, M.5 B32).
Activity keeps a contact's keys, never a person's details (§3.8)."""

from types import SimpleNamespace

import pytest

from contract_helpers import write_path_contract
from deals import contacts, services
from deals.models import Activity, Contact


def person(role, is_primary=False, name=''):
    return SimpleNamespace(role=role, is_primary=is_primary, name=name)


@pytest.mark.parametrize(
    'people, expected',
    [
        ([person('prior_broker', True), person('billing')], 1),  # a prior broker is never primary
        ([person('owner'), person('benefit_admin')], 1),  # a benefit administrator can be
        ([person('owner'), person('hr_admin'), person('benefit_admin')], 1),
        ([person('owner'), person('billing', True)], 1),  # the one marked primary wins
        ([person('payroll_contact'), person('owner')], 0),  # else the first client-side contact
        ([person('prior_broker')], None),
        ([], None),
    ],
)
def test_M30_the_primary_contact_rule(people, expected):
    main = contacts.primary(people)
    assert main is (None if expected is None else people[expected])


def test_OQ106_seven_roles_without_a_partner_agent():
    keys = [role['key'] for role in contacts.meta()]
    assert 'partner_agent' not in keys and 'hr_admin' in keys and len(keys) == len(set(keys))
    assert [role['key'] for role in contacts.meta() if not role['client_side']] == ['prior_broker']


def test_M30_the_first_edit_creates_an_hr_admin_who_is_the_primary(api, deal):
    answer = api.post(f'/api/clients/{deal.client_id}/contacts/', {'name': 'Rae Example'}, format='json')
    assert answer.status_code == 201 and answer.json()['role'] == 'hr_admin'
    listed = api.get(f'/api/clients/{deal.client_id}/contacts/').json()
    assert listed['primary_id'] == answer.json()['id']
    assert api.get(f'/api/clients/{deal.client_id}/').json()['primary_id'] == answer.json()['id']


@pytest.mark.parametrize(
    'body, field',
    [
        ({'email': 'not-an-address'}, 'email'),
        ({'role': 'partner_agent'}, 'role'),
        ({'role': 'prior_broker', 'is_primary': True}, 'is_primary'),
        ({'name': 'x' * 201}, 'name'),
    ],
)
def test_B13_a_bad_contact_answers_400(api, deal, body, field):
    answer = api.post(f'/api/clients/{deal.client_id}/contacts/', body, format='json')
    assert answer.status_code == 400 and field in answer.json()


def test_M30_marking_one_primary_clears_the_others(api, deal):
    url = f'/api/clients/{deal.client_id}/contacts/'
    first = api.post(url, {'name': 'One', 'is_primary': True}, format='json').json()
    second = api.post(url, {'name': 'Two', 'role': 'benefit_admin', 'is_primary': True}, format='json').json()
    assert api.get(url).json()['primary_id'] == second['id']
    api.patch(f'/api/contacts/{first["id"]}/', {'is_primary': True}, format='json')
    flags = dict(Contact.objects.filter(client_id=deal.client_id).values_list('id', 'is_primary'))
    assert flags == {first['id']: True, second['id']: False}


def test_B13_a_contact_is_edited_and_removed(api, deal):
    made = api.post(f'/api/clients/{deal.client_id}/contacts/', {'name': 'Rae', 'email': 'rae@example.com'}).json()
    edited = api.patch(f'/api/contacts/{made["id"]}/', {'phone': '555-0100', 'title': 'HR lead'}, format='json')
    assert edited.json()['phone'] == '555-0100' and edited.json()['email'] == 'rae@example.com'
    assert api.patch(f'/api/contacts/{made["id"]}/', {'email': 'bad'}, format='json').status_code == 400
    assert api.delete(f'/api/contacts/{made["id"]}/').status_code == 204
    assert api.delete(f'/api/contacts/{made["id"]}/').status_code == 404


def test_Q3_1_contact_rows_keep_keys_only_and_their_revert_is_refused(user, deal):
    contact = services.create_contact(user, deal.client_id, name='Rae Example', email='rae@example.com')
    write_path_contract(
        user,
        contact,
        lambda: services.update_contact(user, contact.id, name='Rae Q. Example'),
        lambda row: row.name,
        lambda: None,
        keys_only=True,
    )
    for row in Activity.objects.filter(deal=deal, area='contacts'):
        assert 'Rae' not in row.summary and 'Rae' not in str(row.changes)
