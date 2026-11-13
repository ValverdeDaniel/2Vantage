"""Agenda on the golden deals (Q.4, Q.9 row 60; plan.md §5.9, OQ90, OQ91): GD3's quote-first leads at each of its
checkpoints, GD6's steps as it walks to Ready to market and to the market, and GD1-sold's step after the sale. The
deals come from the root conftest (`quote_first`, `get_to_market`, `sell_gd1`), built for each test that writes."""

from datetime import timedelta
from unittest import mock

import pytest

from agenda import selectors
from deals import clock
from intake import services as intake_services

pytestmark = pytest.mark.django_db

ADD_OR_TYPE = 'Add the census, or type enrollment in the Advisor'


def agenda(deal, user):
    return selectors.deal_agenda(deal, user)


def step(payload, key):
    return next((row for row in payload['rows'] if row.get('key') == key), None)


def test_OQ90_GD3_at_checkpoint_A_typed_counts_keep_the_census_from_leading(user, quote_first):
    """As seeded: ten quotes on typed whole-line counts and the renewal packet unread. Reading the packet leads; the
    census is listed, never leading; intake, the questionnaire and the RFP are listed and do not lead."""
    payload = agenda(quote_first.built.deal, user)
    assert payload['next_step']['label'] == 'Read carrier quotes'
    census = step(payload, 'import_census')
    assert census['label'] == 'Import the census' and not census['lead'] and census['section'] == 'up_next'
    for key in ('complete_intake', 'questionnaire', 'build_rfp'):
        assert step(payload, key) and not step(payload, key)['lead']
    assert [row['state'] for row in payload['journey'] if row['key'] in ('intake_ready', 'marketed')] == ['skipped'] * 2


def test_I50_GD3_a_second_current_plan_leaves_quotes_without_enrollment_and_the_census_step_leads(user, quote_first):
    """The renewal packet's two current plans arrive: the line figure stops pricing them (F88), so no enrollment
    source reaches those plans, and the next step reads "Add the census, or type enrollment in the Advisor"."""
    quote_first.arrive('D').arrive('F')
    payload = agenda(quote_first.built.deal, user)
    assert payload['next_step']['label'] == ADD_OR_TYPE
    assert payload['next_step']['link'] == f'/deals/{quote_first.built.deal.id}/advisor?line=medical'
    census = step(payload, 'import_census')
    assert census['also'] == {'label': 'Census ▸', 'link': f'/deals/{quote_first.built.deal.id}/census'}


def test_I16_GD3_later_holds_the_lead_step_until_its_day(user, quote_first):
    quote_first.arrive('D').arrive('F')
    deal = quote_first.built.deal
    from agenda import services

    services.set_later(user, deal.id, 'import_census', (clock.today() + timedelta(days=2)).isoformat())
    held = agenda(deal, user)
    assert held['next_step']['label'] == 'Read carrier quotes' and step(held, 'import_census')['section'] == 'later'
    two_days = clock.now() + timedelta(days=2)
    with mock.patch.object(clock, 'now', return_value=two_days):
        assert agenda(deal, user)['next_step']['label'] == ADD_OR_TYPE


def test_I49_GD3_the_split_then_the_census_take_the_enrollment_step_away(user, quote_first):
    quote_first.arrive('D').arrive('F').split()
    split = agenda(quote_first.built.deal, user)
    assert not step(split, 'import_census')['lead'] and step(split, 'import_census')['label'] == 'Import the census'
    quote_first.census()
    payload = agenda(quote_first.built.deal, user)
    assert step(payload, 'import_census') is None and step(payload, 'map_census') is None
    assert payload['journey'][1] == {**payload['journey'][1], 'key': 'enrollment_in', 'state': 'done'}


def test_I44_OQ90_GD6_walks_its_gate_one_blocker_at_a_time(user, get_to_market):
    """GD6 carries two alternates for the Advisor's budget hints, so its quotes are in: the gate's steps are listed one
    per blocker and none of them leads (OQ90); the proposal leads."""
    deal = get_to_market.built.deal
    seeded = agenda(deal, user)
    assert seeded['next_step']['key'] == 'build_proposal'
    gate = {'checklist:coverage_intent', 'checklist:cobra', 'add_hr_contact', 'get_bor', 'questionnaire'}
    assert gate <= {row['key'] for row in seeded['rows']}
    assert not any(step(seeded, key)['lead'] for key in gate)
    get_to_market.step('contacts', 'bor')
    payload = agenda(deal, user)
    assert step(payload, 'add_hr_contact') is None and step(payload, 'get_bor') is None
    get_to_market.ready()
    ready = agenda(deal, user)
    assert step(ready, 'send_rfp')['label'] == 'Intake ready — market for quotes'
    assert step(ready, 'import_census') is None and step(ready, 'checklist:cobra') is None
    intake_services.mark_marketed(user, deal.id)
    marketed = agenda(deal, user)
    assert step(marketed, 'send_rfp')['label'] == 'Sent to market' and step(marketed, 'complete_intake') is None
    assert [row['state'] for row in marketed['journey'][:3]] == ['done', 'done', 'done']


def test_I54_GD6_waits_on_carriers_from_marketed_at_and_follows_up_at_ten_days(user, get_to_market):
    deal = get_to_market.ready().built.deal
    intake_services.mark_marketed(user, deal.id)
    later = clock.now() + timedelta(days=10)
    with mock.patch.object(clock, 'now', return_value=later):
        payload = agenda(deal, user)
    waiting = step(payload, 'read_quotes')  # its quotes were in before it went to market: none came back since
    assert waiting['label'] == 'Waiting on carrier quotes' and waiting['section'] == 'waiting'
    follow_up = step(payload, 'follow_up_carriers')
    assert follow_up['label'] == 'Follow up with the carriers — at market 10 days, no quotes back'
    assert payload['waiting']['owner'] == 'carrier' and payload['waiting']['severity'] == 'warn'


def test_I63_GD1_sold_shows_its_commission_step_or_sold(user, sell_gd1):
    payload = agenda(sell_gd1.deal, user)
    assert step(payload, 'mark_sold')['label'] == 'Sold'
    commission = step(payload, 'commission')
    assert payload['next_step']['label'] in ('Sold', commission['label'])
    assert payload['next_step']['key'] in ('mark_sold', 'commission')
    for key in ('follow_up_client', 'send_drafts', 'complete_intake', 'import_census'):
        assert step(payload, key) is None
