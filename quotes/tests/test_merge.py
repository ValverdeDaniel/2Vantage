"""The one merge service (plan.md §5.4; F142, O.6 #32): a rate page's row and an SBC's column of one plan become one.
No endpoint: the reader's combine and Claude's `merge_plans` call it in later slices."""

import pytest
from rest_framework.exceptions import ValidationError

from conftest import write_path_contract
from deals import activity
from deals.values import source
from quotes import services
from quotes.models import Plan

pytestmark = pytest.mark.django_db


@pytest.fixture
def line(user, deal):
    current = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='HMO 1500')
    rates = services.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='Cigna',
        name='LocalPlus 3000',
        replaces_ids=[current.id],
        values={'rate_ee': '489.15', 'rate_fam': '1508.92', 'deductible_single': '3500'},
    )
    sbc = services.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='Cigna',
        name='LocalPlus 3000 SBC',
        values={'deductible_single': '3000', 'oop_max_single': '6500', 'pcp_copay': '30'},
    )
    Plan.objects.filter(pk=sbc.id).update(
        codes=['LP3000'],
        sources={
            **Plan.objects.get(pk=sbc.id).sources,
            'oop_max_single': {**source('ai', doc=41, page=2, read_value='6500'), 'mark': {'state': 'check'}},
        },
    )
    Plan.objects.filter(pk=rates.id).update(codes=['CG-77'])
    return {'current': current, 'rates': rates, 'sbc': sbc}


def fresh(plan):
    return Plan.all_objects.get(pk=plan.id)


def test_F142_the_kept_plan_takes_what_it_lacks_with_its_source_and_the_other_is_removed(user, deal, line):
    rates, sbc = line['rates'], line['sbc']
    kept, changed, row = services.merge_plans(user, deal, rates.id, [sbc.id])
    after = fresh(rates)
    assert after.values == {
        'rate_ee': '489.15',
        'rate_fam': '1508.92',
        'deductible_single': '3500',
        'oop_max_single': '6500',
        'pcp_copay': '30',
    }  # its own deductible stays
    entry = after.sources['oop_max_single']
    assert (entry['origin'], entry['doc'], entry['page'], entry['read_value']) == ('ai', 41, 2, '6500')
    assert 'mark' not in entry
    assert after.codes == ['CG-77', 'LP3000']
    assert fresh(sbc).removed_at is not None and [plan.id for plan in changed] == [rates.id]
    assert row.action == 'merged' and row.summary == 'Merged Cigna LocalPlus 3000 SBC into Cigna LocalPlus 3000'


def test_F142_named_keys_take_the_merged_value_and_revert_puts_both_back(user, deal, line):
    rates, sbc = line['rates'], line['sbc']
    before = (fresh(rates).values, fresh(rates).codes)
    _, _, row = services.merge_plans(user, deal, rates.id, [sbc.id], overwrite=['deductible_single'])
    assert fresh(rates).values['deductible_single'] == '3000'
    activity.revert(row.id, user)
    assert (fresh(rates).values, fresh(rates).codes) == before and fresh(sbc).removed_at is None


def test_F142_Q3_merge_write_path(user, deal, line):
    rates, sbc = line['rates'], line['sbc']
    write_path_contract(
        user,
        rates,
        call=lambda: services.merge_plans(user, deal, rates.id, [sbc.id]),
        read=lambda p: (p.values, p.codes, fresh(sbc).removed_at is None),
        later=lambda: services.update_plan(user, rates.id, {'values': {'pcp_copay': '35'}}),
    )


def test_F142_refusals_are_in_words(user, deal, line):
    rates, sbc = line['rates'], line['sbc']
    services.set_sold(user, sbc.id, True)
    with pytest.raises(activity.Refused) as refused:
        services.merge_plans(user, deal, rates.id, [sbc.id])
    assert refused.value.sentence == 'Cigna LocalPlus 3000 SBC is sold, so it is not merged.'
    services.set_sold(user, sbc.id, False)
    dental = services.create_plan(user, deal, line='dental', role='alternate', carrier='Cigna', name='Dental 50')
    with pytest.raises(activity.Refused) as refused:
        services.merge_plans(user, deal, rates.id, [dental.id])
    assert refused.value.sentence == 'Cigna Dental 50 is on another line: only plans of one line merge.'
    with pytest.raises(ValidationError):
        services.merge_plans(user, deal, rates.id, [rates.id])
    with pytest.raises(ValidationError):
        services.merge_plans(user, deal, rates.id, [sbc.id], overwrite=['den_annual_max'])
