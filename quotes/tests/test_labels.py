"""Option numbers (plan.md §5.4; J159, OQ35, OQ36): `labels.numbers` (pure) and `stamp_option_numbers`."""

import pytest

from deals import activity
from quotes import labels
from quotes import services as plans
from quotes.models import Plan
from quotes.shapes import PlanData


def _plan(pid, role='alternate', version_of=None):
    return PlanData(id=pid, role=role, version_of=version_of)


def test_J159_numbers_follow_reading_order_and_skip_current_plans_and_priced_versions():
    order = [_plan(1, 'current'), _plan(2, 'renewal'), _plan(3), _plan(4, version_of=3), _plan(5)]
    assert labels.numbers(order, {}) == {2: 1, 3: 2, 5: 3}


def test_J159_a_stored_number_stays_and_new_ones_follow_the_highest_never_reusing_one():
    order = [_plan(5), _plan(2), _plan(3)]
    assert labels.numbers(order, {2: 1}) == {5: 2, 2: 1, 3: 3}
    # Plan 9 (not shown, or removed) holds 4: nothing on the line takes 4 again.
    assert labels.numbers(order, {2: 1}, top=4) == {5: 5, 2: 1, 3: 6}


@pytest.fixture
def line(user, deal):
    current = plans.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='PPO')
    renewal = plans.create_renewal(user, current.id)
    quotes = [
        plans.create_plan(user, deal, line='medical', role='alternate', carrier='Cigna', name=name)
        for name in ('HDHP', 'EPO', 'HMO')
    ]
    return current, renewal, quotes


@pytest.mark.django_db
def test_J159_stamping_numbers_the_plans_once_and_again_writes_nothing(user, deal, line):
    current, renewal, (hdhp, epo, hmo) = line
    order = [current.id, renewal.id, epo.id, hdhp.id]
    assert plans.stamp_option_numbers(deal, order) == {renewal.id: 1, epo.id: 2, hdhp.id: 3}
    assert plans.stamp_option_numbers(deal, order) == {}
    assert plans.stamp_option_numbers(deal, [hmo.id, epo.id]) == {hmo.id: 4}  # past the highest, never reused
    assert Plan.objects.get(pk=current.id).option_number is None


@pytest.mark.django_db
def test_J159_a_removed_plan_keeps_its_number_and_no_one_takes_it(user, deal, line):
    _current, _renewal, (hdhp, epo, hmo) = line
    plans.stamp_option_numbers(deal, [hdhp.id, epo.id])
    plans.delete_plans(user, deal, [epo.id])
    assert plans.stamp_option_numbers(deal, [hmo.id]) == {hmo.id: 3}


@pytest.mark.django_db
def test_J159_a_move_to_another_line_renumbers_and_revert_brings_the_number_back(user, deal, line):
    _current, _renewal, (hdhp, epo, _hmo) = line
    plans.stamp_option_numbers(deal, [hdhp.id, epo.id])
    _moved, row = plans.move_line(user, deal, [epo.id], 'dental')
    assert Plan.objects.get(pk=epo.id).option_number is None
    activity.revert(row.id, user)
    moved_back = Plan.objects.get(pk=epo.id)
    assert (moved_back.line, moved_back.option_number) == ('medical', 2)
    _moved, row = plans.move_line(user, deal, [epo.id], 'dental')
    assert plans.stamp_option_numbers(deal, [epo.id]) == {epo.id: 1}  # it starts again on dental
    with pytest.raises(activity.Refused) as refused:
        activity.revert(row.id, user)  # numbered on dental since: the move stays
    assert refused.value.keys == ['plan.option_number']


@pytest.mark.django_db
def test_J159_a_move_back_is_refused_when_its_number_was_given_since(user, deal, line):
    _current, _renewal, (hdhp, epo, hmo) = line
    plans.stamp_option_numbers(deal, [hdhp.id, epo.id])
    _moved, row = plans.move_line(user, deal, [epo.id], 'dental')
    assert plans.stamp_option_numbers(deal, [hmo.id]) == {hmo.id: 2}
    with pytest.raises(activity.Refused) as refused:
        activity.revert(row.id, user)
    assert 'would both be Option 2 on Medical.' in refused.value.sentence
