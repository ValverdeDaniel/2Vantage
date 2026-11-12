"""The rates grid and expected revenue (plan.md §5.6; H3–H8; Q.9 row 48: §5.6's 3,805 example, GD1). Behavioural,
through the payload the tab reads."""

import pytest

from commission import selectors, services
from conftest import make_deal
from deals.models import AgencySettings
from intake import services as intake
from quotes import services as quotes

pytestmark = pytest.mark.django_db


def plan(user, deal, line='medical', role='alternate', carrier='Cigna', name='Open Access', **kw):
    values = kw.pop('values', {})
    return quotes.create_plan(user, deal, line=line, role=role, carrier=carrier, name=name, values=values, **kw)


def counts(user, deal, line, **figures):
    quotes.set_enrollment(user, deal, line, plans=[{'id': pid, 'enrollment': e} for pid, e in figures.items()])


def rows(deal, user):
    deal.refresh_from_db()
    return {row['line']: row for row in selectors.deal_payload(deal, user)['rows']}


def agency(value):
    row = AgencySettings.get()
    row.default_commission = value
    row.save()


def test_H6_the_worked_example_three_sold_plans_at_5_percent_is_3805(user):
    deal = make_deal(user, requested_lines=('medical',))
    made = [plan(user, deal, name=f'Option {n}', values={'rate_ee': rate}) for n, rate in enumerate((2137, 2172, 2032))]
    quotes.set_enrollment(user, deal, 'medical', plans=[{'id': p.id, 'enrollment': {'EE': 1}} for p in made])
    for one in made:
        quotes.set_sold(user, one.id, True)
    services.update(user, deal.id, {'rates': {'medical': '5'}})
    medical = rows(deal, user)['medical']
    assert medical['basis']['key'] == 'sold'
    assert medical['basis']['annual'] == 76092  # every sold plan counts, not one (1,282 would be one)
    assert medical['expected'] == 3805


def test_H6_before_the_sale_renewal_then_current_then_the_starred_estimate(user):
    deal = make_deal(user, requested_lines=('medical', 'dental', 'vision'))
    agency({'type': 'pct', 'value': '10'})
    current = plan(user, deal, role='current', carrier='Aetna', name='HMO', values={'rate_ee': '500'})
    renewal = plan(user, deal, role='renewal', carrier='Aetna', name='HMO', renews_id=current.id)
    counts(user, deal, 'medical', **{str(current.id): {'EE': 10}})
    medical = rows(deal, user)['medical']
    assert medical['basis']['key'] == 'current'  # the renewal has no price yet: Current is the first with a total
    assert medical['expected'] == 6000  # 10 % of $60,000
    quotes.update_plan(user, renewal.id, {'values': {'rate_ee': '550'}})
    medical = rows(deal, user)['medical']
    assert (medical['basis']['key'], medical['expected']) == ('renewal', 6600)
    assert medical['source'] == 'agency' and medical['source_label'] == 'agency default'
    dental = plan(user, deal, line='dental', carrier='Delta', name='PPO', values={'rate_ee': '40'})
    counts(user, deal, 'dental', **{str(dental.id): {'EE': 5}})
    assert rows(deal, user)['dental']['basis'] is None  # a quote that is not starred is no basis
    quotes.star(user, deal, [dental.id], True)
    found = rows(deal, user)['dental']
    assert found['basis']['key'] == 'estimate' and found['basis']['label'] == 'Delta — PPO (estimate)'
    assert found['expected'] == 240
    assert rows(deal, user)['vision']['basis'] is None and rows(deal, user)['vision']['expected'] is None


def test_H6_once_sold_only_the_sold_package_counts_with_its_reason(user):
    deal = make_deal(user, requested_lines=('medical',))
    current = plan(user, deal, role='current', carrier='Aetna', name='HMO', values={'rate_ee': '500'})
    sold = plan(user, deal, carrier='Cigna', name='PPO', replaces_ids=[current.id])
    counts(user, deal, 'medical', **{str(current.id): {'EE': 10}})
    services.update(user, deal.id, {'rates': {'medical': '5'}})
    assert rows(deal, user)['medical']['expected'] == 3000  # Current before the sale
    quotes.set_sold(user, sold.id, True)
    medical = rows(deal, user)['medical']
    assert medical['basis']['key'] == 'sold' and medical['expected'] is None
    assert medical['basis']['reason'].startswith('PPO has no price')


def test_H7_pepm_uses_the_lines_own_employees_and_the_note_names_the_source(user):
    deal = make_deal(user, requested_lines=('medical', 'dental'))
    medical = plan(user, deal, role='current', carrier='Aetna', name='HMO', values={'rate_ee': '500', 'rate_es': '900'})
    dental = plan(user, deal, line='dental', role='current', carrier='Delta', name='PPO', values={'rate_ee': '40'})
    counts(user, deal, 'medical', **{str(medical.id): {'EE': 10, 'ES': 2}})
    counts(user, deal, 'dental', **{str(dental.id): {'EE': 7}})
    pepm, flat = {'type': 'pepm', 'value': '20'}, {'type': 'flat', 'value': '1000'}
    services.update(user, deal.id, {'rates': {'medical': pepm, 'dental': flat}})
    found = rows(deal, user)
    assert found['medical']['basis']['employees'] == 12 and found['medical']['expected'] == 2880  # 20 × 12 × 12
    assert found['dental']['basis']['employees'] == 7 and found['dental']['expected'] == 1000
    payload = selectors.deal_payload(deal, user)
    assert payload['total'] == 3880
    assert payload['note'] == 'Based on 12 enrolled on Medical (typed for this plan).'
    assert payload['basis'] == {'revenue': 3880, 'employees': 12, 'year': 1}


def test_H3_rows_are_the_requested_lines_plus_rated_sold_and_muted_in_force_lines(user):
    deal = make_deal(user, requested_lines=('dental',))
    services.update(user, deal.id, {'rates': {'vision': '8'}})
    intake.create_coverage(
        user, deal.id, {'line': 'std', 'carrier': 'Unum', 'commission': '12', 'commission_source': 'carrier'}
    )
    found = selectors.deal_payload(deal, user)['rows']
    assert [(row['line'], row['not_requested']) for row in found] == [
        ('dental', False),
        ('vision', False),
        ('std', True),
    ]
    std = found[-1]
    assert std['in_force'] == {
        'label': '12%',
        'carrier': 'Unum',
        'source': 'carrier',
        'source_label': 'Carrier told us',
    }
    assert std['rate'] is None and std['expected'] is None


def test_H4_the_in_force_carrier_comes_from_the_current_plans_before_the_coverage_row(user):
    deal = make_deal(user, requested_lines=('medical',))
    intake.create_coverage(user, deal.id, {'line': 'medical', 'carrier': 'Old Carrier', 'commission': '4'})
    assert rows(deal, user)['medical']['in_force']['carrier'] == 'Old Carrier'
    plan(user, deal, role='current', carrier='Aetna', name='HMO')
    found = rows(deal, user)['medical']['in_force']
    assert found['carrier'] == 'Aetna' and found['label'] == '4%'


def test_H8_the_agency_default_fills_a_line_with_no_agreed_rate(user):
    deal = make_deal(user, requested_lines=('medical', 'dental'))
    assert rows(deal, user)['medical']['source_label'] == 'not set'
    agency('5')
    services.update(user, deal.id, {'rates': {'dental': {'type': 'pct', 'value': '15'}}})
    found = rows(deal, user)
    assert (found['medical']['effective_label'], found['medical']['source']) == ('5%', 'agency')
    assert (found['dental']['effective_label'], found['dental']['source']) == ('15%', 'deal')
    assert selectors.requested_rates(deal) == {
        'medical': {'rate': {'type': 'pct', 'value': '5'}, 'source': 'agency'},
        'dental': {'rate': {'type': 'pct', 'value': '15'}, 'source': 'deal'},
    }


def test_H6_GD1_expected_revenue_is_the_rate_on_its_renewal(gd1, golden_keys, user):
    agency('5')
    found = {row['line']: row for row in selectors.deal_payload(gd1.deal, user)['rows']}
    key = golden_keys['GD1']['packages']
    assert found['medical']['basis']['annual'] == key['medical']['Renewal']['annual']
    assert found['medical']['expected'] == 29886  # 5 % of 597,720
    assert found['dental']['expected'] == 1387  # 5 % of 27,744 = 1,387.2
