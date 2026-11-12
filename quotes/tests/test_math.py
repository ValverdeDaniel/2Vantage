"""Every worked example of plan.md §5.5 (table-driven), on `quotes/math/` in Decimal (OQ9 b).

The volume_1000, weekly_10 and payroll_100 examples marked PROVISIONAL (OQ103) are ours, worked out by hand from §5.5's
formulas; they change only if the examples Stephanie signs before slice 27 differ.
"""

from decimal import Decimal

import pytest

from quotes import math as m
from quotes import packages as pk
from quotes.shapes import LineData, PlanData


def plan(pid, role='current', counts=None, rates=None, quoted=None, **kw):
    values = {}
    for tier, rate in (rates or {}).items():
        values[m.TIER_RATE[tier]] = str(rate)
    if quoted is not None:
        values['group_premium_monthly'] = str(quoted)
    for key in ('unit_rate', 'sl_spec_rate', 'sl_agg_rate', 'sl_other_load'):
        if key in kw:
            values[key] = str(kw.pop(key))
    enrollment = counts or {}
    return PlanData(id=pid, role=role, values=values, enrollment=enrollment, **kw)


def price(p, basis='composite', others=()):
    line = LineData(basis, [p, *others])
    enrollment, how = m.enrollment_for(p, line)
    if enrollment is None:
        return None, how
    monthly, reason, _ = m.monthly_premium(p, line, enrollment)
    return monthly, reason


TIER_COUNTS = {'EE': 10, 'ES': 3, 'EC': 2, 'FAM': 5}


@pytest.mark.parametrize(
    'case, p, basis, expected',
    [
        (
            'composite: 5,000 + 3,001.50 + 1,800.50 + 7,503.75 = 17,305.75',
            plan(1, counts=TIER_COUNTS, rates={'EE': 500.00, 'ES': 1000.50, 'EC': 900.25, 'FAM': 1500.75}),
            'composite',
            (17306, None),
        ),
        (
            'missing enrolled rate, quoted premium 15,000',
            plan(1, counts={'EE': 10, 'ES': 2}, rates={'EE': 500}, quoted=15000),
            'composite',
            (15000, None),
        ),
        (
            'missing enrolled rate, no quoted premium',
            plan(1, counts={'EE': 10, 'ES': 2}, rates={'EE': 500}),
            'composite',
            (None, 'missing_rate'),
        ),
        (
            'no enrollment, quoted premium 9,000',
            plan(1, counts={'EE': 0}, quoted=9000),
            'composite',
            (None, 'no_enrollment'),
        ),
        ('volume per $1,000', plan(1, counts={'volume': 1_250_000}, unit_rate=0.12), 'volume_1000', (150, None)),
        (
            'unit rate with three decimals (rounded to 0.19 it would be 380)',
            plan(1, counts={'volume': 2_000_000}, unit_rate=0.185),
            'volume_1000',
            (370, None),
        ),
        ('no volume, quoted premium 400', plan(1, unit_rate=0.12, quoted=400), 'volume_1000', (None, 'no_enrollment')),
        (
            'payroll per $100: 3,000,000 ÷ 12 ÷ 100 × 0.45',
            plan(1, counts={'volume': 3_000_000}, unit_rate=0.45),
            'payroll_100',
            (1125, None),
        ),
        ('PEPM', plan(1, counts={'lives': 42}, unit_rate=3.50), 'pepm', (147, None)),
        (
            'stop-loss: (85.20 + 12.10) × 40',
            plan(1, counts={'lives': 40}, sl_spec_rate=85.20, sl_agg_rate=12.10),
            'stop_loss',
            (3892, None),
        ),
    ],
)
def test_5_5_monthly_premium_worked_examples(case, p, basis, expected):
    assert price(p, basis) == expected, case


@pytest.mark.parametrize(
    'case, p, basis, expected',
    [
        # volume_1000: 1,830,000 of benefit volume at 0.233 a $1,000 = 426.39 → 426.
        ('PROVISIONAL volume_1000', plan(1, counts={'volume': 1_830_000}, unit_rate=0.233), 'volume_1000', 426),
        # volume_1000, half up: 1,250,000 at 0.0996 (a rate4 unit rate) = 124.50 → 125 (Python's round gives 124).
        (
            'PROVISIONAL volume_1000, half up',
            plan(1, counts={'volume': 1_250_000}, unit_rate=0.0996),
            'volume_1000',
            125,
        ),
        # weekly_10: 18,450 of weekly benefit at 0.42 a $10 = 774.90 → 775.
        ('PROVISIONAL weekly_10', plan(1, counts={'volume': 18_450}, unit_rate=0.42), 'weekly_10', 775),
        # weekly_10, half up: 12,900 at 0.25 a $10 = 322.50 → 323 (Python's round gives 322).
        ('PROVISIONAL weekly_10, half up', plan(1, counts={'volume': 12_900}, unit_rate=0.25), 'weekly_10', 323),
        # payroll_100: 2,412,600 of annual payroll ÷ 12 ÷ 100 × 0.62 = 1,246.51 → 1,247.
        ('PROVISIONAL payroll_100', plan(1, counts={'volume': 2_412_600}, unit_rate=0.62), 'payroll_100', 1247),
        # payroll_100, half up: 1,110,000 ÷ 12 ÷ 100 × 0.50 = 462.50 → 463 (Python's round gives 462).
        ('PROVISIONAL payroll_100, half up', plan(1, counts={'volume': 1_110_000}, unit_rate=0.50), 'payroll_100', 463),
    ],
)
def test_OQ103_rate_bases_without_a_golden_deal_equal_their_provisional_worked_examples(case, p, basis, expected):
    assert price(p, basis) == (expected, None), case


def test_5_5_half_up_like_excel():
    assert m.round_decimal(2642.5) == 2643  # Python's round gives 2642
    assert m.round_decimal(2.675, 2) == Decimal('2.68')  # the float 2.675 is 2.67499…; read at 15 digits it is 2.675
    assert m.round_decimal(-2.5) == -3  # half away from zero
    assert m.round_money(2642.5) == 2643 and m.round_money(2.675, 2) == 2.68


def test_5_5_money_is_worked_in_decimal():
    p = plan(1, counts={'volume': 1_250_000}, unit_rate=0.0996)
    monthly, _, _ = m.monthly_premium(p, LineData('volume_1000', [p]), {'volume': Decimal(1_250_000)})
    assert isinstance(monthly, Decimal) and monthly == 125  # in floats the product is 124.49999999999999


def test_5_5_change():
    assert m.change(120_000, 100_000) == {'delta': 20_000, 'pct': 20.0}
    assert m.change(120_000, 0) == {'delta': 120_000, 'pct': None}


def test_5_5_two_current_plans_without_typed_counts_need_per_plan_enrollment():
    a, b = plan(1), plan(2)
    assert price(a, others=[b]) == (None, 'per_plan_counts_needed')


def test_5_5_unlinked_alternate_on_a_one_plan_line_uses_the_current_plans_counts():
    d = plan(1, counts=TIER_COUNTS)
    e = plan(2, role='alternate')
    line = LineData('composite', [d, e])
    figures, source = m.enrollment_for(e, line)
    assert (m.plain(figures['EE']), m.plain(figures['FAM']), source) == (10, 5, 'from replaced plan')
    assert line.base_ids(e) == [1]


def test_5_5_employee_cost_and_tier_rate_change():
    current = plan(1, rates={'EE': 500})
    renewal = plan(2, 'renewal', rates={'EE': 540.5}, renews=1)
    renewal.values['contrib_ee'] = '600'
    assert m.employee_cost(renewal)['EE'] == 0.0  # never below zero
    assert m.tier_rate_change(renewal, current)['EE'] == {'delta': 40.5, 'pct': 8.1}


# Package examples: A $10,000 and B $8,000 a month; renewals A2, B2; Cigna C1, C2 replace A, C3 replaces B.
def package_line(extra=()):
    plans = [
        plan(1, counts={'EE': 10}, rates={'EE': 1000}, carrier='Aetna', name='HDHP 3300'),
        plan(2, counts={'EE': 8}, rates={'EE': 1000}, carrier='Aetna', name='PPO 1500', sort_order=1),
        plan(3, 'renewal', rates={'EE': 1080}, renews=1, carrier='Aetna'),
        plan(4, 'renewal', rates={'EE': 1080}, renews=2, carrier='Aetna'),
        plan(5, 'alternate', rates={'EE': 950}, replaces=(1,), carrier='Cigna', name='C1'),
        plan(6, 'alternate', rates={'EE': 920}, replaces=(1,), carrier='Cigna', name='C2'),
        plan(7, 'alternate', rates={'EE': 987.50}, replaces=(2,), carrier='Cigna', name='C3'),
        *extra,
    ]
    line = LineData('composite', plans)
    return line, pk.evaluate(line)


def test_5_5_current_and_complete_renewal():
    line, results = package_line()
    shown = {p['key']: p for p in pk.line_packages(line, results)}
    assert shown['current']['annual'] == 216_000
    assert shown['renewal']['annual'] == 233_280
    assert shown['renewal']['change'] == {'delta': 17_280, 'pct': 8.0}


def test_5_5_partial_renewal_has_no_total():
    plans = [p for p in package_line()[0].plans if p.id != 4]
    line = LineData('composite', plans)
    renewal = next(p for p in pk.line_packages(line, pk.evaluate(line)) if p['key'] == 'renewal')
    assert renewal['annual'] is None and renewal['change'] is None
    assert renewal['reason'] == 'No renewal entered for PPO 1500'


def test_5_5_a_carriers_two_options_for_one_plan_offer_no_carrier_package():
    line, results = package_line()
    assert not [p for p in pk.line_packages(line, results) if p['key'] == 'carrier:Cigna']
    summed = pk.package([5, 6, 7], line, results)
    assert summed['same_people'] is False and 'are two options counted together?' in summed['reason']
    assert summed['reason'].startswith('Enrollment differs from today (EE 28 vs 18)')


def test_5_5_a_member_built_package():
    line, results = package_line()
    built = pk.package([5, 7], line, results, 'package:1', 'Cigna')
    assert built['annual'] == 208_800 and built['change'] == {'delta': -7_200, 'pct': -3.3}


def test_5_5_recommendation_with_options_and_coverage():
    line, results = package_line()
    for p in line.plans:
        p.recommended = p.id in (5, 6, 7)
    rec = pk.recommendation(line, results)
    assert rec['covered'] is True
    assert results[5]['change'] == {'delta': -6_000, 'pct': -5.0}
    assert results[6]['change'] == {'delta': -9_600, 'pct': -8.0}
    for p in line.plans:
        p.recommended = p.id == 5
    assert pk.recommendation(line, results)['missing'] == ['PPO 1500']


def test_5_5_consolidation_three_plans_to_two():
    u1 = plan(8, 'alternate', rates={'EE': 944.44}, replaces=(1, 2), carrier='UHC', name='U1')
    line, results = package_line([u1])
    assert results[8]['enrollment_used'] == {'EE': 18, 'ES': 0, 'EC': 0, 'FAM': 0}
    assert results[8]['annual'] == 204_000 and results[8]['change'] == {'delta': -12_000, 'pct': -5.6}
    assert pk.package([8], line, results)['change'] == {'delta': -12_000, 'pct': -5.6}


def test_5_5_plans_bought_together():
    h1 = plan(9, 'alternate', counts={'EE': 6}, rates={'EE': 800}, replaces=(1,), name='H1')
    p1 = plan(10, 'alternate', counts={'EE': 4}, rates={'EE': 1400}, replaces=(1,), name='P1')
    line, results = package_line([h1, p1])
    built = pk.package([9, 10, 4], line, results)
    assert built['annual'] == 228_480 and built['change'] == {'delta': 12_480, 'pct': 5.8}
    assert results[9]['change'] is None and results[9]['part_of'] == 'HDHP 3300'


def test_5_5_bought_together_without_splitting_enrollment_shows_no_change():
    h1 = plan(9, 'alternate', rates={'EE': 800}, replaces=(1,), name='H1')
    p1 = plan(10, 'alternate', rates={'EE': 1400}, replaces=(1,), name='P1')
    line, results = package_line([h1, p1])
    built = pk.package([9, 10, 4], line, results)
    assert built['priced'] and built['change'] is None
    assert built['reason'].startswith('Enrollment differs from today')


def test_5_5_one_plan_line_unlinked_alternate_carrier_package():
    d = plan(1, counts={'EE': 10}, rates={'EE': 500}, carrier='Aetna', name='D')
    e = plan(2, 'alternate', rates={'EE': 475}, carrier='Aetna', name='E')
    line = LineData('composite', [d, e])
    results = pk.evaluate(line)
    carrier = next(p for p in pk.line_packages(line, results) if p['key'] == 'carrier:Aetna')
    assert carrier['annual'] == 57_000 and carrier['change'] == {'delta': -3_000, 'pct': -5.0}


def test_5_5_new_line_has_no_current_and_no_carrier_package():
    a = plan(1, 'alternate', counts={'EE': 5}, rates={'EE': 40}, carrier='Cigna')
    b = plan(2, 'alternate', counts={'EE': 5}, rates={'EE': 45}, carrier='Cigna')
    line = LineData('composite', [a, b])
    results = pk.evaluate(line)
    assert pk.line_packages(line, results) == []
    built = pk.package([1, 2], line, results)
    assert built['annual'] == (5 * 40 + 5 * 45) * 12 and built['change'] is None
