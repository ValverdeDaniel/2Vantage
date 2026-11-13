"""The Work queue's graph cards, `GET work-queue/stats/` (plan.md §7.15; A10, I83, I84, I127; OQ94; Q.9 row 61): actions
completed this week as milestone Activity rows plus ticked tasks, each by its `count`; sales this month against the
same days of last month, in the agency's month; ten real points each. Factory deals; dates set in the test's setup."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest import mock
from zoneinfo import ZoneInfo

import pytest

from agenda import services
from agenda.queue import stats
from conftest import make_deal
from deals import clock
from deals.models import Activity
from deals.services import set_archived, set_facts
from intake import services as intake_services
from quotes import services as quote_services
from quotes.models import Plan

pytestmark = pytest.mark.django_db

EASTERN = ZoneInfo('America/New_York')


def day(n):
    return (clock.today() + timedelta(days=n)).isoformat()


def tick_two(user, deal):
    first = services.add_task(user, deal.id, title='Call HR', due=day(1))
    second = services.add_task(user, deal.id, title='Email the census ask', due=day(2))
    services.update_task(user, first.id, done=True)
    services.update_task(user, second.id, done=True)


def test_I83_actions_count_milestones_and_ticked_tasks_by_their_count(api, user):
    deal = make_deal(user, name='Busy Co. (synthetic)')
    tick_two(user, deal)  # one coalesced "Ticked 2 tasks" row
    intake_services.mark_marketed(user, deal.id, override=True)
    intake_services.unmark_marketed(user, deal.id)  # the same action, other words: not a milestone
    ticks = Activity.objects.get(deal=deal, area='agenda', action='updated')
    assert ticks.count == 2
    found = api.get('/api/work-queue/stats/').json()['actions_week']
    assert found['total'] == 3 and found['series'][-1] == 3 and len(found['series']) == stats.POINTS


def test_I83_an_archived_clients_and_a_reverted_rows_actions_leave_the_card(api, user):
    gone = make_deal(user, name='Archived Busy Co. (synthetic)')
    tick_two(user, gone)
    set_archived(user, gone.client_id, True)
    kept = make_deal(user, name='Reverted Co. (synthetic)')
    intake_services.mark_marketed(user, kept.id, override=True)
    Activity.objects.filter(deal=kept, action='marketed').update(reverted_at=clock.now())
    assert api.get('/api/work-queue/stats/').json()['actions_week']['total'] == 0


def test_I83_the_change_is_against_the_seven_days_before(user):
    deal = make_deal(user, name='Two Weeks Co. (synthetic)')
    tick_two(user, deal)
    Activity.objects.filter(deal=deal, area='agenda', action='updated').update(
        created_at=clock.now() - timedelta(days=9)
    )
    intake_services.mark_marketed(user, deal.id, override=True)
    found = stats.actions(clock.now())
    assert found['series'][-2:] == [2, 1] and found['total'] == 1 and found['change_pct'] == -50


def sold_on(user, name, size, moment):
    deal = make_deal(user, name=name)
    set_facts(user, deal.id, deal_size=size)
    plan = quote_services.create_plan(user, deal, line='medical', role='alternate', carrier='Example', name='PPO')
    quote_services.set_sold(user, plan.id, True)
    Plan.objects.filter(pk=plan.id).update(sold_at=moment)
    return deal


def test_I84_OQ94_sales_compare_the_same_days_of_last_month_in_the_agencys_month(user):
    now = datetime(2026, 11, 12, 15, 0, tzinfo=EASTERN)
    sold_on(user, 'November Co. (synthetic)', '200000', datetime(2026, 11, 3, 10, tzinfo=EASTERN))
    sold_on(user, 'Early October Co. (synthetic)', '100000', datetime(2026, 10, 5, 10, tzinfo=EASTERN))
    sold_on(user, 'Late October Co. (synthetic)', '50000', datetime(2026, 10, 20, 10, tzinfo=EASTERN))
    # 21:30 Eastern on Oct 31 is November in UTC, and still October for the agency
    sold_on(user, 'Halloween Co. (synthetic)', '25000', datetime(2026, 10, 31, 21, 30, tzinfo=EASTERN))
    with mock.patch.object(clock, 'now', return_value=now):
        found = stats.sales(now)
    assert Decimal(found['total']) == Decimal('200000')
    assert found['change_pct'] == 100  # 200,000 against Oct 1–12's 100,000, not the whole of October
    assert found['series'][-2:] == [175000.0, 200000.0] and len(found['series']) == stats.POINTS


def test_I84_a_deal_with_two_sold_plans_counts_once_in_the_month_of_its_first_sale(user):
    now = datetime(2026, 11, 12, 15, 0, tzinfo=EASTERN)
    deal = sold_on(user, 'Two Plans Co. (synthetic)', '80000', datetime(2026, 11, 2, 9, tzinfo=EASTERN))
    second = quote_services.create_plan(user, deal, line='dental', role='alternate', carrier='Example', name='Dental')
    quote_services.set_sold(user, second.id, True)
    Plan.objects.filter(pk=second.id).update(sold_at=datetime(2026, 11, 9, 9, tzinfo=EASTERN))
    found = stats.sales(now)
    assert Decimal(found['total']) == Decimal('80000') and found['change_pct'] is None


def test_A10_the_stats_endpoint_answers_both_cards(api):
    found = api.get('/api/work-queue/stats/').json()
    assert set(found) == {'actions_week', 'sales_month'}
    for card in found.values():
        assert set(card) == {'total', 'change_pct', 'series'} and len(card['series']) == stats.POINTS
