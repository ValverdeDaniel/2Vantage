"""GD6 reaches Ready to market, and GD3's headcount sets the tier at both quote-first checkpoints (plan.md §13.4, §13.9
row 40; Q.3 #5, Q.4, Q.9 row 40). Each test builds its own deal (it writes): the root conftest's `get_to_market` and
`quote_first`."""

import pytest

from deals.models import Activity, Deal
from intake import providers, services

pytestmark = pytest.mark.django_db


def gate(api, deal):
    body = api.get(f'/api/deals/{deal.id}/intake/').json()
    return body['checklist'], body['ready']


def test_B33_GD6_as_seeded_is_blocked_by_the_gaps_its_key_lists(api, get_to_market, golden_keys):
    key = golden_keys['GD6']['ready']
    card, ready = gate(api, get_to_market.built.deal)
    assert (card['tier'], card['tier_label'], card['enrolled'], card['geo']) == (
        key['tier'],
        key['tier_label'],
        key['enrolled'],
        key['geo'],
    )
    assert [row['key'] for row in card['items']] == key['items']
    assert [row['key'] for row in card['items'] if row['optional']] == key['optional']
    assert ready['state'] == key['seeded']['state']
    assert [gap['key'] for gap in ready['gaps']] == key['seeded']['gaps']


def test_B33_B34_GD6_reaches_ready_to_market_and_is_marked_without_a_stage_move(user, api, get_to_market, golden_keys):
    key = golden_keys['GD6']['ready']
    deal = get_to_market.built.deal
    stage = Deal.objects.get(pk=deal.pk).stage
    get_to_market.step('contacts', 'census_arrives', 'intent', 'bor')
    card, ready = gate(api, deal)
    assert ready['state'] == 'blocked' and [gap['key'] for gap in ready['gaps']] == [
        'cobra',
        'medical_questionnaire',
        'renewal',
        'invoice',
    ]
    assert (ready['contacts_ok'], ready['bor_on_file'], ready['census_ok']) == (True, True, True)
    get_to_market.step('ticks')
    card, ready = gate(api, deal)
    assert ready['state'] == key['at_ready']['state'] and ready['gaps'] == []
    assert (card['required'], card['done'], card['all_clear']) == (
        key['at_ready']['required'],
        key['at_ready']['done'],
        True,
    )
    body = api.post(f'/api/deals/{deal.id}/intake/marketed/', {}, format='json').json()
    assert body['ready']['state'] == 'submitted' and body['skipped'] == []
    assert Activity.objects.get(pk=body['activity_id']).summary == 'Marked as marketed'
    assert Deal.objects.get(pk=deal.pk).stage == stage  # OQ52 default


def test_B34_GD6_marked_anyway_names_what_it_skipped_and_undo_restores_blocked(user, api, get_to_market):
    deal = get_to_market.built.deal
    get_to_market.step('contacts', 'bor')
    done = services.mark_marketed(user, deal.id, override=True)
    assert [gap['key'] for gap in done.skipped] == [
        'census',
        'coverage_intent',
        'cobra',
        'medical_questionnaire',
        'renewal',
        'invoice',
    ]
    assert done.activity.summary.startswith('Marked as marketed anyway, skipping 6: Census, Confirm current coverage')
    assert api.post(f'/api/activity/{done.activity.id}/revert/').status_code in (200, 201)
    assert gate(api, deal)[1]['state'] == 'blocked'


def test_Q3_5_B25_GD3_the_tier_follows_the_headcount_at_checkpoints_A_and_B(api, quote_first):
    deal = quote_first.built.deal
    card, _ready = gate(api, deal)
    assert card['enrolled'] == providers.headcount(deal.id)['count'] == 52  # A: the line figure 30·8·6·8
    assert (card['tier'], card['geo']) == ('mid', 'home address')
    quote_first.arrive('D').arrive('F').split().census()
    card, _ready = gate(api, deal)
    assert card['enrolled'] == providers.headcount(deal.id)['count'] == 48  # B: the census of 48 takes over
    assert (card['tier'], card['geo']) == ('small', 'ZIP code')
    questionnaire = next(row for row in card['items'] if row['key'] == 'medical_questionnaire')
    assert questionnaire['label'] == 'Group medical questionnaire — completed & signed'
