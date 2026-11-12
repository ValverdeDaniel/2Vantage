"""Priced versions' money and words, pure (plan.md §5.4, §5.5; F77, F78, F80, F87; `quotes/math/pricing.py`,
`quotes/priced_spec.py`). Rounding is half up to the cent; a unit rate keeps the decimals it was stated in, two to
four, as in the old app."""

from decimal import Decimal

import pytest

from quotes import math as m
from quotes import packages as pk
from quotes import priced_spec
from quotes.math import pricing
from quotes.shapes import LineData, PlanData

D = Decimal


@pytest.mark.parametrize(
    ('op', 'value', 'expected'),
    [
        ('pct_off', '5', D('475')),
        ('pct_up', '3', D('515')),
        ('flat_off', '10', D('490')),
        ('flat_up', '10', D('510')),
        ('set', '480', D('480')),
    ],
)
def test_F77_each_operation_on_a_rate(op, value, expected):
    assert pricing.change_rate(D('500'), op, D(value)) == expected


def test_F77_a_relative_change_skips_a_rate_never_stated_but_set_to_does_not():
    ops = [{'key': 'rate_ee', 'op': 'pct_off', 'value': 5}, {'key': 'rate_es', 'op': 'set', 'value': 900}]
    assert pricing.concession({}, ops) == {'rate_es': '900'}


def test_F77_rates_round_half_up_to_the_cent_and_a_unit_rate_keeps_its_stated_decimals():
    assert pricing.concession({'rate_ee': '489.15'}, [{'key': 'rate_ee', 'op': 'pct_off', 'value': 5}]) == {
        'rate_ee': '464.69'  # 464.6925
    }
    assert pricing.concession({'unit_rate': '0.085'}, [{'key': 'unit_rate', 'op': 'pct_off', 'value': 5}]) == {
        'unit_rate': '0.081'  # 0.08075, kept to the three decimals it was stated in (never 0.08)
    }
    assert pricing.concession({'unit_rate': '0.15'}, [{'key': 'unit_rate', 'op': 'flat_off', 'value': '0.005'}]) == {
        'unit_rate': '0.145'
    }


def test_F77_a_change_below_zero_refuses_naming_the_rate():
    with pytest.raises(pricing.BelowZero) as below:
        pricing.concession({'rate_ee': '150'}, [{'key': 'rate_ee', 'op': 'flat_off', 'value': 200}])
    assert (below.value.key, below.value.amount) == ('rate_ee', -50)
    assert priced_spec.below_zero(below.value) == 'Rate — EE: the change lands below zero (-50).'


def test_F78_bundle_parts_add_and_subtract_and_dollars_skip_the_quoted_premium():
    parts = [
        {'op': 'pct_off', 'value': 2},
        {'op': 'pct_off', 'value': 1.5},
        {'op': 'pct_up', 'value': 0.5},
        {'op': 'flat_off', 'value': 10},
    ]
    pct, flat = pricing.bundle_totals(parts)
    assert (pct, flat) == (D('3'), D('10'))
    values = {'rate_ee': '500', 'group_premium_monthly': '20000'}
    assert pricing.bundle(values, ['rate_ee', 'rate_es'], pct, flat) == {
        'rate_ee': '475',  # 500 × 0.97 − 10
        'group_premium_monthly': '19400',  # × 0.97 only
    }


@pytest.mark.parametrize(
    ('credit', 'monthly', 'annual', 'base', 'expected'),
    [
        ({'annual': 3000.4}, 1000, 12000, 12000, (3000, None, 9000, -25.0, None)),
        ({'months': 2}, 1000, 12000, 10000, (2000, 2, 10000, 0.0, None)),
        ({'annual': 13000}, 1000, 12000, 12000, (13000, None, None, None, 'credit_exceeds_year')),
        ({'months': 1}, None, None, 12000, (None, 1, None, None, 'no_price')),
        ({'annual': 500}, 1000, 12000, None, (500, None, 11500, None, None)),
    ],
)
def test_F80_net_after_credit(credit, monthly, annual, base, expected):
    out = pricing.net_after_credit(credit, monthly, annual, base)
    pct = out['change']['pct'] if out['change'] else None
    assert (out['annual'], out['months'], out['net_annual'], pct, out['reason']) == expected


def version_line(original_counts, version_counts=None, role='alternate'):
    current = PlanData(id=1, role='current', values={'rate_ee': '500'}, enrollment={'EE': 10}, enrollment_on=True)
    quote = PlanData(
        id=2,
        role=role,
        renews=1 if role == 'renewal' else None,
        replaces=(1,) if role == 'alternate' else (),
        values={'rate_ee': '600'},
        enrollment=original_counts or {},
        enrollment_on=bool(original_counts),
    )
    version = PlanData(
        id=3,
        role='alternate',
        replaces=(1,),
        values={'rate_ee': '570'},
        enrollment=version_counts or {},
        enrollment_on=bool(version_counts),
        version_of=2,
        credit={'months': 1},
    )
    return LineData('composite', [current, quote, version])


def test_F87_a_priced_version_prices_its_originals_people():
    line = version_line({'EE': 7})  # the quote's own typed counts, not the current plan's 10
    figures, source = m.enrollment_for(line.by_id[3], line)
    assert (figures, source) == ({'EE': D(7), 'ES': D(0), 'EC': D(0), 'FAM': D(0)}, 'from original plan')
    renewal = version_line(None, role='renewal')  # the original priced from its current plan: the same people
    assert m.enrollment_for(renewal.by_id[3], renewal)[0]['EE'] == D(10)


def test_F87_a_version_with_its_own_typed_counts_uses_them():
    line = version_line({'EE': 7}, {'EE': 4})
    assert m.enrollment_for(line.by_id[3], line) == ({'EE': D(4), 'ES': D(0), 'EC': D(0), 'FAM': D(0)}, 'typed')


def test_F80_a_holiday_versions_credit_rides_its_result_and_nets_against_the_base():
    line = version_line(None, role='renewal')
    result = pk.evaluate(line)[3]
    assert (result['monthly'], result['annual'], result['change']['pct']) == (5700, 68400, 14.0)
    assert result['credit'] == {
        'annual': 5700,
        'months': 1,
        'net_annual': 62700,
        'change': {'delta': 2700, 'pct': 4.5},
        'reason': None,
    }
    assert pk.evaluate(line)[2]['credit'] is None


def clean(body, line='medical', lookup=lambda plan_id: None):
    return priced_spec.clean(line, body, lookup)


def test_F77_a_percentage_on_all_rates_reaches_the_quoted_premium_and_a_dollar_amount_does_not():
    pct = clean({'kind': 'concession', 'all': {'op': 'pct_off', 'value': '5'}})
    assert [op['key'] for op in pct.ops] == ['rate_ee', 'rate_es', 'rate_ec', 'rate_fam', 'group_premium_monthly']
    assert pct.label == '5% concession'
    flat = clean({'kind': 'concession', 'all': {'op': 'flat_off', 'value': 10}})
    assert [op['key'] for op in flat.ops] == ['rate_ee', 'rate_es', 'rate_ec', 'rate_fam'] and flat.label == '$10 off'


def test_F77_per_rate_overrides_keep_a_rate_out_or_change_it_alone():
    spec = clean(
        {
            'kind': 'concession',
            'all': {'op': 'pct_off', 'value': 2.5},
            'each': {'rate_ee': 'keep', 'rate_fam': {'op': 'set', 'value': '1400'}},
        }
    )
    assert {op['key']: (op['op'], op['value']) for op in spec.ops} == {
        'rate_es': ('pct_off', 2.5),
        'rate_ec': ('pct_off', 2.5),
        'rate_fam': ('set', 1400),
        'group_premium_monthly': ('pct_off', 2.5),
    }
    assert spec.label == 'concession'  # mixed
    assert clean({'kind': 'concession', 'all': {'op': 'pct_up', 'value': 3}}).label == '3% increase'
    assert clean({'kind': 'concession', 'all': {'op': 'flat_up', 'value': 12.5}}).label == '$12.50 increase'


@pytest.mark.parametrize(
    ('body', 'sentence'),
    [
        ({'kind': 'gift'}, 'Pick a concession, a bundling discount or a premium holiday.'),
        ({'kind': 'concession'}, 'Set a change for all rates, or for at least one rate.'),
        ({'kind': 'concession', 'all': {'op': 'pct_off', 'value': 120}}, 'All rates: the percentage must be between'),
        ({'kind': 'concession', 'all': {'op': 'flat_off', 'value': 'ten'}}, 'All rates needs a number for its change.'),
        ({'kind': 'concession', 'each': {'deductible_single': {'op': 'set', 'value': 1}}}, 'a changed plan design'),
        ({'kind': 'bundle', 'parts': []}, 'A bundling discount needs at least one line'),
        ({'kind': 'bundle', 'parts': [{'line': 'dental', 'op': 'pct_off', 'value': 60}]}, 'between 0 and 50'),
        ({'kind': 'holiday', 'credit': {}}, 'A premium holiday needs a dollar credit or a number of free months.'),
        ({'kind': 'holiday', 'credit': {'months': 13}}, 'Free months must be between 1 and 12.'),
        ({'kind': 'holiday', 'credit': {'annual': -5}}, 'The premium-holiday credit must be a positive dollar amount.'),
    ],
)
def test_F82_one_cleaner_refuses_what_a_version_cannot_be_made_of(body, sentence):
    with pytest.raises(priced_spec.SpecError) as error:
        clean(body)
    assert sentence in str(error.value)


def test_F78_a_bundle_names_its_lines_and_the_quote_that_has_to_sell():
    plans = {7: ('dental', 'Aetna Dental PPO'), 8: ('vision', 'VSP Choice')}
    spec = clean(
        {
            'kind': 'bundle',
            'parts': [
                {'line': 'dental', 'op': 'pct_off', 'value': 2, 'plan_id': 7},
                {'line': 'vision', 'op': 'pct_off', 'value': 0.5, 'plan_id': '8'},
                {'line': 'std', 'op': 'pct_off', 'value': ''},  # untouched: not bundled
                {'line': 'ltd', 'op': 'flat_off', 'value': 0},
            ],
            'conditional': False,
        },
        lookup=plans.get,
    )
    assert spec.label == '2.5% bundled (Dental + Vision)'
    assert spec.requires == [7, 8] and spec.conditional is False
    assert spec.parts[0] == {
        'line': 'dental',
        'op': 'pct_off',
        'value': 2,
        'plan_id': 7,
        'plan_label': 'Aetna Dental PPO',
    }
    with pytest.raises(priced_spec.SpecError) as wrong:
        clean({'kind': 'bundle', 'parts': [{'line': 'vision', 'value': 1, 'plan_id': 7}]}, lookup=plans.get)
    assert str(wrong.value) == 'Vision: Aetna Dental PPO is a Dental plan.'
    with_carrier = clean(
        {'kind': 'bundle', 'parts': [{'line': 'dental', 'op': 'flat_up', 'value': 3, 'carrier': 'UHC'}]}
    )
    assert with_carrier.label == '$3 up bundled (Dental)' and with_carrier.parts[0]['carrier'] == 'UHC'


def test_F82_a_typed_name_stands_on_one_version_and_is_each_plans_suffix_across_several():
    spec = clean({'kind': 'holiday', 'credit': {'months': 1}, 'name': 'Negotiated'})
    assert priced_spec.name_for('HMO 1500', spec) == 'Negotiated'
    assert priced_spec.name_for('HMO 1500', spec, multi=True) == 'HMO 1500 — Negotiated'
    unnamed = clean({'kind': 'holiday', 'credit': {'annual': 3000}})
    assert priced_spec.name_for('HMO 1500', unnamed) == 'HMO 1500 — premium holiday'
