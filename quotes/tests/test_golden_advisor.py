"""GD1 on the Advisor's rules (plan.md §13.6 rows 7 and 8, "done when"; Q.9 rows 7 and 8). The deal comes from the
root conftest's `gd1` fixture, built once for the module. Slice 7's tests only read it; slice 8's write through the
services, and their writes roll back with each test's transaction, so GD1 stays as built."""

import pytest

from deals import activity
from quotes import order, presented, services
from quotes.models import Plan
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


RATES = ('rate_ee', 'rate_es', 'rate_ec', 'rate_fam')


def figures(deal, line='medical'):
    results = line_state(deal, line).results
    return {pid: (r['monthly'], r['annual'], r['change']) for pid, r in results.items()}


def test_F60_GD1_deleting_a_current_plan_turns_its_renewal_into_an_alternate_and_revert_restores_both(gd1, user):
    refs, deal = gd1.refs, gd1.deal
    before = figures(deal)
    replacing_a = set(Plan.objects.filter(replaces=refs['A']).values_list('id', flat=True))
    removal = services.delete_plans(user, deal, [refs['A']])
    renewal = Plan.objects.get(pk=refs['A2'])
    assert (renewal.role, renewal.renews_id) == ('alternate', None)
    assert not Plan.objects.filter(replaces=refs['A']).exists()
    assert refs['A'] not in figures(deal)
    activity.revert(removal.row.id, user)
    renewal = Plan.objects.get(pk=refs['A2'])
    assert (renewal.role, renewal.renews_id) == ('renewal', refs['A'])
    assert set(Plan.objects.filter(replaces=refs['A']).values_list('id', flat=True)) == replacing_a
    assert figures(deal) == before  # every figure on the key is back


def test_F59_GD1_a_plan_moved_to_dental_keeps_its_id(gd1, user):
    refs, deal = gd1.refs, gd1.deal
    changed, _row = services.move_line(user, deal, [refs['U3']], 'dental')
    moved = Plan.objects.get(pk=refs['U3'])
    assert moved.line == 'dental' and refs['U3'] in [plan.id for plan in changed]
    assert refs['U3'] in [plan.id for plan in line_state(deal, 'dental').plans]
    with pytest.raises(activity.Refused) as refused:
        services.move_line(user, deal, [refs['CG1']], 'dental')  # CG1N, the negotiated option, is its copy
    assert refused.value.sentence.endswith(
        'has priced versions or copies, priced on its Medical rates. Remove them before moving it.'
    )


def test_F81_GD1_a_copy_keeps_its_rates(gd1, user):
    original = Plan.objects.get(pk=gd1.refs['CG2'])
    made = services.copy_plan(user, original.id)
    assert {key: made.values.get(key) for key in RATES} == {key: original.values.get(key) for key in RATES}
    assert all(made.values.get(key) for key in RATES)
    assert figures(gd1.deal)[made.id][:2] == figures(gd1.deal)[original.id][:2]  # the same rates, the same people


def test_F60_H6_GD1_a_sold_plan_cannot_be_deleted(gd1, user):
    plan_id = gd1.refs['U1']
    services.set_sold(user, plan_id, True)
    with pytest.raises(activity.Refused) as refused:
        services.delete_plans(user, gd1.deal, [plan_id])
    assert refused.value.sentence.endswith('is sold, so it stays. Unmark sold first.')
    assert Plan.objects.filter(pk=plan_id).exists()


def test_F93_GD1_the_board_export_equals_the_board(gd1, admin_api):
    """Slice 9's done-when: the export matches the screen — the Primary preset's columns, GD1's medical plans in the
    client's order, and every figure as the comparison payload gives it."""
    import io

    from openpyxl import load_workbook

    from quotes import board_export, board_presets
    from quotes.selectors import comparison

    keys = board_presets.columns('primary', 'medical')
    response = admin_api.get(
        f'/api/deals/{gd1.deal.id}/plans/board-export/', {'line': 'medical', 'columns': ','.join(keys)}
    )
    assert response.status_code == 200
    sheet = load_workbook(io.BytesIO(b''.join(response.streaming_content))).active
    cells = [[cell.value for cell in row] for row in sheet.iter_rows(min_row=5)]
    payload = comparison(gd1.deal, 'medical')
    _payload, plans, header, rows = board_export.table(gd1.deal, 'medical', None, keys)
    assert cells[0] == [label for label, _key, _kind in header]
    assert [plan['id'] for plan in plans] == [plan['id'] for plan in payload['plans']]
    assert [row[: len(header)] for row in cells[1:]] == rows
    total = [key for _label, key, _kind in header].index('total')
    assert [row[total] for row in cells[1:]] == [plan['premium']['monthly'] for plan in payload['plans']]


def test_F14_OQ14_GD1_the_finder_index_knows_every_UnitedHealthcare_plan(gd1, admin_api):
    """Slice 10's done-when, server half: "UHC" finds UnitedHealthcare plans on every line. The index lists every line
    at once and names each plan's carrier by the one matcher, so the browser's finder folds the alias "UHC" (from
    /api/meta/ carriers) into U1, U2, U3 and U5 ("UnitedHealthcare Consolidated"), and into nothing on dental or
    vision."""
    response = admin_api.get(f'/api/deals/{gd1.deal.id}/plans/find/')
    entries = response.json()['plans']
    assert {entry['line'] for entry in entries} == {'medical', 'dental', 'vision'}
    uhc = {entry['id'] for entry in entries if entry['carrier'] == 'unitedhealthcare'}
    assert uhc == {gd1.refs[ref] for ref in ('U1', 'U2', 'U3', 'U5')}
    carriers = admin_api.get('/api/meta/').json()['carriers']
    assert 'UHC' in next(c for c in carriers if c['key'] == 'unitedhealthcare')['aliases']


def test_F19_F140_GD1_every_plan_carries_its_total_and_its_numbers(gd1, admin_api):
    """Slice 10's done-when, server half: "Monthly total ≤ $45,000" compares the server's monthly total; the sliders
    and caps the server's numbers (F21)."""
    plans = admin_api.get(f'/api/deals/{gd1.deal.id}/plans/', {'line': 'medical'}).json()['plans']
    by_id = {plan['id']: plan for plan in plans}
    a = by_id[gd1.refs['A']]
    assert a['facts']['numbers']['deductible_single'] == 3300 and a['facts']['numbers']['rate_ee'] == 512.34
    assert 'pcp_copay' not in a['facts']['numbers']  # "Deductible, then 20%" is no number
    assert all(plan['premium']['monthly'] is not None for plan in plans)
