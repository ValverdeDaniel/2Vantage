"""Duplicate a plan, keeping its rates (plan.md §5.4, §7.8; F81, D-049; slice 8 "done when": a copy keeps its rates)."""

import pytest

from deals.models import Activity
from deals.values import source
from quotes import order, services
from quotes.models import Plan
from quotes.shapes import LineData, PlanData

pytestmark = pytest.mark.django_db

RATES = {'rate_ee': '489.15', 'rate_es': '1051.67', 'rate_ec': '916.66', 'rate_fam': '1508.92'}


@pytest.fixture
def line(user, deal):
    a = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='HMO 1500')
    renewal = services.create_renewal(user, a.id)
    first = services.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='Cigna',
        name='HDHP 3000',
        replaces_ids=[a.id],
        values={**RATES, 'deductible_single': '3000', 'contrib_ee': '400'},
    )
    second = services.create_plan(
        user, deal, line='medical', role='alternate', carrier='UHC', name='Choice', replaces_ids=[a.id]
    )
    return {'a': a, 'renewal': renewal, 'first': first, 'second': second}


def copy(api, plan, **body):
    response = api.post(f'/api/plans/{plan.id}/copy/', body, format='json')
    assert response.status_code == 201, response.json()
    return response.json()


def test_F81_done_when_a_copy_keeps_its_rates_and_is_named(api, line):
    first = line['first']
    made = copy(api, first, name='HDHP 3000 negotiated')
    assert made['values'] == {**RATES, 'deductible_single': '3000', 'contrib_ee': '400'}
    assert made['name'] == 'HDHP 3000 negotiated' and made['carrier'] == 'Cigna'
    assert (made['role'], made['replaces_ids']) == ('alternate', [line['a'].id])
    row = Activity.objects.filter(action='created').latest('id')
    assert row.summary == 'Duplicated Cigna HDHP 3000 as HDHP 3000 negotiated' and not row.revertible


def test_F81_an_unnamed_copy_is_called_a_copy_and_records_where_it_came_from(api, user, line):
    made = Plan.objects.get(pk=copy(api, line['renewal'])['id'])
    assert made.name == 'HMO 1500 — copy'
    assert [p.id for p in made.replaces.all()] == [line['a'].id]  # a renewal's copy replaces its current plan
    assert made.derived_from_id == line['renewal'].id and made.derived['kind'] == 'duplicate'
    assert made.derived['by'] == user.id


def test_F81_a_copy_takes_sources_but_no_marks_approvals_or_read_value_and_never_a_pick(user, deal, line):
    first = Plan.objects.get(pk=line['first'].id)
    first.sources['rate_ee'] = {
        **source('ai', doc=7, page=2, read_value='489.15'),
        'mark': {'state': 'check'},
        'confirmed': {'by': user.id},
    }
    first.save()
    services.star(user, deal, [first.id], True)
    services.set_recommended(user, first.id, True)
    made = services.copy_plan(user, first.id)
    entry = made.sources['rate_ee']
    assert (entry['origin'], entry['doc'], entry['page']) == ('ai', 7, 2)
    assert not {'mark', 'confirmed', 'read_value'} & set(entry)
    assert (made.starred, made.recommended, made.sold) == (False, False, False)


def test_F81_a_copy_arrives_right_behind_its_original(api, deal, line):
    made = copy(api, line['first'])
    shown = [plan['id'] for plan in api.get(f'/api/deals/{deal.id}/plans/?line=medical').json()['plans']]
    a, renewal, first, second = (line[key].id for key in ('a', 'renewal', 'first', 'second'))
    assert shown == [a, renewal, first, made['id'], second]
    current_copy = copy(api, line['a'])  # a current plan's copy lands last among the quotes that replace it
    shown = [plan['id'] for plan in api.get(f'/api/deals/{deal.id}/plans/?line=medical').json()['plans']]
    assert shown[-1] == current_copy['id']


def test_F81_behind_places_a_copy_after_its_original_in_their_group():
    plans = [
        PlanData(1, 'current', sort_order=0),
        PlanData(2, 'current', sort_order=1),
        PlanData(3, 'alternate', replaces=(1,), sort_order=2),
        PlanData(4, 'alternate', replaces=(2,), sort_order=3),
        PlanData(5, 'alternate', replaces=(1,), sort_order=4),
        PlanData(6, 'alternate', replaces=(2,), sort_order=5),
    ]
    line = LineData('composite', plans, key='medical')

    def laid_out(hand):
        numbers = order.numbering(line, hand)
        moved = [PlanData(**{**vars(p), 'sort_order': numbers.get(p.id, p.sort_order)}) for p in plans]
        return [p.id for p in order.layout(LineData('composite', moved, key='medical'))]

    assert laid_out(order.behind(line, 6, 4)) == [1, 2, 3, 5, 4, 6]
    assert laid_out(order.behind(line, 5, 3)) == [1, 2, 3, 5, 4, 6]
    assert laid_out(order.behind(line, 3, 1)) == [1, 2, 5, 3, 4, 6]  # a current plan's copy: last in its group
