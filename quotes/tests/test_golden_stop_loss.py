"""GD5, the stop-loss golden deal, against its hand-worked answer key (plan.md §12.6, §13.4; Q.4, Q.9 row 36): the
premiums the board prices, the level-funded split, and the stop-loss analysis — the basis and its source, every figure,
the verdict ranked lowest first, the punchline and the laser what-if (F98–F107). Read-only: GD5 as seeded."""

from decimal import Decimal

import pytest

from quotes import selectors
from quotes.math import stop_loss as sl
from quotes.selectors import stop_loss

pytestmark = pytest.mark.django_db

FIGURES = (
    'annual_premium',
    'annual_admin',
    'annual_attachment',
    'annual_expected_claims',
    'laser_liability',
    'projected_cost',
    'max_annual_liability',
)


def _exact(text):
    return None if text is None else Decimal(text)


@pytest.fixture(scope='module')
def key(golden_keys):
    return golden_keys['GD5']


def test_PAR1_GD5_every_plan_prices_as_its_key(gd5, key):
    deal, refs, spec = gd5
    for line in spec['lines']:
        results = selectors.line_state(deal, line).results
        for plan in (p for p in spec['plans'] if p['line'] == line):
            got = results[refs[plan['ref']]]
            want = key['plans'][plan['ref']]
            assert (got['monthly'], got['annual'], got['change']) == (want['monthly'], want['annual'], want['change'])


def test_F107_GD5_the_level_funded_split_matches_the_key(gd5, key):
    deal, refs, _ = gd5
    plans = {plan.id: plan for plan in selectors.line_state(deal, 'medical').plans}
    for ref, want in key['lf_split'].items():
        assert sl.lf_split(plans[refs[ref]].values) == want, ref


def test_F98_GD5_the_basis_is_the_medical_enrolled_employees_and_names_its_source(gd5, key):
    found = stop_loss.read(gd5.deal)
    basis = key['stop_loss']['basis']
    assert (found.lives, found.months, found.source) == (basis['lives'], basis['months'], basis['source'])
    assert stop_loss.payload(found)['basis'] == basis


def test_F99_GD5_every_figure_matches_the_key_exactly(gd5, key):
    deal, refs, _ = gd5
    found = stop_loss.read(deal)
    by_ref = {refs_id: ref for ref, refs_id in refs.items()}
    for column in found.columns:
        ref = by_ref[column.plan.id]
        want = key['stop_loss']['plans'][ref]
        for name in FIGURES:
            assert column.figures[name] == _exact(want[name]), (ref, name)
        assert column.figures['premium_pepm'] == _exact(want['premium_pepm'])
        assert column.figures['laser_count'] == want['laser_count']
        vs = None if column.vs is None else {name: column.vs[name] for name in want['vs'] or {}}
        assert vs == (None if want['vs'] is None else {k: _exact(v) for k, v in want['vs'].items()}), ref


def test_F100_GD5_the_verdict_ranks_lowest_first_on_every_key(gd5, key):
    deal, refs, _ = gd5
    body = stop_loss.analysis(deal)
    names = {plan_id: ref for ref, plan_id in refs.items()}
    for rank_key, order in key['stop_loss']['ranks'].items():
        assert [names[plan_id] for plan_id in body['ranks'][rank_key]] == order, rank_key


def test_F101_GD5_the_punchline_names_the_cheapest_premium_whatever_the_rank_key(gd5, key):
    deal, refs, _ = gd5
    punchline = stop_loss.analysis(deal)['punchline']
    assert punchline['plan_id'] == refs[key['stop_loss']['punchline']]
    assert punchline['carrier'] == 'Sun Life'


def test_F104_GD5_the_laser_what_if_moves_the_verdict_and_names_lasers_by_position(gd5, key):
    deal, refs, _ = gd5
    case = key['stop_loss']['what_if']
    without = {refs[ref]: set(positions) for ref, positions in case['without'].items()}
    body = stop_loss.analysis(deal, without)
    names = {plan_id: ref for ref, plan_id in refs.items()}
    assert [names[i] for i in body['ranks']['max_annual_liability']] == case['max_annual_liability']
    column = next(c for c in body['columns'] if c['id'] == refs['SL-A'])
    want = case['SL-A']
    assert column['what_if'] is True and body['what_if'] is True
    assert column['figures']['laser_liability'] == int(want['laser_liability'])
    assert column['figures']['laser_count'] == want['laser_count']
    assert column['figures']['max_annual_liability'] == sl.money(Decimal(want['max_annual_liability']))
    assert column['vs']['max_annual_liability'] == int(want['vs_max_annual_liability'])
    assert [laser['included'] for laser in column['figures']['lasers']] == [False, True]
    assert set(column['figures']['lasers'][0]) == {'n', 'amount', 'extra', 'included'}  # no claimant


def test_F104_rule10_GD5_no_claimant_reaches_the_payload(gd5, api):
    deal = gd5.deal
    text = api.get(f'/api/deals/{deal.id}/plans/stop-loss/').content.decode()
    for claimant in ('J.D.', 'R.K.', 'M.P.', 'sl_lasers'):
        assert claimant not in text
