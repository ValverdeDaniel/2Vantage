"""`order.layout` and the moves (plan.md §5.4; F43–F48, F120, J4–J6; OQ13), table-driven over plain plans.

A plan is written `id:role[>links][~original]@sort_order`: `5:alternate>1,2@4` replaces current plans 1 and 2;
`7:alternate~5@6` is a priced version of plan 5; `3:renewal>1@2` renews plan 1.
"""

import pytest

from quotes import order
from quotes.shapes import LineData, PlanData


def plan(spec, basis='composite'):
    head, _, number = spec.partition('@')
    head, _, original = head.partition('~')
    head, _, links = head.partition('>')
    pid, role = head.split(':')
    ids = tuple(int(x) for x in links.split(',')) if links else ()
    return PlanData(
        id=int(pid),
        role=role,
        renews=ids[0] if role == 'renewal' and ids else None,
        replaces=ids if role == 'alternate' else (),
        version_of=int(original) if original else None,
        sort_order=int(number),
        carrier='Carrier',
        name=f'Plan {pid}',
    )


def line(*specs, basis='composite'):
    return LineData(basis, [plan(spec) for spec in specs])


def ids(plans):
    return [p if isinstance(p, int) else p.id for p in plans]


GD1_LIKE = [
    '1:current@0',
    '2:current@1',
    '3:current@2',
    '4:renewal>1@3',
    '5:renewal>2@4',
    '6:renewal>3@5',
    '7:alternate>1@6',
    '8:alternate>2@7',
    '9:alternate>2,3@8',  # a consolidation: under the first plan it replaces
    '10:alternate@9',  # replaces none: last
    '11:alternate>1@10',
]


@pytest.mark.parametrize(
    'case, specs, expected',
    [
        ('current plans first, then each group, unlinked last', GD1_LIKE, [1, 2, 3, 4, 7, 11, 5, 8, 9, 6, 10]),
        (
            'current plans in slot order; their groups follow',
            ['1:current@5', '2:current@1', '3:alternate>1@2', '4:alternate>2@3'],
            [2, 1, 4, 3],
        ),
        (
            'hand order inside a group, never values',
            ['1:current@0', '2:alternate>1@9', '3:alternate>1@4', '4:renewal>1@6'],
            [1, 3, 4, 2],
        ),
        (
            'a priced version rides right behind its original',
            ['1:current@0', '2:alternate>1@1', '3:alternate>1@2', '4:alternate~2@3'],
            [1, 2, 4, 3],
        ),
        (
            'a priced version of a current plan leads with the current plans',
            ['1:current@0', '2:current@1', '3:alternate~1@2', '4:alternate>1@3'],
            [1, 2, 3, 4],
        ),
        (
            'one current plan: an unlinked alternate is compared with it',
            ['1:current@0', '2:alternate@1', '3:renewal>1@2', '4:alternate>1@3'],
            [1, 2, 3, 4],
        ),
        ('no current plans: the hand order', ['1:alternate@2', '2:alternate@0', '3:alternate@1'], [2, 3, 1]),
    ],
)
def test_F120_J4_layout(case, specs, expected):
    assert ids(order.layout(line(*specs))) == expected, case


def test_F120_OQ13_stop_loss_is_ordered_like_every_line():
    specs = ['1:current@0', '2:alternate>1@3', '3:alternate>1@1']
    assert ids(order.layout(line(*specs, basis='stop_loss'))) == [1, 3, 2]
    assert ids(order.move(line(*specs, basis='stop_loss'), 2, -1)) == [1, 2, 3]


def test_F120_a_rate_edit_moves_nothing():
    before = line(*GD1_LIKE)
    after = line(*GD1_LIKE)
    for p in after.plans:
        p.values = {'rate_ee': str(1000 - p.id)}  # dearer to cheaper, in the other direction
    assert ids(order.layout(after)) == ids(order.layout(before))


@pytest.mark.parametrize(
    'case, plan_id, step, among, expected',
    [
        ('a quote one place earlier in its group', 11, -1, None, [1, 2, 3, 4, 11, 7, 5, 8, 9, 6, 10]),
        ('past a hidden plan', 11, -1, [1, 2, 3, 4, 11], [1, 2, 3, 11, 4, 7, 5, 8, 9, 6, 10]),
        ('a current plan moves as a slot', 2, -1, None, [2, 1, 3, 4, 7, 11, 5, 8, 9, 6, 10]),
    ],
)
def test_F43_F44_move(case, plan_id, step, among, expected):
    assert order.move(line(*GD1_LIKE), plan_id, step, among) == expected, case


@pytest.mark.parametrize(
    'case, plan_id, step, sentence',
    [
        (
            'the end of its group',
            11,
            1,
            'Carrier Plan 11 is already last among the plans compared with Carrier Plan 1.',
        ),
        ('the first current plan', 1, -1, 'Carrier Plan 1 is already first among the current plans.'),
        ('two places at once', 7, 2, 'Move a plan one place at a time.'),
        ('another line', 99, 1, 'That plan is not on this line.'),
        ('unlinked and last', 10, 1, 'Carrier Plan 10 is already last.'),
    ],
)
def test_F43_a_refused_move_says_why(case, plan_id, step, sentence):
    with pytest.raises(order.Refused) as refused:
        order.move(line(*GD1_LIKE), plan_id, step)
    assert str(refused.value) == sentence, case


def test_F43_a_quote_moves_with_its_priced_versions():
    specs = ['1:current@0', '2:alternate>1@1', '3:alternate~2@2', '4:alternate>1@3']
    assert order.move(line(*specs), 4, -1) == [1, 4, 2, 3]
    with pytest.raises(order.Refused, match='priced version of a current plan'):
        order.move(line('1:current@0', '2:alternate~1@1'), 2, -1)


def test_F45_swap_last_and_lead():
    data = line(*GD1_LIKE)
    assert order.swap(data, 7, 11) == [1, 2, 3, 4, 11, 7, 5, 8, 9, 6, 10]
    assert order.last(data, 7)[-1] == 7  # last in the hand order: last in whichever group its links put it
    assert order.lead(data, 11) == [1, 2, 3, 11, 4, 7, 5, 8, 9, 6, 10]
    with pytest.raises(order.Refused, match='is a current plan'):
        order.swap(data, 1, 7)


def test_F48_reset_puts_the_renewal_first_then_the_quotes_as_added():
    shuffled = line('1:current@1', '2:current@0', '5:alternate>1@2', '3:renewal>1@3', '4:alternate>1@4')
    assert order.reset(shuffled) == [2, 1, 3, 4, 5]  # current plans keep their slots


def test_F44_a_current_plans_group_follows_its_slot():
    data = line(*GD1_LIKE)
    moved = order.numbering(data, order.move(data, 2, -1))
    for p in data.plans:
        p.sort_order = moved.get(p.id, p.sort_order)
    assert ids(order.layout(LineData(data.rate_basis, data.plans))) == [2, 1, 3, 5, 8, 9, 4, 7, 11, 6, 10]


def test_F43_numbering_rewrites_only_the_plans_that_move():
    data = line('1:current@0', '2:alternate>1@1', '3:alternate>1@2', '4:alternate>1@3')
    assert order.numbering(data, order.move(data, 2, 1)) == {3: 1, 2: 2}  # a step rewrites the two plans only
    tied = line('1:current@0', '2:alternate>1@0', '3:alternate>1@0')
    assert order.numbering(tied, [1, 3, 2]) == {2: 2, 3: 1}  # tied numbers are renumbered from 0
