"""What quotes tells intake, and what the Advisor shows of the intent (plan.md §5.2, §6.5; F13, F144, B24; Q.9 row
11). GD1's tests write through the services; their writes roll back with each test's transaction."""

import pytest

from conftest import make_deal
from deals.models import Deal
from intake import providers
from intake import services as intake
from intake.selectors import intake_payload
from quotes import facts, services
from quotes.selectors import lines_summary

pytestmark = pytest.mark.django_db


def _plan(user, deal, line, role, carrier, **values):
    return services.create_plan(user, deal, line=line, role=role, carrier=carrier, name=f'{carrier} {role}',
                                values=values)


def test_B24_quotes_fills_quote_lines(user, deal):
    current = _plan(user, deal, 'medical', 'current', 'Aetna', funding='level_funded')
    _plan(user, deal, 'medical', 'current', 'Cigna')
    _plan(user, deal, 'dental', 'alternate', 'Guardian')
    services.set_sold(user, current.id, True)
    found = providers.quote_lines(deal.id)
    assert found['medical']['sold'] and found['medical']['presented'] == 2
    assert found['medical']['current'] == {'carrier': 'Aetna, Cigna', 'funding': 'level_funded'}
    assert found['dental'] == {'presented': 1, 'sold': False, 'current': None}


def test_F144_incumbent_is_the_current_plans_once_there_are_some_else_the_coverage_row(user, deal):
    assert facts.incumbent(deal, 'medical') is None
    intake.create_coverage(user, deal.id, {'line': 'medical', 'carrier': 'Florida Blue', 'funding': 'fully_insured'})
    assert facts.incumbent(deal, 'medical') == {
        'carrier': 'Florida Blue',
        'funding': 'fully_insured',
        'source': 'coverage',
    }
    _plan(user, deal, 'medical', 'current', 'Aetna', funding='level_funded')
    assert facts.incumbent(deal, 'medical') == {'carrier': 'Aetna', 'funding': 'level_funded', 'source': 'plans'}
    intake.create_coverage(user, deal.id, {'line': 'std', 'carrier': 'Lincoln', 'in_force': False})
    assert facts.incumbent(deal, 'std') is None  # a gap the deal proposes to fill is not in force


def test_F13_a_line_the_intent_keeps_off_the_proposal_is_flagged_on_its_tab(user):
    deal = make_deal(user, requested_lines=('medical',))
    for line in ('medical', 'dental', 'vision'):
        _plan(user, deal, line, 'current', 'Carrier')
    intake.set_intent(user, deal.id, line='dental', has_today=True)
    intake.set_intent(user, deal.id, line='dental', this_year='off')
    off = {row['line']: (row['off'], row['off_reason']) for row in lines_summary(deal)}
    assert off['medical'] == (None, '')
    assert off['dental'] == ('left_off', 'Left off in Coverage & marketing intent')
    assert off['vision'] == ('not_in_intent', 'Not in the Coverage & marketing intent')


def test_B16_F13_GD1_shop_it_and_keep_as_is_per_line_confirm_lapses_and_the_advisor_flags_the_line(gd1, user):
    """Slice 11's done-when on GD1: the card shows Shop it and Keep as-is per line; a change after Confirm shows
    "Changed since confirmed"; the Advisor flags the line kept off the proposal."""
    deal_id = gd1.deal.id

    def card():
        return intake_payload(Deal.objects.get(pk=deal_id))['intent']

    intake.set_intent(user, deal_id, lines=['medical', 'dental', 'vision'], has_today=True)
    intake.set_intent(user, deal_id, line='dental', this_year='keep')
    shown = card()
    assert {row['line']: row['this_year_label'] for row in shown['rows']} == {
        'medical': 'Shop it',
        'dental': 'Keep as-is',
        'vision': 'Shop it',
    }
    assert {row['line']: row['from_plans']['carrier'] for row in shown['rows']} == {
        'medical': 'Aetna',
        'dental': 'Guardian',
        'vision': 'VSP',
    }
    intake.confirm_intent(user, deal_id)
    assert card()['state'] == 'done'
    intake.set_intent(user, deal_id, line='vision', this_year='off')
    assert card()['state'] == 'stale'
    tabs = {row['line']: row['off'] for row in lines_summary(Deal.objects.get(pk=deal_id))}
    assert tabs == {'medical': None, 'dental': None, 'vision': 'left_off'}
