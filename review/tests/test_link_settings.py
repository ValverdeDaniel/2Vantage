"""One person's link settings and the reminder to nudge (plan.md §7.13 `PATCH links/{id}/`; L39, L61, L63, L66, L69;
I35–I39): each acts at once, locks Deal → request → link, records Activity, writes nothing when nothing changes, and
Revert puts it back; `set_nudge` and `finish_nudge` are the only writers Agenda calls."""

from datetime import timedelta

import pytest

from deals import activity, clock
from deals.models import Activity
from deals.services import mark_lost
from review import services
from review.models import ClientLink

from .portal_world import make_request

pytestmark = pytest.mark.django_db

ASK = {'intake': {'scope': 'missing'}}


def patch(api, link, **body):
    return api.patch(f'/api/links/{link.id}/', body, format='json')


def day(n):
    return (clock.today() + timedelta(days=n)).isoformat()


def test_L61_a_picked_day_ends_the_link_that_night_and_stops_the_slide(api, user, deal):
    link, _token, _pin = make_request(user, deal, ASK)
    answer = patch(api, link, action='expiry', day=day(3))
    assert answer.status_code == 200, answer.content
    fresh = ClientLink.objects.get(pk=link.pk)
    local = clock.local(fresh.expires_at)
    assert (local.date().isoformat(), local.hour, fresh.slides) == (day(3), 23, False)
    assert answer.json()['link']['slides'] is False
    assert patch(api, link, action='expiry', day=day(3)).json()['activity_id'] is None  # the same day: nothing
    assert patch(api, link, action='expiry', day=day(-1)).status_code == 400
    assert patch(api, link, action='expiry', day=day(40)).status_code == 400


def test_L61_revert_puts_the_date_and_the_slide_back(user, deal):
    link, _token, _pin = make_request(user, deal, ASK)
    before = ClientLink.objects.get(pk=link.pk).expires_at
    acted = services.set_expiry(user, link.id, day(2))
    activity.revert(acted.activity.id, user)
    fresh = ClientLink.objects.get(pk=link.pk)
    assert (fresh.expires_at, fresh.slides) == (before, True)


def test_L66_blank_is_set_and_put_back(api, user, deal):
    link, _token, _pin = make_request(user, deal, ASK)
    answer = patch(api, link, action='blank', blank=True)
    assert answer.status_code == 200 and ClientLink.objects.get(pk=link.pk).blank
    activity.revert(answer.json()['activity_id'], user)
    assert not ClientLink.objects.get(pk=link.pk).blank
    assert patch(api, link, action='blank', blank='yes').status_code == 400


def test_L63_the_address_changes_only_until_someone_opens_it_and_never_enters_activity(api, user, deal):
    link, _token, _pin = make_request(user, deal, ASK, people=[{'name': 'Dana', 'email': 'dana@exmaple.com'}])
    answer = patch(api, link, action='address', email='dana@example.com')
    assert answer.status_code == 200 and ClientLink.objects.get(pk=link.pk).email == 'dana@example.com'
    row = Activity.objects.get(pk=answer.json()['activity_id'])
    assert 'example.com' not in str(row.changes) + row.summary and not row.revertible
    assert patch(api, link, action='address', email='not an address').status_code == 400
    ClientLink.objects.filter(pk=link.pk).update(opened_at=clock.now())
    assert patch(api, link, action='address', email='other@example.com').status_code == 409


def test_I36_a_nudge_is_today_or_later_and_before_the_link_runs_out(user, deal):
    link, _token, _pin = make_request(user, deal, ASK)
    acted = services.set_nudge(user, link.id, day(2))
    nudge = ClientLink.objects.get(pk=link.pk).nudge
    assert (nudge['on'], nudge['by']) == (day(2), user.id) and acted.activity.action == 'nudge'
    assert services.set_nudge(user, link.id, day(2)).activity is None  # the same day again: nothing
    for wrong in (day(-1), day(7)):
        with pytest.raises(Exception) as refused:
            services.set_nudge(user, link.id, wrong)
        assert getattr(refused.value, 'status_code', None) == 400
    services.revoke(user, link.id)
    with pytest.raises(activity.Refused):
        services.set_nudge(user, link.id, day(1))


def test_I39_clearing_takes_it_off_and_finishing_stamps_it_done(user, deal):
    link, _token, _pin = make_request(user, deal, ASK)
    with pytest.raises(activity.Refused):
        services.finish_nudge(user, link.id)
    services.set_nudge(user, link.id, day(1))
    done = services.finish_nudge(user, link.id)
    nudge = ClientLink.objects.get(pk=link.pk).nudge
    assert nudge['done_by'] == user.id and nudge['done_at'] and done.activity.summary == 'Nudge done'
    assert services.finish_nudge(user, link.id).activity is None
    services.set_nudge(user, link.id, None)
    assert ClientLink.objects.get(pk=link.pk).nudge == {}


def test_I37_agenda_and_the_card_reach_the_same_writers_by_patch(api, user, deal):
    link, _token, _pin = make_request(user, deal, ASK)
    assert patch(api, link, action='nudge', day=day(1)).status_code == 200
    answer = patch(api, link, action='nudge_done')
    assert answer.status_code == 200 and answer.json()['link']['nudge_done_at']
    activity.revert(answer.json()['activity_id'], user)
    assert not ClientLink.objects.get(pk=link.pk).nudge.get('done_at')


def test_L69_a_lost_deal_takes_no_new_reminder(user, deal):
    link, _token, _pin = make_request(user, deal, ASK)
    mark_lost(user, deal.id, 'price')
    with pytest.raises(activity.Refused):
        services.set_nudge(user, link.id, day(1))
