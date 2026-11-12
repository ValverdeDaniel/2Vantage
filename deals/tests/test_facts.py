"""The header's facts and owners (plan.md §6.2, §7.3; M27, M29, H22, J22; OQ45, OQ49): Potential deal size, Agent of
record, `set_owner`, and the deal type the builder's RENEWAL chip reads."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from conftest import make_client
from contract_helpers import write_path_contract
from deals import services
from deals.models import Activity, AgencySettings, Client, Deal


def patch(api, deal, **body):
    return api.patch(f'/api/deals/{deal.id}/', body, format='json')


@pytest.mark.parametrize(
    'typed, stored',
    [('$250,000', '250000.00'), ('1234.5', '1234.50'), (125000, '125000.00'), ('', None), (None, None)],
)
def test_M29_the_deal_size_strips_dollars_and_commas_and_blank_clears(api, deal, typed, stored):
    patch(api, deal, deal_size='999')
    answer = patch(api, deal, deal_size=typed)
    assert answer.status_code == 200 and answer.json()['deal_size'] == stored


@pytest.mark.parametrize('typed', ['about 250k', '-5', 'NaN', '1e20'])
def test_M29_a_deal_size_that_is_not_dollars_answers_400(api, deal, typed):
    answer = patch(api, deal, deal_size=typed)
    assert answer.status_code == 400 and 'deal_size' in answer.json()


def test_M29_the_deal_size_reaches_the_client_rows(api, deal):
    patch(api, deal, deal_size='$80,000')
    assert api.get('/api/clients/').json()['results'][0]['deal']['deal_size'] == '80000.00'


def test_M27_a_blank_agent_of_record_shows_the_owner_then_the_agency_producer(api, user, deal):
    header = patch(api, deal, agent_of_record='  Outside   Agent ').json()
    assert header['agent_of_record'] == 'Outside Agent' and header['agent_default'] == 'Dana'
    header = patch(api, deal, agent_of_record='', owner_id=None).json()
    assert header['agent_of_record'] == '' and header['agent_default'] == ''
    AgencySettings.objects.create(producer_name='Pat Agency')
    assert api.get(f'/api/deals/{deal.id}/').json()['agent_default'] == 'Pat Agency'


def test_M27_an_agent_of_record_over_200_characters_answers_400(api, deal):
    assert patch(api, deal, agent_of_record='x' * 201).status_code == 400


def test_Q3_1_the_deal_size_reverts_once_and_not_after_a_later_edit(user, deal):
    write_path_contract(
        user,
        deal,
        lambda: services.set_facts(user, deal.id, deal_size=Decimal('250000.00')),
        lambda row: row.deal_size,
        lambda: services.set_facts(user, deal.id, deal_size=Decimal('1.00')),
    )


def test_Q3_1_the_agent_of_record_reverts(user, deal):
    write_path_contract(
        user,
        deal,
        lambda: services.set_facts(user, deal.id, agent_of_record='Outside Agent'),
        lambda row: row.agent_of_record,
        lambda: services.set_facts(user, deal.id, agent_of_record='Another Agent'),
    )


def test_H22_set_owner_writes_one_row_and_reverts(user, deal):
    other = get_user_model().objects.create_user('lee', 'lee@example.com', 'pw-Example-1', first_name='Lee')
    write_path_contract(
        user,
        deal,
        lambda: services.set_owner(user, other, deal_id=deal.id),
        lambda row: row.owner_id,
        lambda: services.set_owner(user, None, deal_id=deal.id),
    )


def test_H22_set_owner_takes_a_clients_owner_too(user, deal):
    other = get_user_model().objects.create_user('lee', 'lee@example.com', 'pw-Example-1')
    assert services.set_owner(user, other, client_id=deal.client_id) == {'owner': [user.id, other.id]}
    assert Client.objects.get(pk=deal.client_id).owner_id == other.id
    row = Activity.objects.filter(area='deal_facts').latest('id')
    assert row.deal_id == deal.id and row.changes == [
        {'t': f'client:{deal.client_id}', 'k': {'owner': [user.id, other.id]}}
    ]
    with pytest.raises(ValueError):
        services.set_owner(user, other)


def test_H22_the_header_owner_picker_goes_through_set_owner(api, user, deal):
    patch(api, deal, owner_id=None)
    row = Activity.objects.filter(deal=deal).latest('id')
    assert (row.area, row.summary, row.changes) == (
        'deal_facts',
        'Changed the owner',
        [{'t': f'deal:{deal.id}', 'k': {'owner': [user.id, None]}}],
    )
    assert Deal.objects.get(pk=deal.id).owner_id is None


def test_J22_a_deal_opened_for_an_existing_client_is_a_renewal_and_a_prospects_is_not(api, user):
    _, renewal = make_client(user, name='Old Friend Co.', relationship='existing_client')
    _, new = make_client(user, name='Fresh Co.')
    assert api.get(f'/api/deals/{renewal.id}/').json()['deal_type'] == 'renewal'
    assert api.get(f'/api/deals/{new.id}/').json()['deal_type'] == 'new_business'


def test_J22_converting_a_prospect_keeps_its_deal_new_business(api, user):
    client, deal = make_client(user)
    services.set_status(user, client.id, 'new_client')
    assert api.get(f'/api/deals/{deal.id}/').json()['deal_type'] == 'new_business'
