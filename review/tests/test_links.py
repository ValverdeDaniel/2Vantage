"""What a person does to one link (plan.md §7.13; L8, L58, L60–L64, L71, L77; Q.9 row 53): Copy and Mark sent and
their undo, Extend, Turn off and back on, New PIN, the five-try lock, each with its refusals and its Undo."""

from datetime import timedelta
from unittest import mock

import pytest

from conftest import write_path_contract
from deals import activity, clock
from deals.services import mark_lost
from review import services
from review.models import ClientLink
from review.rules import policy
from review.services import pins

pytestmark = pytest.mark.django_db


def make_link(user, deal, *, asks=None, people=None, security='link'):
    body = {
        'asks': asks or {'intake': {'scope': 'missing'}},
        'people': people or [{'name': 'Dana'}],
        'security': security,
    }
    made = services.create(user, deal.id, body)
    link, _path, pin = made.links[0]
    return link, pin


def fresh(link):
    return ClientLink.objects.get(pk=link.pk)


def at(moment):
    return mock.patch.object(clock, 'now', return_value=moment)


def test_L71_Q3_1_copying_marks_sent_once_and_undo_puts_it_back(user, deal):
    link, _pin = make_link(user, deal)
    write_path_contract(
        user,
        link,
        lambda: services.mark_sent(user, link.id, copied=True),
        lambda row: row.sent_at,
        lambda: services.unsend(user, link.id),
    )


def test_L71_copying_words_the_row_and_never_restamps(user, deal):
    link, _pin = make_link(user, deal)
    first = services.mark_sent(user, link.id, copied=True)
    assert first.activity.summary == 'Copied a client link'
    stamped = fresh(link).sent_at
    again = services.mark_sent(user, link.id, copied=True)
    assert (again.changed, again.activity, fresh(link).sent_at) == ({}, None, stamped)


def test_L71_not_sent_after_all_is_refused_once_the_link_was_opened(user, deal):
    link, _pin = make_link(user, deal)
    sent = services.mark_sent(user, link.id)
    ClientLink.objects.filter(pk=link.pk).update(opened_at=clock.now(), open_count=1)
    with pytest.raises(activity.Refused) as refused:
        services.unsend(user, link.id)
    assert refused.value.sentence == 'This link was opened — it went out.'
    with pytest.raises(activity.Refused):
        activity.revert(sent.activity.id, user)  # Undo of the copy says the same
    assert fresh(link).sent_at is not None


def test_L60_Q3_1_turning_off_and_undo_turns_it_back_on(user, deal):
    link, _pin = make_link(user, deal)
    write_path_contract(
        user,
        link,
        lambda: services.revoke(user, link.id),
        lambda row: (row.revoked_at, row.revoked_by_id),
        lambda: services.restore(user, link.id),
    )


def test_L60_a_link_turned_off_stops_opening_and_survives_extend(user, deal):
    link, _pin = make_link(user, deal)
    services.revoke(user, link.id)
    row = fresh(link)
    assert not policy.opens(row, clock.now()) and row.revoked_by_id == user.id
    with pytest.raises(activity.Refused) as refused:
        services.extend(user, link.id)
    assert refused.value.sentence == 'This link is turned off: turn it back on first.'
    assert fresh(link).revoked_at is not None


def test_L60_turning_off_is_allowed_on_a_lost_deal_and_a_closed_request(user, deal):
    link, _pin = make_link(user, deal)
    services.close(user, link.request_id, 'cancelled')
    mark_lost(user, deal.id, reason='Went elsewhere')
    assert services.revoke(user, link.id).changed


def test_L60_turning_back_on_gives_its_own_life_within_the_ceiling(user, deal):
    link, _pin = make_link(user, deal)
    services.revoke(user, link.id)
    later = clock.now() + timedelta(days=26)
    with at(later):
        services.restore(user, link.id)
    row = fresh(link)
    assert row.revoked_at is None and row.expires_at == row.ceiling_at  # 26 + 7 days is past the ceiling
    services.revoke(user, link.id)
    with at(row.ceiling_at + timedelta(minutes=1)), pytest.raises(activity.Refused) as refused:
        services.restore(user, link.id)
    assert 'past its 30-day limit' in refused.value.sentence


def test_L58_Q3_1_extend_gives_the_link_its_life_again(user, deal):
    link, _pin = make_link(user, deal)
    with at(clock.now() + timedelta(days=3)):
        write_path_contract(
            user,
            link,
            lambda: services.extend(user, link.id),
            lambda row: row.expires_at,
            lambda: services.extend(user, link.id),
        )


def test_L58_extend_brings_back_a_link_that_ran_out_but_never_past_the_ceiling(user, deal):
    link, _pin = make_link(user, deal)
    row = fresh(link)
    with at(row.created_at + timedelta(days=10)):
        assert not policy.opens(fresh(link), clock.now())
        services.extend(user, link.id)
        assert policy.opens(fresh(link), clock.now())
    with at(row.created_at + timedelta(days=29)):
        services.extend(user, link.id)
        assert fresh(link).expires_at == row.ceiling_at
        with pytest.raises(activity.Refused) as refused:
            services.extend(user, link.id)
    assert 'cannot live any longer' in refused.value.sentence


def test_L64_new_pin_unlocks_the_link_and_the_old_pin_stops_working(user, deal):
    link, first = make_link(user, deal, security='pin')
    for _ in range(policy.PIN_TRIES):
        pins.check(link.id, '000000' if first != '000000' else '111111')
    assert pins.check(link.id, first).outcome == pins.LOCKED  # five wrong tries lock it, even for the right PIN
    made = services.new_pin(user, link.id)
    assert made.pin and made.changed == {'pin_version': [1, 2]}
    if made.pin != first:  # one in a million draws the same six digits again
        assert pins.check(link.id, first).outcome == pins.WRONG
    assert pins.check(link.id, made.pin).outcome == pins.OK
    row = fresh(link)
    assert (row.pin_tries, row.pin_version) == (0, 2) and made.pin not in str(made.activity.changes)


def test_L77_Q9_a_pin_locks_after_five_wrong_tries(user, deal):
    link, pin = make_link(user, deal, security='pin')
    wrong = '000000' if pin != '000000' else '111111'
    outcomes = [pins.check(link.id, wrong) for _ in range(policy.PIN_TRIES)]
    assert [o.outcome for o in outcomes] == [pins.WRONG] * 4 + [pins.LOCKED]
    assert [o.tries_left for o in outcomes] == [4, 3, 2, 1, 0]
    assert pins.check(link.id, pin).outcome == pins.LOCKED


def test_L77_a_right_pin_starts_the_tries_over(user, deal):
    link, pin = make_link(user, deal, security='pin')
    wrong = '000000' if pin != '000000' else '111111'
    pins.check(link.id, wrong)
    assert pins.check(link.id, pin) == (pins.OK, policy.PIN_TRIES)
    assert fresh(link).pin_tries == 0


def test_L64_a_private_link_has_no_pin_to_check_or_renew(user, deal):
    link, pin = make_link(user, deal)
    assert pin == '' and pins.check(link.id, '123456').outcome == pins.NONE
    with pytest.raises(activity.Refused) as refused:
        services.new_pin(user, link.id)
    assert refused.value.sentence == 'This link does not ask for a PIN.'


def test_L64_a_new_pin_cannot_be_undone(user, deal):
    link, _pin = make_link(user, deal, security='pin')
    made = services.new_pin(user, link.id)
    assert made.activity.revertible is False
    with pytest.raises(activity.Refused) as refused:
        activity.revert(made.activity.id, user)
    assert 'shown once' in refused.value.sentence


@pytest.mark.parametrize('action', ['mark_sent', 'extend', 'restore', 'new_pin'])
def test_B10_actions_that_ask_the_client_are_refused_once_the_deal_is_lost(user, deal, action):
    link, _pin = make_link(user, deal, security='pin')
    if action == 'restore':
        services.revoke(user, link.id)
    mark_lost(user, deal.id, reason='Went elsewhere')
    with pytest.raises(activity.Refused) as refused:
        services.ACTIONS[action](user, link.id)
    assert 'marked lost' in refused.value.sentence


@pytest.mark.parametrize('action', ['mark_sent', 'extend', 'restore', 'new_pin'])
def test_L70_actions_on_a_closed_request_are_refused(user, deal, action):
    link, _pin = make_link(user, deal, security='pin')
    if action == 'restore':
        services.revoke(user, link.id)
    services.close(user, link.request_id, 'superseded')
    with pytest.raises(activity.Refused) as refused:
        services.ACTIONS[action](user, link.id)
    assert refused.value.sentence == 'That request is closed: send a new one.'


def test_Q3_1_undo_of_turning_off_is_refused_after_a_later_write_to_the_link(user, deal):
    link, _pin = make_link(user, deal)
    off = services.revoke(user, link.id)
    services.restore(user, link.id)
    with pytest.raises(activity.Refused) as refused:
        activity.revert(off.activity.id, user)
    assert refused.value.keys
