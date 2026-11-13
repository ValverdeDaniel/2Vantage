"""`GET clients/{id}/overview/` (plan.md §7.16, §8.5; CL14–CL22, G116; Q.9 row 67): the client payload for a prospect,
a New client (GD1-sold) and a client with no deal; the deal the page works in; the Agenda tile; Coverage in force; and
GD6's History chips. Synthetic only; the module-scoped golden deals are only read."""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

import pytest

from agenda.services import add_task
from conftest import make_deal
from deals import clock, lifecycle
from deals.models import Activity
from deals.services import create_client, mark_lost, set_status
from intake import services as intake_services

pytestmark = pytest.mark.django_db

BLOCKS = {'client_id', 'deal_id', 'current', 'last_sold', 'convert', 'facts', 'tiles', 'in_force', 'commission',
          'outreach', 'history'}  # fmt: skip


def client_overview(api, client_id):
    response = api.get(f'/api/clients/{client_id}/overview/')
    assert response.status_code == 200, response.content
    return response.json()


def test_Q9_67_a_prospect_works_in_its_deal_and_may_be_converted(api, user):
    deal = make_deal(user, name='Prospect Co. (synthetic)', effective_date=clock.today() + timedelta(days=40))
    intake_services.update_answers(user, deal.id, {'legal_name': 'Prospect Holdings LLC', 'fein': '12-3456789'})
    intake_services.create_coverage(
        user, deal.id, {'line': 'medical', 'carrier': 'Example Health', 'funding': 'level_funded', 'in_force': True,
                        'commission': '4'}
    )  # fmt: skip
    rows = Activity.objects.count()
    payload = client_overview(api, deal.client_id)
    assert set(payload) == BLOCKS and Activity.objects.count() == rows
    assert payload['deal_id'] == deal.id and payload['current']['deal_id'] == deal.id
    assert payload['current']['stage'] == 'intake' and payload['current']['type'] == 'new_business'
    assert payload['convert'] == {'allowed': True, 'sentence': ''} and payload['last_sold'] is None
    assert payload['facts']['legal_name'] == 'Prospect Holdings LLC' and payload['facts']['fein'] == '12-3456789'
    assert payload['facts']['funding'] == {'value': 'level_funded', 'from': 'coverage'}
    assert payload['tiles']['effective']['days'] == 40
    # A prospect's coverage in force is its current coverage, with the in-force commission (CL20).
    assert payload['in_force']['kind'] == 'current'
    assert payload['in_force']['rows'] == [{
        'line': 'medical', 'label': 'Medical', 'carrier': 'Example Health', 'plan': '', 'funding': 'level_funded',
        'premium_month': None, 'commission': '4%', 'expected': None, 'renews': deal.effective_date.isoformat(),
    }]  # fmt: skip
    # The deal in flight's outreach strip and "Who we've asked" ride along for the Activity card (old ActivityFeed).
    assert payload['outreach']['links'] == [] and payload['outreach']['open'] == 0
    [row] = payload['history']
    assert row['deal_id'] == deal.id and row['current'] is True and row['sold'] is None
    assert row['chips']['intake']['answered'] >= 2 and row['chips']['census'] is None


def test_CL15_convert_is_refused_with_the_status_doors_sentence_on_a_lost_deal(api, user):
    deal = make_deal(user, name='Lost Co. (synthetic)')
    mark_lost(user, deal.id, 'Went elsewhere (synthetic)')
    payload = client_overview(api, deal.client_id)
    assert payload['convert'] == {
        'allowed': False,
        'sentence': 'This deal is marked lost — reopen it before converting the client.',
    }
    # A lost deal is past working with the client: nothing is in flight, and the page works in the newest deal.
    assert payload['current'] is None and payload['deal_id'] == deal.id and payload['outreach'] is None
    assert payload['tiles']['agenda'] == {'overdue': 0, 'soon': 0, 'total': 0}
    set_status(user, deal.client_id, lifecycle.EXISTING_CLIENT)
    assert client_overview(api, deal.client_id)['convert'] is None  # only a prospect is offered Convert


def test_Q9_67_a_new_client_GD1_sold_shows_its_sold_plans_and_its_revenue(api, gd1_sold, golden_keys):
    """The key's two records (CG1N and U2 at the agreed 5%): the medical line's Sold package is both plans, its
    premium a month their annual premiums over twelve, and the Expected revenue tile the key's total, half up."""
    deal = gd1_sold.deal
    payload = client_overview(api, deal.client_id)
    key = golden_keys['GD1-sold']
    carriers = [record['carrier'] for record in key['records']]
    assert payload['convert'] is None and payload['current']['stage'] == 'sold'
    assert payload['last_sold']['carriers'] == carriers and payload['last_sold']['deal_id'] == deal.id
    [medical] = payload['in_force']['rows']
    assert payload['in_force']['kind'] == 'sold' and medical['line'] == 'medical'
    assert medical['carrier'] == ', '.join(carriers) and medical['commission'] == '5%'
    annual = sum(Decimal(record['premium_annual']) for record in key['records'])
    assert Decimal(str(medical['premium_month'])) == (annual / 12).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    total = Decimal(str(key['expected_total'])).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    assert payload['tiles']['expected_revenue'] == int(total) == medical['expected']
    assert payload['history'][0]['expected'] == int(total)
    assert medical['renews'] == deal.effective_date.replace(year=deal.effective_date.year + 1).isoformat()
    assert payload['commission']['booking']['state'] == 'booked'
    assert payload['history'][0]['sold']['carriers'] == carriers and payload['history'][0]['current'] is True


def test_Q9_67_a_client_with_no_deal_answers_every_block_empty(api, user):
    client, deal = create_client(user, name='Outside Co. (synthetic)', relationship='existing_client', first_deal=False)
    assert deal is None
    payload = client_overview(api, client.id)
    assert set(payload) == BLOCKS
    assert payload['deal_id'] is None and payload['current'] is None and payload['facts'] is None
    assert payload['history'] == [] and payload['in_force'] == {'kind': None, 'rows': []}
    assert payload['commission'] is None and payload['last_sold'] is None and payload['convert'] is None
    assert payload['tiles'] == {'effective': None, 'agenda': {'overdue': 0, 'soon': 0, 'total': 0},
                                'expected_revenue': None}  # fmt: skip


def test_CL18_the_agenda_tile_counts_open_tasks_by_the_day_they_fall_due(api, user):
    deal = make_deal(user, name='Agenda Co. (synthetic)')
    today = clock.today()
    before = client_overview(api, deal.client_id)['tiles']['agenda']
    add_task(user, deal.id, title='Chase the census (synthetic)', due=(today - timedelta(days=2)).isoformat())
    add_task(user, deal.id, title='Send the summary (synthetic)', due=(today + timedelta(days=5)).isoformat())
    add_task(user, deal.id, title='Plan next year (synthetic)', due=(today + timedelta(days=200)).isoformat())
    add_task(user, deal.id, title='Done already (synthetic)', due=today.isoformat(), done=True)
    after = client_overview(api, deal.client_id)['tiles']['agenda']
    assert after['overdue'] == before['overdue'] + 1 and after['soon'] == before['soon'] + 1
    assert after['total'] == before['total'] + 3


def test_CL20_a_hand_converted_client_with_nothing_sold_shows_its_current_coverage(api, user):
    deal = make_deal(user, name='Converted Co. (synthetic)')
    set_status(user, deal.client_id, lifecycle.NEW_CLIENT)
    payload = client_overview(api, deal.client_id)
    assert payload['in_force']['kind'] == 'current' and payload['last_sold'] is None


def test_G116_GD6s_history_chips_name_its_intake_census_and_questionnaire(api, get_to_market):
    built = get_to_market.step('census_arrives').built
    [row] = client_overview(api, built.deal.client_id)['history']
    chips = row['chips']
    assert chips['intake']['answered'] > 0
    assert chips['census']['employees'] == sum(group['n'] for group in built.spec['census']['groups'])
    [form] = chips['forms']
    assert form['chip'] == 'Questionnaire' and form['label'] and form['signed'] is False
    assert chips['documents'] >= 1  # the census file


def test_CL20_a_prospects_coverage_in_force_falls_back_to_the_advisors_current_plans(api, gd6):
    """GD6 as seeded: no coverage confirmed on Intake yet, but its current medical plan is on the Advisor."""
    payload = client_overview(api, gd6.deal.client_id)
    current = next(plan for plan in gd6.spec['plans'] if plan['role'] == 'current' and plan['line'] == 'medical')
    medical = next(row for row in payload['in_force']['rows'] if row['line'] == 'medical')
    assert payload['in_force']['kind'] == 'current' and medical['carrier'] == current['carrier']
    assert medical['premium_month'] is None and medical['renews'] == gd6.deal.effective_date.isoformat()
