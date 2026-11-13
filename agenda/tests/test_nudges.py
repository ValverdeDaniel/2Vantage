"""Nudge rows (plan.md §7.15; I35–I39, I15; Part I's `test_nudges`): a review link's reminder on the deal's Agenda, with
Later and ✓ through review's `set_nudge` and `finish_nudge` (I37), so review's rules and sentences hold — a day before
the link runs out, a link that still opens, a reminder that is set. Factory deals; synthetic names only."""

from datetime import timedelta

import pytest

from conftest import make_deal
from deals import clock
from deals.models import Activity, Note
from deals.services import mark_lost
from review import services as review_services
from review.models import ClientLink

from .world import sent_ask

pytestmark = pytest.mark.django_db


def day(n):
    return (clock.today() + timedelta(days=n)).isoformat()


@pytest.fixture
def held(user):
    """(deal, link): a link sent yesterday with a reminder to nudge them in two days, set in its settings card."""
    deal = make_deal(user, name='Nudge Row Co. (synthetic)')
    link = sent_ask(user, deal, days_ago=1)
    review_services.set_nudge(user, link.id, day(2))
    return deal, ClientLink.objects.get(pk=link.id)


def nudge_row(api, deal):
    rows = api.get(f'/api/deals/{deal.id}/agenda/').json()['rows']
    return next((row for row in rows if row['kind'] == 'nudge'), None)


def post(api, deal, link_id, body):
    return api.post(f'/api/deals/{deal.id}/agenda/nudges/{link_id}/', body, format='json')


def nudge_of(link):
    return ClientLink.objects.get(pk=link.pk).nudge


def reviews(deal, action):
    return Activity.objects.filter(deal=deal, area='review', action=action).count()


def test_I35_I37_a_nudge_row_offers_later_and_tick_and_opens_the_links_settings(api, held):
    deal, link = held
    row = nudge_row(api, deal)
    assert row['label'] == 'Nudge Casey (synthetic) about their form' and row['chip'] == 'Nudge'
    assert (row['section'], row['date']) == ('up_next', day(2))
    assert row['can'] == {'tick': True, 'later': True}
    assert row['link'] == f'/deals/{deal.id}/review?view=request&target=link%3A{link.id}&settings={link.id}'
    assert row['later_max'] == (clock.local(link.expires_at).date() - timedelta(days=1)).isoformat()


def test_I37_I39_later_moves_the_reminder_through_review_to_the_mover(api, user, held):
    deal, link = held
    answer = post(api, deal, link.id, {'kind': 'later', 'until': day(4), 'note': 'They are out until Monday'})
    assert answer.status_code == 200, answer.content
    assert answer.json()['nudge']['date'] == day(4) and answer.json()['nudge']['section'] == 'up_next'
    assert nudge_of(link)['on'] == day(4) and nudge_of(link)['by'] == user.id
    assert reviews(deal, 'nudge') == 2  # set in the settings card, then moved here: review's own rows
    assert not Activity.objects.filter(deal=deal, area='agenda').exists()
    note = Note.objects.get(deal=deal)
    assert note.body.startswith('Task moved to ') and note.body.endswith(': They are out until Monday')
    again = post(api, deal, link.id, {'kind': 'later', 'until': day(4), 'note': 'They are out until Monday'})
    assert again.status_code == 200 and reviews(deal, 'nudge') == 2 and Note.objects.filter(deal=deal).count() == 1


def test_I15_I36_later_on_or_past_the_day_the_link_runs_out_is_refused_with_reviews_sentence(api, held):
    deal, link = held
    ends = clock.local(link.expires_at).date().isoformat()
    answer = post(api, deal, link.id, {'kind': 'later', 'until': ends})
    assert answer.status_code == 400 and 'before the link runs out' in str(answer.json())
    past = post(api, deal, link.id, {'kind': 'later', 'until': day(-1)})
    assert past.status_code == 400
    assert nudge_of(link)['on'] == day(2)


def test_I36_I38_a_link_that_ran_out_refuses_later_and_its_row_goes_quiet(api, held):
    deal, link = held
    ClientLink.objects.filter(pk=link.pk).update(expires_at=clock.now() - timedelta(hours=1))
    assert nudge_row(api, deal) is None
    answer = post(api, deal, link.id, {'kind': 'later', 'until': day(3)})
    assert answer.status_code == 409 and 'run out' in answer.json()['detail']
    assert nudge_of(link)['on'] == day(2)


def test_I37_I39_tick_stamps_the_reminder_done_and_it_stays_in_done(api, user, held):
    deal, link = held
    answer = post(api, deal, link.id, {'kind': 'done'})
    assert answer.status_code == 200, answer.content
    row = answer.json()['nudge']
    assert row['section'] == 'done' and row['can'] == {'tick': False, 'later': False} and row['link'] is None
    assert nudge_of(link)['done_by'] == user.id and nudge_of(link)['done_at']
    assert Activity.objects.get(deal=deal, area='review', action='nudge_done').summary == 'Nudge done'
    assert nudge_row(api, deal)['section'] == 'done'
    assert post(api, deal, link.id, {'kind': 'done'}).status_code == 200 and reviews(deal, 'nudge_done') == 1
    later = post(api, deal, link.id, {'kind': 'later', 'until': day(3)})
    assert later.status_code == 409 and nudge_of(link)['done_at']


def test_I37_with_no_reminder_on_the_link_tick_and_later_are_refused(api, user):
    deal = make_deal(user, name='No Reminder Co. (synthetic)')
    link = sent_ask(user, deal, days_ago=1)
    for body in ({'kind': 'done'}, {'kind': 'later', 'until': day(3)}):
        answer = post(api, deal, link.id, body)
        assert answer.status_code == 409 and answer.json()['detail'] == 'There is no reminder to nudge on this link.'
    assert nudge_of(link) == {} and nudge_row(api, deal) is None


def test_I36_a_lost_deal_refuses_later(api, user, held):
    deal, link = held
    mark_lost(user, deal.id, reason='')
    assert post(api, deal, link.id, {'kind': 'later', 'until': day(3)}).status_code == 409
    assert nudge_of(link)['on'] == day(2)


def test_I37_a_bad_request_is_400_and_another_deals_link_is_404(api, user, held):
    deal, link = held
    other = make_deal(user, name='Other Co. (synthetic)')
    assert post(api, other, link.id, {'kind': 'done'}).status_code == 404
    assert post(api, deal, link.id, {'kind': 'snooze'}).status_code == 400
    assert post(api, deal, link.id, {'kind': 'later', 'until': 'soon'}).status_code == 400
    assert post(api, deal, link.id, {'kind': 'later'}).status_code == 400
    assert nudge_of(link)['on'] == day(2) and not nudge_of(link).get('done_at')
