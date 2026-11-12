"""GD1 on the Advisor's slice-7 rules, read-only (plan.md §13.6 row 7's "done when"; Q.9 row 7). The deal comes from
the root conftest's `gd1` fixture; tests that write use factory deals (test_marks, test_roles, test_ordering)."""

import pytest

from quotes import order, presented
from quotes.selectors import line_state

pytestmark = pytest.mark.django_db


def test_F50_GD1_medical_has_room_for_three_more_columns(gd1):
    data = line_state(gd1.deal, 'medical').data
    assert presented.room(data) == 3
    assert presented.refusal(data, 'Medical', 4) == (
        'The Medical proposal holds 16 plans (3 current, 4 recommended, 6 starred): 4 ticked, only 3 more fit. '
        'Unstar some or tick fewer.'
    )


def test_F119_OQ11_GD1_presents_its_picks_and_only_the_picked_renewal(gd1):
    refs = gd1.refs
    shown = {plan.id for plan in presented.presented(line_state(gd1.deal, 'medical').data)}
    medical = {plan['ref'] for plan in gd1.spec['plans'] if plan['line'] == 'medical'}
    picked = (set(gd1.spec['starred']) | set(gd1.spec['recommended']) | {'A', 'B', 'C'}) & medical
    assert shown == {refs[ref] for ref in picked}
    assert refs['C2'] in shown and refs['A2'] not in shown and refs['B2'] not in shown


def test_F120_GD1_layout_groups_quotes_under_the_plans_they_replace(gd1):
    refs = gd1.refs
    plans = line_state(gd1.deal, 'medical').plans
    expected = ['A', 'B', 'C', 'A2', 'CG1', 'CG1N', 'CG2', 'U1', 'D1', 'D2', 'B2', 'CG3', 'U2', 'U5', 'C2', 'CG4', 'U3']
    assert [plan.id for plan in plans] == [refs[ref] for ref in expected]  # U5 replaces B and C: under B


def test_F120_GD1_a_rate_edit_would_move_nothing(gd1):
    data = line_state(gd1.deal, 'medical').data
    before = [p.id for p in order.layout(data)]
    for plan in data.plans:
        plan.values = {**plan.values, 'rate_ee': str(10_000 - plan.id)}
    assert [p.id for p in order.layout(data)] == before
