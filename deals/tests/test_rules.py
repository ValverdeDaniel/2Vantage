"""deals.rules (plan.md §5.1, O.3.7): what a lost deal refuses, the deal type and the agent's name. Table-driven."""

from types import SimpleNamespace

import pytest

from conftest import make_deal
from deals import rules
from deals.models import AgencySettings

EVERY_ACTION = [
    ('send_to_market', 'This deal is marked lost — reopen it before sending it to market.'),
    ('sign', 'This deal is marked lost — reopen it before signing.'),
    ('mark_sold', 'This deal is marked lost — reopen it before selling a plan.'),
    ('book', 'This deal is marked lost — reopen it before booking its commission.'),
    ('portal_write', 'This link is no longer active.'),
    ('client_ask', 'This deal is marked lost — reopen it before asking the client for anything.'),
    (
        'ai_land',
        'This deal is marked lost, so the read was saved for review instead of applied. Reopen the deal to use it.',
    ),
    ('convert', 'This deal is marked lost — reopen it before converting the client.'),
]


def deal(stage='quoting', opened_as='prospect', owner=None):
    return SimpleNamespace(stage=stage, opened_as=opened_as, owner=owner)


@pytest.mark.parametrize('action, sentence', EVERY_ACTION)
def test_A19_a_lost_deal_refuses_each_action_with_its_sentence(action, sentence):
    assert rules.refuses(deal('lost'), action) == sentence


@pytest.mark.parametrize('stage', ['intake', 'quoting', 'proposal', 'sold'])
@pytest.mark.parametrize('action', rules.ACTIONS)
def test_A19_an_open_deal_refuses_nothing(stage, action):
    assert rules.refuses(deal(stage), action) is None


def test_A19_the_table_covers_every_action_and_an_unknown_one_is_an_error():
    assert {action for action, _ in EVERY_ACTION} == set(rules.ACTIONS)
    with pytest.raises(ValueError):
        rules.refuses(deal('lost'), 'edit_notes')  # internal edits are not on the list: lost is a label, not a lock


def test_CL4_convert_is_refused_while_any_of_the_clients_deals_is_lost():
    assert rules.convert_refusal([]) is None
    assert rules.convert_refusal([deal('proposal')]) is None
    assert rules.convert_refusal([deal('proposal'), deal('lost')]) == dict(EVERY_ACTION)['convert']


@pytest.mark.parametrize(
    'opened_as, deal_type, label',
    [
        ('prospect', 'new_business', 'New business'),
        ('new_client', 'new_business', 'New business'),
        ('existing_client', 'renewal', 'Renewal'),
    ],
)
def test_M14_deal_type_is_renewal_only_for_a_deal_opened_for_an_existing_client(opened_as, deal_type, label):
    assert rules.deal_type(deal(opened_as=opened_as)) == deal_type
    assert rules.deal_type_label(deal(opened_as=opened_as)) == label


@pytest.mark.parametrize(
    'owner, producer, name',
    [
        (SimpleNamespace(get_full_name=lambda: 'Dana Lee', username='dana'), 'Pat Agency', 'Dana Lee'),
        (SimpleNamespace(get_full_name=lambda: '', username='dana'), 'Pat Agency', 'dana'),
        (None, 'Pat Agency', 'Pat Agency'),
        (None, '', ''),
    ],
)
def test_M27_agent_name_is_the_owner_else_the_agency_producer(owner, producer, name):
    agency = AgencySettings(producer_name=producer)
    assert rules.agent_name(deal(owner=owner), agency) == name


def test_M27_agent_name_reads_the_agency_settings_when_not_given(user):
    AgencySettings.objects.create(producer_name='Pat Agency', producer_npn='1234567')
    unowned = make_deal(user)
    unowned.owner = None
    assert rules.agent_name(unowned) == 'Pat Agency'
