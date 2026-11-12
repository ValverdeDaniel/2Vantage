"""`slots.prepare` (plan.md §5.4; F45, F46, J10, J11; OQ13), over plain plans: a pick changes stars, links and the
order and writes nothing."""

import pytest

from quotes import slots
from quotes.shapes import LineData, PlanData


def plan(pid, role='alternate', replaces=(), renews=None, starred=False, recommended=False, version_of=None):
    return PlanData(
        id=pid,
        role=role,
        carrier='Carrier',
        name=f'Plan {pid}',
        replaces=tuple(replaces),
        renews=renews,
        starred=starred,
        recommended=recommended,
        version_of=version_of,
        sort_order=pid,
    )


def two_currents(*quotes, basis='composite'):
    return LineData(basis, [plan(1, 'current'), plan(2, 'current'), *quotes])


def test_F45_a_plan_off_the_proposal_replaces_the_one_in_the_spot():
    line = two_currents(plan(3, replaces=[1], starred=True, recommended=True), plan(4, replaces=[2]))
    placement = slots.prepare(line, 'Medical', 4, at=3)
    assert (placement.stars_on, placement.stars_off, placement.unrecommend) == ([4], [3], [3])
    assert placement.links == {4: [1]}  # the picked plan takes the spot's links; the leaving plan keeps its own
    assert placement.order.index(4) < placement.order.index(3)  # it takes the spot's place


def test_F45_two_plans_on_the_proposal_trade_places_and_whole_replaces_sets():
    line = two_currents(plan(3, replaces=[1], starred=True), plan(4, replaces=[1, 2], starred=True))
    placement = slots.prepare(line, 'Medical', 4, at=3)
    assert (placement.stars_on, placement.stars_off, placement.unrecommend) == ([], [], [])
    assert placement.links == {4: [1], 3: [1, 2]}


def test_F45_one_current_plan_trades_no_links():
    line = LineData('composite', [plan(1, 'current'), plan(3, starred=True), plan(4)])
    assert slots.prepare(line, 'Medical', 4, at=3).links == {}


@pytest.mark.parametrize(
    'case, quotes, picked, at, sentence',
    [
        (
            'a current plan never takes a spot',
            [plan(3, replaces=[1])],
            1,
            3,
            'Carrier Plan 1 is a current plan: current plans lead each page, and their arrows move them.',
        ),
        (
            'nor a priced version',
            [plan(3, replaces=[1]), plan(4, version_of=3)],
            4,
            3,
            'Carrier Plan 4 is a priced version: it moves with its plan.',
        ),
        (
            'a renewal stays beside its plan',
            [plan(3, 'renewal', renews=1), plan(4, replaces=[2], starred=True)],
            3,
            4,
            'Carrier Plan 3 is the renewal of Carrier Plan 1: it stays beside that plan.',
        ),
        ('already there', [plan(3, replaces=[1])], 3, 3, 'Carrier Plan 3 is already there.'),
        ('another line', [plan(3, replaces=[1])], 3, 99, 'That spot is not on this line.'),
    ],
)
def test_F45_a_refused_pick_says_why(case, quotes, picked, at, sentence):
    with pytest.raises(slots.Refused) as refused:
        slots.prepare(two_currents(*quotes), 'Medical', picked, at=at)
    assert str(refused.value) == sentence, case


def test_F46_add_a_plan_beside_a_current_plan():
    line = two_currents(plan(3, replaces=[1], starred=True), plan(4), plan(5, replaces=[2]))
    placement = slots.prepare(line, 'Medical', 4, beside=2)
    assert placement.stars_on == [4] and placement.links == {4: [2]}
    assert placement.order[-1] == 4  # last in the hand order: last among the plans compared with plan 2
    with pytest.raises(slots.Refused, match='Add a plan beside a current plan on this line.'):
        slots.prepare(line, 'Medical', 4, beside=3)


def test_F46_adding_past_16_columns_is_refused_with_the_room_sentence():
    full = two_currents(*[plan(pid, replaces=[1], starred=True) for pid in range(3, 17)], plan(17))
    with pytest.raises(slots.Refused, match=r'^The Medical proposal holds 16 plans \(2 current, 14 starred\)'):
        slots.prepare(full, 'Medical', 17, beside=1)


def test_OQ13_a_stop_loss_quote_takes_a_slot_pick():
    line = two_currents(plan(3, replaces=[1], starred=True), plan(4, replaces=[2]), basis='stop_loss')
    placement = slots.prepare(line, 'Stop-loss', 4, at=3)
    assert placement.stars_on == [4] and placement.links == {4: [1]}
