"""Share math, pure (plan.md §5.6; H.6 "Tests": Comp amounts, the old share examples, gross and expiry; Q.9 row 48:
shares in millionths)."""

from decimal import Decimal

from commission import math

PCT = lambda value: {'type': 'pct', 'value': str(value)}  # noqa: E731
FLAT = lambda value: {'type': 'flat', 'value': str(value)}  # noqa: E731
PEPM = lambda value: {'type': 'pepm', 'value': str(value)}  # noqa: E731


def primary(party='p1'):
    return {'party': party, 'role': 'primary', 'amount': None, 'basis': 'pool'}


def row(party, amount, role='split', basis='pool', **terms):
    return {'party': party, 'role': role, 'amount': amount, 'basis': basis, **terms}


def by_role(shares):
    return {(share['role'], share['party']): share['share'] for share in shares}


def test_H6_comp_amount_per_type_rounds_half_up():
    assert math.comp_amount(PCT(5), premium=76092) == Decimal('3805')  # 3,804.6 → 3,805 (§5.6's worked example)
    assert math.comp_amount(PCT('2.5'), premium=1) == Decimal('0')  # 0.025 → 0
    assert math.comp_amount(PCT(5), premium=10) == Decimal('1')  # 0.5 → 1, half up, never banker's
    assert math.comp_amount(FLAT('12345.67')) == Decimal('12346')
    assert math.comp_amount(FLAT('12345.67'), places=2) == Decimal('12345.67')
    assert math.comp_amount(PEPM(32), employees=46) == Decimal('17664')  # 32 × 46 × 12


def test_H6_a_missing_figure_gives_no_amount():
    assert math.comp_amount(PCT(5)) is None
    assert math.comp_amount(PEPM(32)) is None
    assert math.comp_amount(None, premium=1000) is None


def test_H17_the_old_example_house_then_flat_then_pct_then_the_primary():
    # $10,000 of revenue, the house at 60 %: a $1,000 flat row is 10 %, a 50 % split of what is left is 15 %, and the
    # primary keeps 15 % (891f1b3 commissions/tests.py's share example).
    shares = math.compute_shares(10000, [primary(), row('p2', FLAT(1000)), row('p3', PCT(50))], Decimal(60))
    assert by_role(shares) == {
        ('house', None): 600_000,
        ('primary', 'p1'): 150_000,
        ('split', 'p2'): 100_000,
        ('split', 'p3'): 150_000,
    }
    assert sum(share['share'] for share in shares) == math.MILLION
    assert [share['role'] for share in shares][:2] == ['house', 'primary']


def test_H17_a_flat_amount_is_capped_at_the_pool():
    shares = by_role(math.compute_shares(10000, [primary(), row('p2', FLAT(5000))], Decimal(60)))
    assert shares[('split', 'p2')] == 400_000  # $5,000 asked, but the pool is $4,000
    assert shares[('primary', 'p1')] == 0


def test_H10_no_primary_the_house_keeps_the_rest():
    shares = by_role(math.compute_shares(10000, [row('p2', PCT(25))], Decimal(60)))
    assert shares == {('house', None): 900_000, ('split', 'p2'): 100_000}


def test_H17_a_gross_row_comes_off_the_top_before_the_house():
    shares = by_role(math.compute_shares(10000, [primary(), row('p2', PCT(10), basis='gross')], Decimal(60)))
    assert shares[('split', 'p2')] == 100_000  # 10 % of all revenue
    assert shares[('house', None)] == 540_000  # 60 % of the 90 % left
    assert shares[('primary', 'p1')] == 360_000


def test_OQ71_a_60_40_split_of_the_pool():
    shares = by_role(math.compute_shares(10000, [primary(), row('p2', PCT(40), role='secondary')], Decimal(60)))
    assert shares == {('house', None): 600_000, ('primary', 'p1'): 240_000, ('secondary', 'p2'): 160_000}


def test_H18_flat_shares_wait_for_the_revenue_and_settle_when_it_arrives():
    rows = [primary(), row('p2', FLAT(1000))]
    assert by_role(math.compute_shares(None, rows, Decimal(60)))[('split', 'p2')] == 0
    assert by_role(math.compute_shares(20000, rows, Decimal(60)))[('split', 'p2')] == 50_000


def test_OQ71_a_pepm_split_pays_on_the_headcount_it_is_given():
    rows = [primary(), row('p2', PEPM(2))]
    shares = by_role(math.compute_shares(12000, rows, Decimal(60), employees=50))
    assert shares[('split', 'p2')] == 100_000  # $2 × 50 × 12 = $1,200 of $12,000


def test_H15_H121_renewal_amount_and_expiry():
    rows = [
        primary(),
        row('p2', PCT(20), renewal_amount=PCT(0)),
        row('p3', PCT(10), expires_after_years=1),
        row('p4', PCT(5)),
    ]
    first = math.year_terms(rows, 1)
    assert [r['party'] for r in first] == ['p1', 'p2', 'p3', 'p4']
    second = math.year_terms(rows, 2)
    assert [r['party'] for r in second] == ['p1', 'p2', 'p4']  # p3 expired after year one
    assert second[1]['amount'] == PCT(0)  # "first year only" pays nothing from year two
    shares = by_role(math.compute_shares(10000, second, Decimal(70)))
    assert shares[('split', 'p2')] == 0
    assert math.year_terms(rows, None) == second  # a year not known pays the renewal terms


def test_H18_dollars_sum_to_the_revenue_exactly():
    shares = math.compute_shares(1000, [primary(), row('p2', PCT('33.3333')), row('p3', PCT('33.3333'))], Decimal(0))
    amounts = math.dollars(Decimal('1000.01'), shares)
    assert sum(amounts) == Decimal('1000.01')
    assert math.dollars(None, shares) == [None, None, None, None]


def test_H18_shares_as_text():
    assert math.pct_text(150_000) == '15'
    assert math.pct_text(333_333) == '33.3333'
    assert math.millionths('12.5') == 125_000
    assert (math.pct_label(333_333), math.pct_label(600_000), math.pct_label(150_500)) == ('33.3%', '60.0%', '15.1%')
