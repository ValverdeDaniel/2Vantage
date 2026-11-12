"""Stars, the shortlist, the recommendation and the sale through the API and the services (plan.md §5.4; F50, F51,
F55, F123, H124; OQ12, OQ37; slice 7's "done when")."""

import threading
import time
from unittest import mock

import pytest
from django.db import connection

from conftest import make_deal
from deals.models import Activity, Deal
from quotes import signals
from quotes.models import Plan
from quotes.services import marks
from quotes.services import plans as plan_services

SIXTEEN = 'The Medical proposal holds 16 plans (3 current, 13 starred) — unstar one first.'


def make(user, deal, role='alternate', name='Quote', replaces=(), **values):
    return plan_services.create_plan(
        user, deal, line='medical', role=role, carrier='Cigna', name=name, replaces_ids=list(replaces), values=values
    )


def quotes_for(deal, current, count):
    """`count` quotes replacing `current`, as create_plan leaves them (made in one statement: the tests are about
    marks, not about adding plans)."""
    made = Plan.objects.bulk_create(
        Plan(deal=deal, line='medical', role='alternate', carrier='Cigna', name=f'Quote {n}', sort_order=10 + n)
        for n in range(count)
    )
    links = Plan.replaces.through
    links.objects.bulk_create(links(from_plan_id=plan.id, to_plan_id=current.id) for plan in made)
    return made


@pytest.fixture
def crowded(user, deal):
    """Three current plans and seventeen quotes replacing the first: 13 stars fill the line."""
    currents = [make(user, deal, 'current', f'Current {n}') for n in range(3)]
    return currents, quotes_for(deal, currents[0], 17)


def star(api, deal, plans, starred=True):
    return api.post(
        f'/api/deals/{deal.id}/plans/star/', {'plan_ids': [p.id for p in plans], 'starred': starred}, format='json'
    )


def test_F50_done_when_the_17th_column_is_refused_with_a_sentence(api, deal, crowded):
    _, quotes = crowded
    assert star(api, deal, quotes[:13]).status_code == 200
    refused = star(api, deal, [quotes[13]])
    assert (refused.status_code, refused.json()) == (409, {'detail': SIXTEEN})
    assert not Plan.objects.get(pk=quotes[13].id).starred
    batch = star(api, deal, quotes[:12])  # already starred: nothing new to fit
    assert batch.status_code == 200 and batch.json()['plans'] == []


def test_F50_a_batch_past_the_room_is_refused_whole(api, deal, crowded):
    _, quotes = crowded
    star(api, deal, quotes[:11])
    refused = star(api, deal, quotes[11:15])
    assert refused.status_code == 409
    assert refused.json()['detail'] == (
        'The Medical proposal holds 16 plans (3 current, 11 starred): 4 ticked, only 2 more fit. '
        'Unstar some or tick fewer.'
    )
    assert Plan.objects.filter(deal=deal, starred=True).count() == 11


def test_F50_a_recommendation_counts_toward_the_room(api, user, deal, crowded):
    _, quotes = crowded
    star(api, deal, quotes[:12])
    marks.set_recommended(user, quotes[12].id, True)
    refused = api.post(f'/api/plans/{quotes[13].id}/recommend/', {'recommended': True}, format='json')
    assert refused.status_code == 409
    assert refused.json()['detail'] == (
        'The Medical proposal holds 16 plans (3 current, 1 recommended, 12 starred) — unstar one before recommending '
        'another.'
    )
    assert star(api, deal, [quotes[12]]).status_code == 200  # a recommended plan's star adds no column


def test_F50_a_current_plan_takes_no_star(api, deal, crowded):
    currents, _ = crowded
    refused = star(api, deal, [currents[0]])
    assert refused.status_code == 409
    assert (
        refused.json()['detail']
        == 'Cigna Current 0 is a current plan — it is always on the proposal, so it takes no star.'
    )


def test_F50_a_star_records_its_reason_who_and_when(api, user, deal, crowded):
    _, quotes = crowded
    body = star(api, deal, [quotes[0]]).json()
    (plan,) = body['plans']
    assert plan['star']['reason'] == 'Hand-picked' and plan['star']['by'] == user.id and plan['star']['at']
    assert Activity.objects.get(pk=body['activity_id']).summary == 'Starred 1 plan'
    off = star(api, deal, [quotes[0]], False).json()['plans'][0]
    assert off['star'] is None and Plan.objects.get(pk=quotes[0].id).star_reason == ''


def test_F51_a_fresh_star_links_an_unlinked_quote_to_the_nearest_current_plan(api, user, deal):
    hdhp = make(user, deal, 'current', 'HDHP', deductible_single='3300', oop_max_single='6000', rate_ee='512')
    ppo = make(user, deal, 'current', 'PPO', deductible_single='1500', oop_max_single='4000', rate_ee='700')
    like_ppo = make(user, deal, name='Like PPO', deductible_single='1250', oop_max_single='4500', rate_ee='690')
    linked = make(user, deal, name='Linked', replaces=[hdhp.id], deductible_single='1500')
    star(api, deal, [like_ppo, linked])
    assert list(Plan.objects.get(pk=like_ppo.id).replaces.values_list('id', flat=True)) == [ppo.id]
    assert list(Plan.objects.get(pk=linked.id).replaces.values_list('id', flat=True)) == [hdhp.id]  # left as linked


def test_F51_on_a_line_with_one_current_plan_a_star_links_nothing(api, user, deal):
    make(user, deal, 'current', 'Only', deductible_single='3300')
    quote = make(user, deal, name='Quote', deductible_single='3000')
    star(api, deal, [quote])
    assert not Plan.objects.get(pk=quote.id).replaces.exists()


def test_F55_clear_shortlist_clears_one_line_with_one_revertible_row(api, user, deal, crowded):
    _, quotes = crowded
    dental = plan_services.create_plan(user, deal, line='dental', role='alternate', carrier='Delta', name='PPO')
    marks.star(user, deal, [quotes[0].id, quotes[1].id, dental.id], True)
    body = api.post(f'/api/deals/{deal.id}/plans/shortlist/clear/', {'line': 'medical'}, format='json').json()
    assert {p['id'] for p in body['plans']} == {quotes[0].id, quotes[1].id}
    assert Plan.objects.get(pk=dental.id).starred  # another line keeps its stars
    row = Activity.objects.get(pk=body['activity_id'])
    assert row.summary == 'Cleared the Medical shortlist (2 stars)' and row.revertible
    assert api.post(f'/api/activity/{row.id}/revert/').status_code == 200
    assert (
        Plan.objects.filter(pk__in=[quotes[0].id, quotes[1].id], starred=True, star_reason='Hand-picked').count() == 2
    )


@pytest.mark.django_db(transaction=True)
def test_F50_Q3_concurrent_stars_at_the_cap_leave_16(user):
    deal = make_deal(user)
    currents = [make(user, deal, 'current', f'Current {n}') for n in range(3)]
    quotes = quotes_for(deal, currents[0], 14)
    marks.star(user, deal, [q.id for q in quotes[:12]], True)
    real_line = marks.locks.line
    results = []

    def slow_line(*args):
        found = real_line(*args)
        time.sleep(0.15)  # hold the room check open while the other request arrives
        return found

    def race(plan):
        try:
            marks.star(user, deal, [plan.id], True)
            results.append('starred')
        except marks.activity.Refused as refused:
            results.append(refused.sentence)
        finally:
            connection.close()

    with mock.patch.object(marks.locks, 'line', slow_line):
        threads = [threading.Thread(target=race, args=(plan,)) for plan in quotes[12:14]]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert sorted(results) == sorted(
        ['starred', 'The Medical proposal holds 16 plans (3 current, 13 starred) — unstar one first.']
    )
    assert Plan.objects.filter(deal=deal, starred=True).count() + len(currents) == 16


def test_5_1_un_selling_the_last_sold_plan_records_the_stage_change(api, user, deal, crowded):
    _, quotes = crowded
    api.post(f'/api/plans/{quotes[0].id}/sold/', {'sold': True}, format='json')
    body = api.post(f'/api/plans/{quotes[0].id}/sold/', {'sold': False}, format='json').json()
    assert body['deal']['stage'] == 'proposal'
    row = Activity.objects.filter(deal=deal, area='deal').latest('id')
    assert (row.summary, row.changes) == (
        'Moved to Proposal (no plan is sold now)',
        [{'t': f'deal:{deal.id}', 'k': {'stage': ['sold', 'proposal']}}],
    )
    sold_rows = Activity.objects.filter(deal=deal, action='sold').order_by('id')
    assert [r.changes[0]['k']['plan.sold'] for r in sold_rows] == [[False, True], [True, False]]
    assert Deal.objects.get(pk=deal.id).stage == 'proposal'


def test_O1_sold_changed_and_plans_changed_are_sent_on_commit(user, deal, crowded, django_capture_on_commit_callbacks):
    _, quotes = crowded
    heard = []

    def hear(signal_name):
        return lambda sender, **kwargs: heard.append((signal_name, kwargs))

    signals.sold_changed.connect(sold := hear('sold'), weak=False)
    signals.plans_changed.connect(changed := hear('changed'), weak=False)
    try:
        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            marks.set_sold(user, quotes[0].id, True)
        assert heard == []  # nothing before the commit
        for callback in callbacks:
            callback()
    finally:
        signals.sold_changed.disconnect(sold)
        signals.plans_changed.disconnect(changed)
    assert (
        'sold',
        {'signal': signals.sold_changed, 'deal_id': deal.id, 'lines': ['medical'], 'user_id': user.id},
    ) in heard
    assert ('changed', {'signal': signals.plans_changed, 'deal_id': deal.id, 'lines': ['medical']}) in heard
