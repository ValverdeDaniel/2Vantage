"""Stop-loss arithmetic (plan.md §5.5, §9.13; F98–F107; Q.9 row 36: "stop-loss math"), pinned by worked examples
worked out by hand (48 enrolled employees × 12 months = 576 employee-months), never from the app's own output."""

from decimal import Decimal

import pytest

from quotes.math import stop_loss as sl

D = Decimal
CONTRACT = {
    'sl_spec_deductible': '50000',
    'sl_spec_rate': '85.20',
    'sl_agg_rate': '12.10',
    'sl_agg_factor': '850.00',
    'sl_agg_corridor': '1.25',
    'sl_lasers': 'J.D. 125000, R.K. 90000',
    'tpa_admin_fee': '38.00',
}


def test_F99_a_contract_worked_by_hand():
    found = sl.summary(CONTRACT, 48)
    assert found['premium_pepm'] == D('97.30')
    assert found['annual_premium'] == D('56044.80')  # 97.30 × 48 × 12
    assert found['annual_admin'] == D('21888.00')  # 38 × 576
    assert found['attachment_pepm'] == D('1062.5000')  # 850 × 1.25
    assert found['annual_attachment'] == D('612000')  # 1,062.50 × 576
    assert found['annual_expected_claims'] == D('489600')  # 850 × 576, before the corridor
    assert found['laser_liability'] == D('115000')  # 75,000 + 40,000
    assert found['laser_count'] == 2
    assert found['max_annual_liability'] == D('804932.80')
    assert found['projected_cost'] == D('567532.80')
    assert found['fixed_cost'] == D('77932.80')
    assert [laser['n'] for laser in found['lasers']] == [1, 2]


def test_F99_a_quoted_floor_binds_only_above_the_computed_attachment():
    floored = sl.summary({**CONTRACT, 'sl_agg_factor': '860', 'sl_agg_corridor': '1.20', 'sl_agg_floor': '650000'}, 48)
    assert floored['annual_attachment'] == D('650000')  # 860 × 1.20 × 576 = 594,432 < 650,000
    above = sl.summary({**CONTRACT, 'sl_agg_factor': '880', 'sl_agg_floor': '600000'}, 48)
    assert above['annual_attachment'] == D('633600')  # 880 × 1.25 × 576


@pytest.mark.parametrize(
    ('change', 'none'),
    [
        ({'sl_spec_rate': ''}, ('annual_premium', 'max_annual_liability', 'projected_cost', 'fixed_cost')),
        ({'sl_agg_factor': ''}, ('annual_attachment', 'annual_expected_claims', 'max_annual_liability')),
        ({'sl_agg_corridor': ''}, ('annual_attachment', 'max_annual_liability')),
        ({'sl_spec_deductible': ''}, ('laser_liability', 'laser_count', 'max_annual_liability')),
    ],
)
def test_F99_a_missing_load_bearing_input_states_nothing_it_carries(change, none):
    found = sl.summary({**CONTRACT, **change}, 48)
    for key in none:
        assert found[key] is None, key


def test_F99_optional_parts_count_as_zero_and_agg_alone_mints_no_premium():
    bare = sl.summary({'sl_spec_rate': '80', 'sl_agg_factor': '800', 'sl_agg_corridor': '1.25'}, 10)
    assert bare['premium_pepm'] == D('80')
    assert bare['annual_admin'] == 0 and bare['laser_liability'] == 0
    assert bare['max_annual_liability'] == D('9600') + D('120000')
    assert sl.summary({'sl_agg_rate': '12.10', 'sl_other_load': '2'}, 10)['premium_pepm'] is None


def test_F98_no_enrolled_employees_leaves_every_annual_figure_blank():
    for headcount in (None, 0):
        found = sl.summary(CONTRACT, headcount)
        assert found['annual_premium'] is None and found['annual_attachment'] is None
        assert found['max_annual_liability'] is None
        assert found['premium_pepm'] == D('97.30')  # the PEPM still reads


def test_F104_the_what_if_leaves_lasers_out_by_position():
    found = sl.summary(CONTRACT, 48, without={1})
    assert found['laser_liability'] == D('40000')
    assert found['laser_count'] == 1
    assert found['max_annual_liability'] == D('804932.80') - D('75000')
    assert found['what_if'] is True
    assert [laser['included'] for laser in found['lasers']] == [False, True]
    assert sl.summary(CONTRACT, 48, without={9})['what_if'] is False  # a position the plan does not have


def test_F104_the_what_if_waits_for_a_specific_deductible():
    found = sl.summary({**CONTRACT, 'sl_spec_deductible': ''}, 48, without={1})
    assert found['what_if'] is False and found['laser_liability'] is None


@pytest.mark.parametrize(
    ('text', 'amounts'),
    [
        ('B.S. 200000, M.W. 90000', [200000, 90000]),
        ('M.W. 90,000; K.L. 75000', [90000, 75000]),  # thousands separators never split an entry
        ('B.S. 200000 (renal)', [200000]),
        ('X 90k', [90000]),
        ('aged 45 laser 165000 est', [165000]),  # the largest standalone number; small numbers are notes
        ('pending\nC.D. 120000', [120000]),
        ('', []),
    ],
)
def test_F104_lasers_are_read_from_the_mini_format(text, amounts):
    assert [laser.amount for laser in sl.parse_lasers(text)] == [D(a) for a in amounts]


def test_OQ104_the_shared_rows_line_one_claimant_up_and_print_no_claimant():
    plans = [sl.parse_lasers('J.D. 125000, R.K. 90000'), sl.parse_lasers('j.d. 175000, M.P. 75000'), []]
    count, rows = sl.shared_rows(plans)
    assert count == 3
    assert rows == [{1: D(125000), 2: D(90000)}, {1: D(175000), 3: D(75000)}, {}]
    assert all(isinstance(row, int) for mine in rows for row in mine)


def test_OQ104_lasers_with_no_claimant_never_share_a_row():
    count, rows = sl.shared_rows([sl.parse_lasers('125000'), sl.parse_lasers('90000')])
    assert count == 2 and rows == [{1: D(125000)}, {2: D(90000)}]


def test_F103_deltas_against_the_current_contract_refuse_a_hole():
    current = sl.summary(CONTRACT, 48)
    option = sl.summary({'sl_spec_rate': '', 'sl_agg_factor': '850', 'sl_agg_corridor': '1.25'}, 48)
    vs = sl.against_current(option, current)
    assert vs == {'max_annual_liability': None, 'annual_premium': None, 'laser_liability': None}


def test_F100_the_board_rounds_once_half_up():
    shown = sl.shown(sl.summary(CONTRACT, 48))
    assert shown['annual_premium'] == 56045 and shown['max_annual_liability'] == 804933
    assert shown['premium_pepm'] == 97.3 and shown['corridor'] == 1.25
    assert sl.money(D('-67956.80')) == -67957  # half away from zero, as Excel's ROUND


def test_F107_the_level_funded_split():
    split = sl.lf_split({'lf_claim_funding': '30702.00', 'lf_stop_loss_premium': '8772.00', 'lf_admin_fee': '4386'})
    assert split == {'claim_funding': 30702, 'fixed_costs': 13158, 'monthly_total': 43860, 'pct_to_claims': 70.0}
    assert sl.lf_split({'lf_claim_funding': '30000'}) is None  # claims alone would score itself 100%
    assert sl.lf_split({'lf_stop_loss_premium': '100'}) is None


def test_F99_the_workbook_mirrors_derive_back_from_the_annual():
    assert sl.per_month(D('56044.80')) == D('4670.40')
    assert sl.per_employee(D('612000'), 48) == D('1062.5')
    assert sl.times(D('97.30'), 48) == D('4670.40') and sl.times(None, 48) is None
