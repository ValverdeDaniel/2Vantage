"""One plan filed under two plan numbers, printed as one column (plan.md §5.4, §5.5, §7.8; D-219, J15, F137, O.6 #4;
slice 33): which pairs fold (`pairs`), a pair counting once against the 16 columns (`presented`), the pair priced as
`package()` of its halves (`packages.folded`), and the pairing door with its refusals (`services.pairs`)."""

import pytest

from conftest import make_deal
from deals import activity
from quotes import packages as pk
from quotes import pairs, presented, services
from quotes.models import Plan
from quotes.shapes import LineData, PlanData

pytestmark = pytest.mark.django_db

A = PlanData(
    1,
    'current',
    'Aetna',
    'PPO 1500',
    values={'rate_ee': '640.25', 'rate_es': '1376.54', 'rate_ec': '1200.10', 'rate_fam': '1975.66'},
    enrollment={'EE': 8, 'ES': 2, 'EC': 1, 'FAM': 4},
)
EE_HALF = PlanData(
    2,
    'alternate',
    'Florida Blue',
    'HSA 05182',
    values={'rate_ee': '575.50'},
    enrollment={'EE': 8},
    replaces=(1,),
    starred=True,
    sort_order=1,
)
DEP_HALF = PlanData(
    3,
    'alternate',
    'Florida Blue',
    'HSA 05183',
    values={'rate_es': '1237.40', 'rate_ec': '1078.85', 'rate_fam': '1774.95'},
    enrollment={'ES': 2, 'EC': 1, 'FAM': 4},
    replaces=(1,),
    starred=True,
    sort_order=2,
    pair_of=2,
)


def line(*plans):
    return LineData('composite', list(plans), key='medical')


def test_J15_a_stored_pair_folds_only_where_both_halves_print():
    found = line(A, EE_HALF, DEP_HALF)
    assert pairs.found(found) == [(2, 3)]
    assert pairs.found(found, [1, 2]) == []
    assert pairs.columns(found, [1, 2, 3]) == 2
    assert pairs.partner(found, 2) == 3 and pairs.partner(found, 3) == 2
    other_kind = PlanData(4, 'alternate', 'Aetna', 'HMO', pair_of=1)
    assert pairs.stored(line(A, other_kind)) == [], 'a current plan and a quote are not one plan'


def test_J15_a_current_pairs_renewals_print_as_one_too():
    first = PlanData(1, 'current', 'Florida Blue', '05182')
    second = PlanData(2, 'current', 'Florida Blue', '05183', pair_of=1)
    renew_first = PlanData(3, 'renewal', 'Florida Blue', '05182', renews=1)
    renew_second = PlanData(4, 'renewal', 'Florida Blue', '05183', renews=2)
    found = line(first, second, renew_first, renew_second)
    assert pairs.found(found) == [(1, 2), (3, 4)]
    assert pairs.follows(found, 3) == 4 and pairs.follows(found, 4) == 3
    assert pairs.found(found, [1, 2, 3]) == [(1, 2)], 'a renewal pair needs both renewals on the proposal'


def test_J15_a_pair_counts_once_against_the_sixteen_columns():
    others = [PlanData(10 + n, 'alternate', 'Cigna', f'Plan {n}', starred=True, sort_order=10 + n) for n in range(13)]
    full = line(A, *others, EE_HALF, DEP_HALF)
    assert len(presented.held(full)) == presented.MAX_COLUMNS
    assert presented.columns(full) == presented.MAX_COLUMNS - 1
    assert presented.room(full) == 1
    unstarred = DEP_HALF.__class__(**{**DEP_HALF.__dict__, 'starred': False})
    half_held = line(A, *others, EE_HALF, unstarred)
    assert presented.added(half_held, [unstarred.id]) == 0, 'the half whose partner is held adds no column'
    assert presented.refusal(half_held, 'Medical', presented.added(half_held, [unstarred.id])) is None


def test_J15_the_pair_is_priced_as_its_package():
    found = line(A, EE_HALF, DEP_HALF)
    results = pk.evaluate(found)
    folded = pk.folded(found, results, [(2, 3)])
    package = pk.package([2, 3], found, results)
    assert 3 not in folded
    assert (folded[2]['monthly'], folded[2]['annual']) == (package['monthly'], package['annual']) == (15257, 183084)
    assert folded[2]['change'] == {'delta': 183084 - results[1]['annual'], 'pct': -10.1}, 'the same people as A'
    assert results[2]['change'] is None and results[2]['part_of'], 'a half alone is part of its base'


def _halves(user):
    deal = make_deal(user)
    make = services.create_plan
    current = make(user, deal, line='medical', role='current', carrier='Florida Blue', name='HSA 05180')
    first = make(user, deal, line='medical', role='alternate', carrier='Florida Blue', name='HSA 05182')
    second = make(user, deal, line='medical', role='alternate', carrier='Florida Blue', name='HSA 05183')
    return deal, current, first, second


def test_J15_F137_pair_and_split_through_the_door(api, user):
    deal, _current, first, second = _halves(user)
    url = f'/api/deals/{deal.id}/plans/pair/'
    made = api.post(url, {'plan_ids': [first.id, second.id]}, format='json')
    assert made.status_code == 200, made.content
    assert [(p['id'], p['pair_of']) for p in made.json()['plans']] == [(second.id, first.id)]
    assert made.json()['activity_id']
    again = api.post(url, {'plan_ids': [first.id, second.id]}, format='json').json()
    assert again == {'plans': [], 'activity_id': None}, 'a pair made again writes nothing'
    split = api.post(url, {'plan_ids': [first.id], 'split': True}, format='json')
    assert split.status_code == 200 and Plan.objects.get(pk=second.id).pair_of_id is None
    assert both_plans_stay(deal), 'pairing never removes a plan'


def both_plans_stay(deal):
    return Plan.objects.filter(deal=deal).count() == 3


@pytest.mark.parametrize(
    ('which', 'words'),
    [
        ('carrier', 'different carriers'),
        ('kind', 'not the same kind'),
        ('itself', 'cannot be paired with itself'),
        ('taken', 'split it first'),
    ],
)
def test_J15_what_cannot_be_one_plan_is_refused_by_name(api, user, which, words):
    deal, current, first, second = _halves(user)
    other = services.create_plan(user, deal, line='medical', role='alternate', carrier='Aetna', name='Choice POS')
    if which == 'taken':
        services.pair_plans(user, deal, first.id, second.id)
    third = services.create_plan(user, deal, line='medical', role='alternate', carrier='Florida Blue', name='HSA 7')
    ids = {
        'carrier': [first.id, other.id],
        'kind': [first.id, current.id],
        'itself': [first.id, first.id],
        'taken': [third.id, second.id],
    }[which]
    answer = api.post(f'/api/deals/{deal.id}/plans/pair/', {'plan_ids': ids}, format='json')
    assert answer.status_code == 409
    assert words in answer.json()['detail']


def test_J15_bad_ids_answer_400_and_a_plan_in_no_pair_cannot_split(api, user):
    deal, _current, first, second = _halves(user)
    url = f'/api/deals/{deal.id}/plans/pair/'
    assert api.post(url, {'plan_ids': [first.id, 'x']}, format='json').status_code == 400
    assert api.post(url, {'plan_ids': [first.id, second.id, 1]}, format='json').status_code == 400
    assert api.post(url, {'plan_ids': [first.id, 999999]}, format='json').status_code == 400
    lone = api.post(url, {'plan_ids': [first.id], 'split': True}, format='json')
    assert lone.status_code == 409 and 'is not printed as one column' in lone.json()['detail']


def test_J15_on_a_full_line_the_other_half_adds_no_column_and_split_waits_for_room(user):
    deal, _current, first, second = _halves(user)
    quotes = [
        services.create_plan(user, deal, line='medical', role='alternate', carrier='Cigna', name=f'Option {n}')
        for n in range(14)
    ]
    services.pair_plans(user, deal, first.id, second.id)
    services.star(user, deal, [p.id for p in quotes] + [first.id], True)  # 1 current + 15 starred: 16 columns
    changed, _row = services.star(user, deal, [second.id], True)
    assert [plan.id for plan in changed] == [second.id], 'the pair is still 16 columns'
    with pytest.raises(activity.Refused) as refused:
        services.split_pair(user, deal, second.id)
    assert 'holds 16 plans' in refused.value.sentence and 'splitting this pair' in refused.value.sentence
    services.star(user, deal, [quotes[0].id], False)
    changed, _row = services.split_pair(user, deal, second.id)
    assert [plan.id for plan in changed] == [second.id]


def test_J15_GD1_the_pair_counts_once_and_prints_its_package(gd1, golden_keys):
    from quotes import selectors

    deal, refs, _spec = gd1
    state = selectors.line_state(deal, 'medical')
    assert pairs.found(state.data, [p.id for p in presented.presented(state.data)]) == [(refs['FB1'], refs['FB2'])]
    assert presented.room(state.data) == presented.MAX_COLUMNS - len(presented.held(state.data)) + 1
    folded = pk.folded(state.data, state.results, [(refs['FB1'], refs['FB2'])])
    expected = golden_keys['GD1']['pairs']['FB1+FB2']
    got = folded[refs['FB1']]
    assert (got['monthly'], got['annual'], got['change']) == (
        expected['monthly'],
        expected['annual'],
        expected['change'],
    )
    package = pk.package([refs['FB1'], refs['FB2']], state.data, state.results)
    assert (package['monthly'], package['annual']) == (got['monthly'], got['annual'])
