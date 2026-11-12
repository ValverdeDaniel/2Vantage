"""The one page splitter (plan.md §5.4, §9.5; J.6.3, J.6.10 "splitter table cases"; F37, F38, J49; D-221). Pure:
no database. Each case is the old app's rule (7385bb3 `presentation_model`) on plain columns."""

import pytest

from proposals import pages
from proposals.pages import Column


def cur(pid, carrier='aetna'):
    return Column(pid, True, True, carrier, carrier.title(), None, None, False)


def opt(pid, carrier='cigna', group=None, renews=None, version=False, lead=False):
    return Column(pid, False, lead, carrier, carrier.title(), group, renews, version)


def ids(found):
    return [page['plan_ids'] for page in found]


@pytest.mark.parametrize(
    ('lead', 'titles', 'groups', 'per_page', 'first', 'later'),
    [
        (1, 1, [5], 6, [(0, 0, 5)], []),  # one current and five options: one full page
        (1, 1, [6], 6, [(0, 0, 5)], [(0, 5, 1)]),  # the sixth option starts page two beside the current plan
        (2, 2, [3, 4], 6, [(0, 0, 3)], [(1, 0, 4)]),  # each later carrier run starts a page
        (3, 3, [10], 6, [(0, 0, 3)], [(0, 3, 3), (0, 6, 3), (0, 9, 1)]),  # three repeated currents leave three
        (7, 7, [2], 6, [(0, 0, 1)], [(0, 1, 1)]),  # a lead wider than a page still takes one plan a run
        (0, 0, [], 6, [], []),
    ],
)
def test_F38_split_on_counts(lead, titles, groups, per_page, first, later):
    assert pages.split(lead, titles, groups, per_page) == (first, later)


def test_F37_by_carrier_page_one_holds_the_current_plan_and_the_first_run():
    columns = [cur(1), opt(2, 'cigna'), opt(3, 'cigna'), opt(4, 'uhc'), opt(5, 'uhc')]
    found = pages.sequence(columns)
    assert ids(found) == [[1, 2, 3], [1, 4, 5]]
    assert found[0]['carrier'] == 'Cigna' and found[1]['carrier'] == 'Uhc'
    assert found[1]['repeat_ids'] == [1] and found[0]['repeat_ids'] == []


def test_F38_six_plans_a_slide_and_a_carrier_continues_onto_the_next():
    columns = [cur(1)] + [opt(pid, 'cigna') for pid in range(2, 10)]
    found = pages.sequence(columns)
    assert ids(found) == [[1, 2, 3, 4, 5, 6], [1, 7, 8, 9]]
    assert [page['continued'] for page in found] == [False, True]


def test_F37_a_line_with_no_current_plan_repeats_nothing():
    found = pages.sequence([opt(pid, 'cigna') for pid in range(1, 9)])
    assert ids(found) == [[1, 2, 3, 4, 5, 6], [7, 8]]
    assert found[1]['repeat_ids'] == []


def test_F37_several_current_plans_repeat_until_an_option_is_linked():
    columns = [cur(1), cur(2), opt(3, 'cigna'), opt(4, 'cigna'), opt(5, 'cigna'), opt(6, 'uhc')]
    assert ids(pages.sequence(columns)) == [[1, 2, 3, 4, 5], [1, 2, 6]]  # a new carrier starts a page
    columns = [cur(1), cur(2), opt(3, 'cigna'), opt(4, 'uhc'), opt(5, 'uhc'), opt(6, 'uhc'), opt(7, 'uhc')]
    found = pages.sequence(columns)
    assert ids(found) == [[1, 2, 3], [1, 2, 4, 5, 6, 7]]
    assert found[1]['repeat_ids'] == [1, 2]


def test_F37_J12_pages_by_current_plan_once_options_are_linked():
    columns = [
        cur(1),
        cur(2),
        cur(3),
        opt(4, group=1),
        opt(5, group=1),
        opt(6, group=2),
        opt(7, group=None),
    ]
    captions = {1: 'Replacing: Aetna A', 2: 'Replacing: Aetna B', 3: 'Replacing: Aetna C'}
    found = pages.sequence(columns, captions)
    assert ids(found) == [[1, 4, 5], [2, 6], [3], [7]]
    assert [page['caption'] for page in found] == [
        'Replacing: Aetna A',
        'Replacing: Aetna B',
        pages.NO_OPTIONS,
        pages.OTHER_OPTIONS,
    ]
    assert [page['current_id'] for page in found] == [1, 2, None, None]


def test_F37_by_current_plan_a_long_group_continues_beside_its_plan_alone():
    columns = [cur(1), cur(2)] + [opt(pid, group=1) for pid in range(3, 11)] + [opt(11, group=2)]
    found = pages.sequence(columns, {1: 'Replacing: A', 2: 'Replacing: B'})
    assert ids(found) == [[1, 3, 4, 5, 6, 7], [1, 8, 9, 10], [2, 11]]
    assert found[1]['repeat_ids'] == [1] and found[1]['continued']


def test_F37_a_priced_version_of_a_current_plan_leads_with_it():
    columns = [cur(1), opt(2, lead=True, version=True, group=1), opt(3, 'cigna')]
    assert ids(pages.sequence(columns)) == [[1, 2, 3]]
    assert pages.leading(columns) == [1, 2]


@pytest.mark.parametrize(
    ('count', 'sizes'),
    [(1, [1]), (2, [2]), (3, [3]), (4, [2, 2]), (5, [3, 2]), (6, [3, 3]), (7, [3, 2, 2]), (0, [])],
)
def test_J49_renewal_pairs_three_a_slide_shared_evenly_never_split(count, sizes):
    pairs = [[n, n + 100] for n in range(count)]
    slides = pages.pair_slides(pairs, 6)
    assert [len(chunk) for chunk in slides] == sizes
    assert [pair for chunk in slides for pair in chunk] == pairs


def test_J49_the_renewal_page_comes_first_and_answers_for_its_plans():
    columns = [
        cur(1),
        cur(2),
        opt(3, 'aetna', group=1, renews=1),
        opt(4, 'aetna', group=2, renews=2),
        opt(5, 'cigna', group=1),
    ]
    found = pages.sequence(columns, {1: 'Replacing: A', 2: 'Replacing: B'})
    assert [page['part'] for page in found] == ['renewal', 'options']
    assert ids(found) == [[1, 3, 2, 4], [1, 5]]  # B has no options left: no page of its own


def test_J49_the_renewal_page_prefers_a_priced_version_of_the_renewal():
    columns = [
        cur(1),
        cur(2),
        opt(3, group=1, renews=1),
        opt(4, group=1, renews=1, version=True),
        opt(5, group=2, renews=2),
    ]
    found = pages.sequence(columns)
    assert ids(found)[0] == [1, 4, 2, 5]


def test_J49_no_renewal_page_unless_every_current_plan_has_its_offer():
    columns = [cur(1), cur(2), opt(3, group=1, renews=1), opt(4, group=2)]
    assert [page['part'] for page in pages.sequence(columns)] == ['options', 'options']
    assert [page['part'] for page in pages.sequence(columns, presentation=False)] == ['options', 'options']


def test_F37_side_by_side_and_best_only_layouts():
    columns = [cur(1), opt(2, 'cigna'), opt(3, 'uhc'), opt(4, 'uhc')]
    assert ids(pages.sequence(columns, layout='side_by_side')) == [[1, 2, 3, 4]]
    assert ids(pages.sequence(columns, layout='best_only', picks=[3])) == [[1, 3]]
    assert ids(pages.sequence(columns, layout='best_only', picks=[99])) == [[1, 2], [1, 3, 4]]  # no pick shown


def test_J159_reading_order_is_first_appearance():
    found = [{'plan_ids': [1, 2, 3]}, {'plan_ids': [1, 4]}, {'plan_ids': [5, 2]}]
    assert pages.reading_order(found) == [1, 2, 3, 4, 5]
    assert pages.first_pages(found) == {1: 1, 2: 1, 3: 1, 4: 2, 5: 3}


def test_F37_no_plans_no_pages():
    assert pages.sequence([]) == []
