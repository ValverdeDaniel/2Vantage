"""Every worked example of plan.md §5.5 (table-driven)."""

import pytest

from quotes import math as m
from quotes import packages as pk


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
    return m.PlanData(id=pid, role=role, values=values, enrollment=enrollment, enrollment_on=bool(enrollment), **kw)


def price(p, basis='composite', others=()):
    line = m.LineData(basis, [p, *others])
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
            'composite',
            plan(1, counts=TIER_COUNTS, rates={'EE': 500.00, 'ES': 1000.50, 'EC': 900.25, 'FAM': 1500.75}),
            'composite',
            (17306, None),
        ),
        (
            'quoted premium for an enrolled tier without a rate',
            plan(1, counts={'EE': 10, 'ES': 2}, rates={'EE': 500}, quoted=15000),
            'composite',
            (15000, None),
        ),
        (
            'missing rate, no quoted premium',
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
            'unit rate with three decimals',
            plan(1, counts={'volume': 2_000_000}, unit_rate=0.185),
            'volume_1000',
            (370, None),
        ),
        ('no volume, quoted premium 400', plan(1, unit_rate=0.12, quoted=400), 'volume_1000', (None, 'no_enrollment')),
        ('payroll per $100', plan(1, counts={'volume': 3_000_000}, unit_rate=0.45), 'payroll_100', (1125, None)),
        ('PEPM', plan(1, counts={'lives': 42}, unit_rate=3.50), 'pepm', (147, None)),
        ('stop-loss', plan(1, counts={'lives': 40}, sl_spec_rate=85.20, sl_agg_rate=12.10), 'stop_loss', (3892, None)),
    ],
)
def test_monthly_premium_examples(case, p, basis, expected):
    assert price(p, basis) == expected, case


def test_half_up_like_excel():
    assert m.round_money(2642.5) == 2643
    assert m.round_money(2.675, 2) == 2.68


def test_change():
    assert m.change(120_000, 100_000) == {'delta': 20_000, 'pct': 20.0}


def test_two_current_plans_without_typed_counts_need_per_plan_enrollment():
    a, b = plan(1), plan(2)
    assert price(a, others=[b]) == (None, 'per_plan_counts_needed')


def test_unlinked_alternate_on_a_one_plan_line_uses_the_current_plans_counts():
    d = plan(1, counts=TIER_COUNTS)
    e = plan(2, role='alternate')
    line = m.LineData('composite', [d, e])
    assert m.enrollment_for(e, line) == ({'EE': 10, 'ES': 3, 'EC': 2, 'FAM': 5}, 'from replaced plan')
    assert m.base_ids(e, line) == [1]


# Package examples: A $10,000 and B $8,000 a month; renewals A2, B2; Cigna C1, C2 replace A, C3 replaces B.
def package_line(extra=()):
    plans = [
        plan(1, counts={'EE': 10}, rates={'EE': 1000}, carrier='Aetna', name='HDHP 3300'),
        plan(2, counts={'EE': 8}, rates={'EE': 1000}, carrier='Aetna', name='PPO 1500'),
        plan(3, 'renewal', rates={'EE': 1080}, renews=1, carrier='Aetna'),
        plan(4, 'renewal', rates={'EE': 1080}, renews=2, carrier='Aetna'),
        plan(5, 'alternate', rates={'EE': 950}, replaces=(1,), carrier='Cigna', name='C1'),
        plan(6, 'alternate', rates={'EE': 920}, replaces=(1,), carrier='Cigna', name='C2'),
        plan(7, 'alternate', rates={'EE': 987.50}, replaces=(2,), carrier='Cigna', name='C3'),
        *extra,
    ]
    line = m.LineData('composite', plans)
    return line, pk.evaluate(line)


def test_current_and_complete_renewal():
    line, results = package_line()
    shown = {p['key']: p for p in pk.line_packages(line, results)}
    assert shown['current']['annual'] == 216_000
    assert shown['renewal']['annual'] == 233_280
    assert shown['renewal']['change'] == {'delta': 17_280, 'pct': 8.0}


def test_partial_renewal_has_no_total():
    plans = [p for p in package_line()[0].plans if p.id != 4]
    line = m.LineData('composite', plans)
    renewal = next(p for p in pk.line_packages(line, pk.evaluate(line)) if p['key'] == 'renewal')
    assert renewal['annual'] is None and renewal['change'] is None
    assert renewal['reason'] == 'No renewal entered for PPO 1500'


def test_a_carriers_two_options_for_one_plan_offer_no_carrier_package():
    line, results = package_line()
    assert not [p for p in pk.line_packages(line, results) if p['key'] == 'carrier:Cigna']
    summed = pk.package([5, 6, 7], line, results)
    assert summed['same_people'] is False and 'are two options counted together?' in summed['reason']


def test_a_member_built_package():
    line, results = package_line()
    built = pk.package([5, 7], line, results, 'package:1', 'Cigna')
    assert built['annual'] == 208_800 and built['change'] == {'delta': -7_200, 'pct': -3.3}


def test_recommendation_with_options_and_coverage():
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


def test_consolidation_three_plans_to_two():
    u1 = plan(8, 'alternate', rates={'EE': 944.44}, replaces=(1, 2), carrier='UHC', name='U1')
    line, results = package_line([u1])
    assert results[8]['enrollment_used'] == {'EE': 18, 'ES': 0, 'EC': 0, 'FAM': 0}
    assert results[8]['annual'] == 204_000 and results[8]['change'] == {'delta': -12_000, 'pct': -5.6}
    assert pk.package([8], line, results)['change'] == {'delta': -12_000, 'pct': -5.6}


def test_plans_bought_together():
    h1 = plan(9, 'alternate', counts={'EE': 6}, rates={'EE': 800}, replaces=(1,), name='H1')
    p1 = plan(10, 'alternate', counts={'EE': 4}, rates={'EE': 1400}, replaces=(1,), name='P1')
    line, results = package_line([h1, p1])
    built = pk.package([9, 10, 4], line, results)
    assert built['annual'] == 228_480 and built['change'] == {'delta': 12_480, 'pct': 5.8}
    assert results[9]['change'] is None and results[9]['part_of'] == 'HDHP 3300'


def test_bought_together_without_splitting_enrollment_shows_no_change():
    h1 = plan(9, 'alternate', rates={'EE': 800}, replaces=(1,), name='H1')
    p1 = plan(10, 'alternate', rates={'EE': 1400}, replaces=(1,), name='P1')
    line, results = package_line([h1, p1])
    built = pk.package([9, 10, 4], line, results)
    assert built['priced'] and built['change'] is None
    assert built['reason'].startswith('Enrollment differs from today')


def test_one_plan_line_unlinked_alternate_carrier_package():
    d = plan(1, counts={'EE': 10}, rates={'EE': 500}, carrier='Aetna', name='D')
    e = plan(2, 'alternate', rates={'EE': 475}, carrier='Aetna', name='E')
    line = m.LineData('composite', [d, e])
    results = pk.evaluate(line)
    carrier = next(p for p in pk.line_packages(line, results) if p['key'] == 'carrier:Aetna')
    assert carrier['annual'] == 57_000 and carrier['change'] == {'delta': -3_000, 'pct': -5.0}


def test_new_line_has_no_current_and_no_carrier_package():
    a = plan(1, 'alternate', counts={'EE': 5}, rates={'EE': 40}, carrier='Cigna')
    b = plan(2, 'alternate', counts={'EE': 5}, rates={'EE': 45}, carrier='Cigna')
    line = m.LineData('composite', [a, b])
    results = pk.evaluate(line)
    assert pk.line_packages(line, results) == []
    built = pk.package([1, 2], line, results)
    assert built['annual'] == (5 * 40 + 5 * 45) * 12 and built['change'] is None
