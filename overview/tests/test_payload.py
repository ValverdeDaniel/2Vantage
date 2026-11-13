"""`GET deals/{id}/overview/` on factory deals (plan.md §7.16, §8.6; M.6's payload tests; Q.9 row 62): every block on
an empty deal; the facts read where their owners wrote them; the deal type as M.6's test reads it after OQ2; Last
contact; the renewal-offer chip. Synthetic only."""

from datetime import timedelta

import pytest

from conftest import make_deal
from deals import clock, lifecycle
from deals.models import Activity, Note
from deals.services import add_note, create_contact, mark_lost, set_facts, set_status
from intake import services as intake_services
from intake.models import Intake
from quotes import services as quote_services
from review import services as review_services

pytestmark = pytest.mark.django_db

BLOCKS = {'deal_id', 'identity', 'client', 'renewal_offer', 'facts', 'tiles'}


def overview(api, deal):
    response = api.get(f'/api/deals/{deal.id}/overview/')
    assert response.status_code == 200, response.content
    return response.json()


def test_Q9_62_an_empty_deal_answers_every_block_and_creates_nothing(api, user):
    deal = make_deal(user, name='Empty Co. (synthetic)', requested_lines=())
    rows = Activity.objects.count()
    payload = overview(api, deal)
    assert set(payload) == BLOCKS and Activity.objects.count() == rows
    assert payload['identity'] == {
        'name': 'Empty Co. (synthetic)',
        'legal_name': '',
        'legal_name_default': 'Empty Co. (synthetic)',
        'type': 'new_business',
        'type_label': 'New business',
        'stage': 'intake',
        'open_days': 0,
        'renews': None,
        'owner': {'id': user.id, 'name': 'Dana'},
    }
    assert payload['client']['relationship'] == 'prospect' and payload['client']['on_book'] is False
    assert payload['client']['convert'] == {'allowed': True, 'sentence': ''}
    assert payload['renewal_offer'] is None
    facts = payload['facts']
    assert [facts[key] for key in ('fein', 'sic_code', 'situs_state', 'employee_count')] == ['', '', '', '']
    assert facts['carrier'] == {'value': '', 'from': None, 'coverage_id': None, 'editable': True}
    assert facts['agent_of_record'] == {'value': '', 'default': 'Dana'}
    assert facts['deal_size'] is None and facts['in_force'] == [] and facts['contact'] is None
    assert payload['tiles'] == {'plans_quoted': 0, 'last_contact_at': None, 'expected_revenue': None}
    assert not Intake.objects.filter(deal=deal).exists()  # the read made no Intake row (M.5 B34)


def test_M13_M25_M29_M30_the_facts_are_read_where_their_owners_wrote_them(api, user, deal):
    intake_services.update_answers(
        user, deal.id, {'legal_name': 'Example Holdings LLC', 'fein': '12-3456789', 'employee_count': '42'}
    )
    set_facts(user, deal.id, deal_size='250000', agent_of_record='Avery Agent (synthetic)')
    create_contact(user, deal.client_id, role='prior_broker', name='Prior Broker (synthetic)')
    hr = create_contact(user, deal.client_id, name='Casey HR (synthetic)', email='casey@example.com', phone='555-0100')
    payload = overview(api, deal)
    assert payload['identity']['legal_name'] == 'Example Holdings LLC'
    assert (payload['facts']['fein'], payload['facts']['employee_count']) == ('12-3456789', '42')
    assert payload['facts']['deal_size'] == '250000.00'
    assert payload['facts']['agent_of_record'] == {'value': 'Avery Agent (synthetic)', 'default': 'Dana'}
    assert payload['facts']['contact']['id'] == hr.id  # a prior broker is never the main contact (M30, B32)
    assert payload['facts']['contact']['email'] == 'casey@example.com'


def test_M26_M28_the_incumbent_reads_intakes_coverage_until_the_current_plans_hold_it(api, user, deal):
    written = intake_services.create_coverage(
        user, deal.id, {'line': 'medical', 'carrier': 'Example Health', 'funding': 'level_funded',
                        'in_force': True, 'commission': '4'}
    )  # fmt: skip
    facts = overview(api, deal)['facts']
    assert facts['carrier'] == {'value': 'Example Health', 'from': 'coverage', 'coverage_id': written.row.id,
                                'editable': True}  # fmt: skip
    assert facts['funding']['value'] == 'level_funded'
    assert facts['in_force'] == [{'line': 'medical', 'label': 'Medical', 'comp_label': '4%'}]
    quote_services.create_plan(
        user, deal, line='medical', role='current', carrier='Other Health', name='Current PPO',
        values={'funding': 'fully_insured'},
    )  # fmt: skip
    facts = overview(api, deal)['facts']
    assert facts['carrier']['from'] == 'plans' and facts['carrier']['editable'] is False
    assert facts['carrier']['value'] == 'Other Health'


def test_M14_CL8_a_won_prospect_stays_new_business_while_its_client_becomes_a_new_client(
    api, user, deal, django_capture_on_commit_callbacks
):
    set_status(user, deal.client_id, lifecycle.EXISTING_CLIENT)
    assert overview(api, deal)['identity']['type'] == 'renewal'  # before the sale the type follows the status
    set_status(user, deal.client_id, lifecycle.PROSPECT)
    assert overview(api, deal)['identity']['type'] == 'new_business'
    plan = quote_services.create_plan(user, deal, line='medical', role='alternate', carrier='Example', name='PPO')
    with django_capture_on_commit_callbacks(execute=True):
        quote_services.set_sold(user, plan.id, True)
    payload = overview(api, deal)
    assert payload['identity']['type'] == 'new_business' and payload['identity']['stage'] == 'sold'
    assert payload['client']['relationship'] == 'new_client' and payload['client']['on_book'] is True
    assert payload['client']['client_since'] == clock.today().isoformat()


def test_M36_plans_quoted_counts_renewal_and_alternate_plans_not_removed(api, user, deal):
    def plan(role, name, **links):
        return quote_services.create_plan(user, deal, line='medical', role=role, carrier='Example', name=name, **links)

    today = plan('current', 'Today')
    plan('renewal', 'Renewal', renews_id=today.id)
    plan('alternate', 'Alt A')
    gone = plan('alternate', 'Alt B')
    quote_services.delete_plans(user, deal, [gone.id])
    assert overview(api, deal)['tiles']['plans_quoted'] == 2


def test_M37_a_call_note_is_a_contact_and_a_plain_note_is_not(api, user, deal):
    add_note(user, deal.id, body='Internal thought (synthetic)', kind='note')
    assert overview(api, deal)['tiles']['last_contact_at'] is None
    call = add_note(user, deal.id, body='Called HR (synthetic)', kind='call')
    found = overview(api, deal)['tiles']['last_contact_at']
    assert found is not None and found.startswith(call.created_at.isoformat()[:16])


def test_M37_a_draft_link_is_no_contact_and_a_sent_one_is(api, user, deal):
    made = review_services.create(user, deal.id, {'asks': {'census': {'file': True}}, 'people': [{'name': 'Casey'}]})
    assert overview(api, deal)['tiles']['last_contact_at'] is None
    link = made.links[0][0]
    review_services.mark_sent(user, link.id, copied=True)
    assert overview(api, deal)['tiles']['last_contact_at'] is not None


def test_M37_an_older_note_does_not_hide_a_newer_send(api, user, deal):
    note = add_note(user, deal.id, body='Met the CFO (synthetic)', kind='meeting')
    Note.objects.filter(pk=note.id).update(created_at=clock.now() - timedelta(days=5))
    made = review_services.create(user, deal.id, {'asks': {'census': {'file': True}}, 'people': [{'name': 'Casey'}]})
    review_services.mark_sent(user, made.links[0][0].id, copied=True)
    found = overview(api, deal)['tiles']['last_contact_at']
    assert found > (clock.now() - timedelta(days=1)).isoformat()


def test_Q9_62_M20_the_renewal_offer_chip_shows_the_letters_figures_through_the_one_rule(api, deal, monkeypatch):
    from proposals import summary_read

    assert overview(api, deal)['renewal_offer'] is None  # no slice stores the letter's facts yet (OQ38)
    offer = {'renewal_pct_change': 12.0, 'renewal_premium_annual': 13440.0, 'stated_current_premium_annual': 12000.0,
             'group_number': 'G-100'}  # fmt: skip
    monkeypatch.setattr(summary_read, 'renewal_offer', lambda _deal: offer)
    assert overview(api, deal)['renewal_offer'] == {
        'premium_annual': 13440.0,
        'pct_change': 12.0,
        'label': 'Renewal offer $13,440/yr (+12.0%)',
    }


def test_M34_a_lost_deal_still_answers_its_header(api, user, deal):
    mark_lost(user, deal.id, 'Went with another broker')
    payload = overview(api, deal)
    assert payload['identity']['stage'] == 'lost'
    assert payload['client']['convert']['allowed'] is False
