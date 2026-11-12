"""The employer's contribution on the client spreadsheet's Compare tab (plan.md §5.5, §9.4; J148; old Vantage
891f1b3 `presentation_math` / `contribution_math`): the inputs it starts from and each figure, as table cases."""

from decimal import Decimal

import pytest

from quotes.math import annual, contribution

RATES = {'EE': '500', 'ES': '1000', 'EC': '900', 'FAM': '1500'}
PEOPLE = {'EE': 10, 'ES': 3, 'EC': 2, 'FAM': 5}


@pytest.mark.parametrize(
    'paid, expected',
    [
        # 80% of the employee rate, 50% of every dependent cost: Bryke's two percents
        ({'EE': '400', 'ES': '650', 'EC': '600', 'FAM': '900'}, {'ee_pct': Decimal('0.8'), 'dep_pct': Decimal('0.5')}),
        # employee share only, no dependent tier states one: the employee percent alone
        ({'EE': '375'}, {'ee_pct': Decimal('0.75'), 'dep_pct': None}),
        # dependent shares that disagree: the dollars each tier pays
        ({'EE': '400', 'ES': '650', 'EC': '600', 'FAM': '850'}, {'tier': True}),
    ],
)
def test_J148_contribution_inputs_start_from_the_current_plans_own_share(paid, expected):
    found = contribution.inputs(RATES, paid, PEOPLE)
    if expected.get('tier'):
        assert found['ee_pct'] is None and found['tier']['FAM'] == Decimal('850')
    else:
        assert found['ee_pct'] == expected['ee_pct'] and found['dep_pct'] == expected['dep_pct']


def test_J148_nothing_honest_to_say_gives_no_input():
    assert contribution.inputs(RATES, {}, PEOPLE) == {'ee_pct': None, 'dep_pct': None, 'tier': None}
    # a tier with people and no figure: no dollars either
    assert contribution.inputs(RATES, {'EE': '600', 'ES': '650'}, PEOPLE)['tier'] is None


def test_J148_the_employer_figures_under_each_mode():
    pct = Decimal('0.8')
    assert contribution.for_employees(PEOPLE, RATES, pct) == Decimal(8000)  # 20 people × 500 × 0.8
    # (3 × 500 + 2 × 400 + 5 × 1000) × 0.5 = 3,650
    assert contribution.for_dependents(PEOPLE, RATES, Decimal('0.5')) == Decimal(3650)
    amounts = {'EE': '400', 'ES': None, 'EC': '950', 'FAM': '900'}
    assert contribution.for_employees(PEOPLE, RATES, pct, amounts) is None  # the dollars win
    assert contribution.for_tier(10, '500', '400', amounts) == Decimal(4000)
    assert contribution.for_tier(3, '1000', None, amounts) == Decimal(0)  # a tier left blank pays nothing
    assert contribution.for_tier(2, '900', '950', amounts) == Decimal(1800)  # never more than the rate
    assert contribution.employer_total(Decimal(4000), None, Decimal(1800)) == Decimal(5800)
    assert contribution.employee_total(17306, Decimal(5800)) == Decimal(11506)
    assert contribution.employee_total(5000, Decimal(5800)) == Decimal(0)
    assert annual(17306) == Decimal(207672) and annual(None) is None
