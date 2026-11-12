"""One plan under two plan numbers (plan.md §5.4; Q.9 row 22: "5182 / 5183" halves stay two plans; D116, D-219):
which plans are halves, a read's fresh halves staying two plans, and an "A / B" plan taking both halves."""

import pytest

from conftest import make_deal
from quotes import services, split
from quotes.reader import changes

HALF_EE = {'rate_ee': '612.45', 'deductible_single': '2500'}
HALF_DEP = {'rate_es': '1286.05', 'rate_ec': '1133.15', 'rate_fam': '1837.25', 'deductible_single': '5000'}


def plan_dict(number, values, key, carrier='Florida Blue', name='BlueOptions HSA'):
    return {
        'key': key,
        'line': 'medical',
        'side': 'quote',
        'carrier': carrier,
        'name': f'{name} {number}',
        'plan_number': number,
        'codes': [],
        'replaces': '',
        'unsure': False,
        'order': [0, 1, int(key[1:])],
        'docs': [],
        'renews': None,
        'values': {
            k: {'value': v, 'doc': None, 'page': 1, 'cell': '', 'unsure': False, 'label': k} for k, v in values.items()
        },
        'unmapped': [],
        'counts': {},
    }


def merged(*plans):
    return {'plans': list(plans), 'line_counts': {}, 'layouts': [], 'conflicts': []}


def flat(number, values, carrier='Florida Blue'):
    return {'line': 'medical', 'side': 'quote', 'carrier': carrier, 'plan_number': number, 'values': values}


def test_D116_halves_by_sibling_numbers_or_by_tiers_and_only_of_one_carrier():
    assert split.halves(flat('05182', {}), flat('05183', {}))
    assert split.halves(flat('', HALF_EE), flat('', HALF_DEP))
    assert not split.halves(flat('05182', {}), flat('05185', {}))
    assert not split.halves(flat('05182', {}), flat('05183', {}, carrier='Aetna'))
    assert not split.halves(flat('', HALF_EE), flat('', HALF_EE))


@pytest.mark.django_db
def test_D116_fresh_halves_stay_two_plans_with_a_finding(user):
    deal = make_deal(user)
    found = merged(plan_dict('05182', HALF_EE, 'm1'), plan_dict('05183', HALF_DEP, 'm2'))
    change_set = changes.build_changes(deal, user, found, [], {})
    made = [item for item in change_set['items'] if item['op'] == 'create_plan']
    assert [item['plan_number'] for item in made] == ['05182', '05183']
    assert any('stay two plans' in finding['text'] for finding in change_set['findings'])


@pytest.mark.django_db
def test_D116_an_a_b_plan_takes_both_halves(user):
    deal = make_deal(user)
    plan = services.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='Florida Blue',
        name='BlueOptions HSA',
        plan_number='05182 / 05183',
    )
    found = merged(plan_dict('05182', HALF_EE, 'm1'), plan_dict('05183', HALF_DEP, 'm2'))
    change_set = changes.build_changes(deal, user, found, [], {})
    [item] = [item for item in change_set['items'] if item['op'] != 'summary_counts']
    assert (item['op'], item['plan']) == ('set_values', plan.id)
    values = {value['key']: value['new'] for value in item['values']}
    assert values == {
        'rate_ee': '612.45',
        'rate_es': '1286.05',
        'rate_ec': '1133.15',
        'rate_fam': '1837.25',
        'deductible_single': '2500',
    }  # the employee-only half's deductible is kept
    assert any('2500' in f['text'] and '5000' in f['text'] for f in change_set['findings'])
