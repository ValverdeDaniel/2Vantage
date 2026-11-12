"""The executive summary's blocks as table cases (plan.md §8.14; J64–J66; Q.9 row 26 "summary-block tables"; OQ38).
Pure: hand-built facts in the shape `summary_read` gives, every figure as quotes would have worked it out."""

import pytest

from proposals import summary_blocks as summary
from proposals.summary_blocks import catalog

NO_MARKETS = {'has_asks': False, 'auto': False, 'override': None, 'on': False, 'lines': []}


def plan(pid, carrier, monthly, *, bases=(), change=None, credit=None, **values):
    return {
        'id': pid,
        'words': f'{carrier} Plan {pid}',
        'carrier': carrier,
        'name': f'Plan {pid}',
        'monthly': monthly,
        'annual': None if monthly is None else monthly * 12,
        'change': change,
        'bases': list(bases),
        'credit': credit,
        'values': values,
    }


def line(key='medical', *, currents=(), options=(), picks=(), state='shopped', no_people=False, package=None):
    return {
        'key': key,
        'label': key.capitalize(),
        'state': state,
        'shopping': state != 'presented',
        'field_set': key if key in ('medical', 'dental', 'vision') else 'generic',
        'composite': True,
        'no_people': no_people,
        'people': {'figures': {'EE': 10, 'ES': 2, 'EC': 0, 'FAM': 3}, 'source': 'census'},
        'currents': list(currents),
        'options': list(options),
        'quotes': list(options),
        'picks': list(picks),
        'current_package': package,
    }


def facts(*lines, new_business=False, offer=None, ages=None, markets=NO_MARKETS):
    return {
        'lines': list(lines),
        'new_business': new_business,
        'renewal_offer': offer,
        'ages': ages,
        'markets': markets,
    }


def block(found, key, line_key=''):
    return next(b for b in summary.build(found, [{'key': key}]) if b['line'] == line_key)


TODAY = plan(1, 'Aetna', 1000, deductible_single='2000', rate_ee='500.00')
CHEAPER = plan(
    2, 'Cigna', 900, bases=[1], change={'delta': -1200, 'pct': -10.0}, deductible_single='3000', rate_ee='450'
)
DEARER = plan(3, 'UnitedHealthcare', 1100, bases=[1], change={'delta': 1200, 'pct': 10.0})
MEDICAL = line(currents=[TODAY], options=[CHEAPER, DEARER], picks=[CHEAPER])


def test_J64_the_standard_set_leads_with_today_and_a_new_group_gets_the_new_business_set():
    keys = [spec['key'] for spec in summary.standard(facts(MEDICAL))]
    assert keys == list(catalog.DEFAULT_BLOCKS)
    new_group = line(options=[CHEAPER], picks=[CHEAPER])
    assert [spec['key'] for spec in summary.standard(facts(new_group))] == list(catalog.NEW_BUSINESS_BLOCKS)


def test_J65_J66_the_renewal_and_medicare_figures_join_only_when_their_facts_exist():
    ages = {'rows': 30, 'with_dob': 30, 'employees_65': 1, 'dependents_65': 1, 'as_of': '01/01/2027'}
    keys = [spec['key'] for spec in summary.standard(facts(MEDICAL, ages=ages, offer={'renewal_pct_change': 8.5}))]
    assert keys[-3:] == ['medicare_eligible', 'renewal_offer', 'renewal_vs_recommended']
    none_over = {**ages, 'employees_65': 0, 'dependents_65': 0}
    assert 'medicare_eligible' not in [s['key'] for s in summary.standard(facts(MEDICAL, ages=none_over))]


@pytest.mark.parametrize(
    ('key', 'value_label', 'sub', 'delta_label'),
    [
        ('current_cost', '$1,000/mo', 'Aetna Plan 1 · $12,000/yr', ''),
        ('best_option', '$900/mo', 'Cigna Plan 2', '-$100/mo (-10.0%)'),
        ('recommended', '$900/mo', 'Cigna Plan 2', '-$100/mo (-10.0%)'),
        ('spread', '$900 – $1,100/mo', 'Cigna Plan 2 … UnitedHealthcare Plan 3', ''),
        ('annual_delta', '$1,200 saved', 'over 12 months vs the current plan (-10.0%)', ''),
        ('ee_only', '$450.00/mo', 'was $500.00', '-$50.00'),
        ('deductible_move', '$3,000', 'was $2,000', '$1,000'),
        ('enrollment', '15 enrolled', '10 × EE · 2 × ES · 3 × FAM — from the census', ''),
    ],
)
def test_J64_line_blocks_read_quotes_figures_and_print_them_once(key, value_label, sub, delta_label):
    found = block(facts(MEDICAL), key, 'medical')
    assert found['available'], found['reason']
    assert (found['value_label'], found['sub'], found['delta_label']) == (value_label, sub, delta_label)


@pytest.mark.parametrize(
    ('medical', 'key', 'reason'),
    [
        (line(currents=[TODAY], options=[CHEAPER]), 'recommended', 'No plan is recommended on this line yet'),
        (
            line(currents=[TODAY], options=[CHEAPER, DEARER], picks=[CHEAPER, DEARER]),
            'recommended',
            'Several plans are recommended on this line — this figure needs one',
        ),
        (line(options=[CHEAPER], state='gap'), 'current_cost', 'Not in force today — this line is a proposed addition'),
        (
            line(currents=[plan(1, 'Aetna', None)], options=[CHEAPER], no_people=True),
            'current_cost',
            'No enrollment counted on this line',
        ),
        (line(currents=[TODAY], options=[CHEAPER]), 'spread', 'Needs at least two priced quotes'),
        (MEDICAL, 'lf_claims_pct', 'The recommended plan has no level-funded breakout'),
        (MEDICAL, 'oop_move', 'The recommended plan has no out-of-pocket max (single)'),
    ],
)
def test_J64_a_block_that_cannot_be_worked_out_says_why_and_never_prints_a_zero(medical, key, reason):
    found = block(facts(medical), key, 'medical')
    assert not found['available'] and found['reason'] == reason and found['value_label'] == ''


def _several(picks):
    first, second = plan(1, 'Aetna', 1000), plan(2, 'Aetna', 500)
    swap = plan(3, 'Cigna', 800, bases=[1], change={'delta': -2400, 'pct': -20.0})
    package = {'monthly': 1500, 'annual': 18000}
    return line(currents=[first, second], options=[swap], picks=picks(first, second, swap), package=package)


def test_J64_several_current_plans_add_up_pair_by_pair():
    keep_second = _several(lambda first, second, swap: [swap])  # the second current plan stays as it is
    found = block(facts(keep_second), 'recommended', 'medical')
    assert (found['value_label'], found['delta_label']) == ('$1,300/mo', '-$200/mo (-13.3%)')
    assert block(facts(keep_second), 'current_cost', 'medical')['value_label'] == '$1,500/mo'
    assert block(facts(keep_second), 'annual_delta', 'medical')['value_label'] == '$2,400 saved'
    unanswered = _several(lambda first, second, swap: [])
    reason = block(facts(unanswered), 'recommended', 'medical')['reason']
    assert reason == 'A current plan on this line has no recommendation yet'


def test_J64_the_deal_totals_refuse_to_half_add():
    dental_today = plan(10, 'Guardian', 200)
    dental_quote = plan(11, 'Delta', 180, bases=[10], change={'delta': -240, 'pct': -10.0})
    dental = line('dental', currents=[dental_today], options=[dental_quote], picks=[dental_quote])
    both = facts(MEDICAL, dental)
    assert block(both, 'total_current')['value_label'] == '$1,200/mo'
    total = block(both, 'total_recommended')
    assert (total['value_label'], total['delta_label']) == ('$1,080/mo', '-$120/mo (-10.0%)')
    assert block(both, 'total_annual_delta')['value_label'] == '$1,440 saved'
    unpicked = line('dental', currents=[dental_today], options=[dental_quote])
    refused = block(facts(MEDICAL, unpicked), 'total_recommended')
    assert refused['reason'] == 'Not every line has a priced recommendation'
    assert block(facts(MEDICAL, unpicked), 'total_current')['available']  # today needs no recommendation


def test_J64_a_first_year_credit_nets_the_annual_figures_and_names_itself():
    credited = plan(
        2,
        'Cigna',
        900,
        bases=[1],
        change={'delta': -1200, 'pct': -10.0},
        credit={'annual': 900, 'net_annual': 9900, 'change': {'delta': -2100, 'pct': -17.5}, 'reason': None},
    )
    medical = line(currents=[TODAY], options=[credited], picks=[credited])
    found = block(facts(medical), 'annual_delta', 'medical')
    assert found['value_label'] == '$2,100 saved'
    assert found['sub'] == 'over 12 months vs the current plan (-17.5%), after $900 first-year credit'
    assert block(facts(medical), 'recommended', 'medical')['value_label'] == '$900/mo'  # monthly stays billed


def test_J64_new_business_proposes_every_line_and_prices_the_first_year():
    dental_quote = plan(11, 'Delta', 180)
    new_group = facts(
        line(options=[CHEAPER], picks=[CHEAPER]),
        line('dental', options=[dental_quote], picks=[dental_quote]),
        new_business=True,
    )
    assert block(new_group, 'lines_proposed')['sub'] == 'Medical, Dental — new group — every line is proposed coverage'
    first_year = block(new_group, 'first_year_cost')
    assert (first_year['value_label'], first_year['sub']) == ('$1,080/mo', '$12,960/yr as proposed')


def test_J65_OQ38_the_carriers_renewal_shows_its_percent_and_dollars_and_ours_against_it_in_points():
    offer = {'renewal_pct_change': 12.0, 'renewal_premium_annual': 13440, 'stated_current_premium_annual': 12000}
    theirs = block(facts(MEDICAL, offer=offer), 'renewal_offer')
    assert (theirs['value_label'], theirs['sub']) == ('+12.0%', '$13,440/yr as offered in the renewal letter')
    ours = block(facts(MEDICAL, offer=offer), 'renewal_vs_recommended')
    assert ours['value_label'] == '22.0 pts better than the renewal'
    assert ours['sub'] == '+12.0% offered · -10.0% as recommended (Cigna Plan 2)'
    assert block(facts(MEDICAL), 'renewal_offer')['reason'] == "No renewal letter's figures on this deal"


def test_J66_the_medicare_figure_is_counts_only_and_only_under_medical():
    ages = {'rows': 31, 'with_dob': 30, 'employees_65': 2, 'dependents_65': 1, 'as_of': '01/01/2027'}
    dental = line('dental', currents=[plan(10, 'Guardian', 200)])
    found = summary.build(facts(MEDICAL, dental, ages=ages), [{'key': 'medicare_eligible'}])
    assert [b['line'] for b in found] == ['medical']
    assert found[0]['value_label'] == '3 members 65+'
    assert found[0]['sub'] == (
        'At the 01/01/2027 effective date · 2 employees, 1 dependent · consider Medicare education · '
        '1 without a birth date'
    )
    assert block(facts(MEDICAL), 'medicare_eligible', 'medical')['reason'] == 'No census on this deal'


def test_J64_blocks_group_by_line_and_a_pin_keeps_a_block_to_one_line():
    dental = line('dental', currents=[plan(10, 'Guardian', 200)])
    picked = [{'key': 'current_cost'}, {'key': 'total_current'}, {'key': 'recommended', 'line': 'medical'}]
    found = summary.build(facts(MEDICAL, dental), picked)
    assert [(b['line'], b['key']) for b in found] == [
        ('medical', 'current_cost'),
        ('medical', 'recommended'),
        ('dental', 'current_cost'),
        ('', 'total_current'),
    ]
