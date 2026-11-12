"""GD1 on the Advisor's rules (plan.md §13.6 rows 7 and 8, "done when"; Q.9 rows 7 and 8). The deal comes from the
root conftest's `gd1` fixture, built once for the module. Slice 7's tests only read it; slice 8's write through the
services, and their writes roll back with each test's transaction, so GD1 stays as built."""

import pytest

from deals import activity
from quotes import order, presented, services
from quotes.models import Plan
from quotes.selectors import line_state

pytestmark = pytest.mark.django_db


def test_F50_J15_GD1_medical_has_room_for_two_more_columns_its_pair_counting_once(gd1):
    data = line_state(gd1.deal, 'medical').data
    assert presented.room(data) == 2  # 15 plans held; Florida Blue's 05182 and 05183 print as one column (slice 33)
    assert presented.refusal(data, 'Medical', 4) == (
        'The Medical proposal holds 16 plans (3 current, 4 recommended, 7 starred): 4 ticked, only 2 more fit. '
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
    expected = ['A', 'B', 'C', 'A2', 'CG1', 'CG1N', 'CG2', 'U1', 'D1', 'D2', 'B2', 'CG3', 'U2', 'U5', 'FB1', 'FB2']
    expected += ['C2', 'CG4', 'U3']  # both halves of the Florida Blue pair stay plans on working screens (D-219)
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


def test_17_GD1_stored_flags_equal_a_rebuild_and_the_board(gd1, admin_api):
    """Slice 17 (Q.9 row 17, Q.3 #9): GD1's stored open-warning counts equal a fresh rebuild, and the board's own count
    on every plan. GD1's file values were typed with their file, so nothing on it needs review yet (OQ28)."""
    from quotes import flags

    assert flags.rebuild([gd1.deal.id]) == []
    plans = admin_api.get(f'/api/deals/{gd1.deal.id}/plans/', {'line': 'medical'}).json()['plans']
    stored = dict(Plan.objects.filter(deal=gd1.deal).values_list('id', 'flags'))
    assert {plan['id']: plan['facts']['flags'] for plan in plans} == {plan['id']: stored[plan['id']] for plan in plans}


def test_17_GD1_a_flag_on_a_value_from_the_cigna_file_shows_on_both_screens_and_undoes_once(gd1, admin_api):
    """Slice 17's done-when, server half: ⚑ on a value from the Cigna workbook makes the station's strip read "1 AI
    value to review · 1 need checking" and the Advisor's count 1 on that plan; the review's one Activity row holds
    marks, never the value, and Undo puts it back once."""
    from deals.models import Activity
    from documents.models import Document

    cigna = Document.objects.get(deal=gd1.deal, kind='quote')
    base = f'/api/deals/{gd1.deal.id}/plans/'
    rows = admin_api.get(f'{base}sources/', {'documents': cigna.id}).json()
    assert rows['warnings']['open'] == 0 and rows['rows']
    assert {row['bucket'] for row in rows['rows']} <= {'unchecked', 'found', 'absent'}
    target = next(row for row in rows['rows'] if row['plan_id'] == gd1.refs['CG2'] and row['key'] == 'rate_ee')
    answer = admin_api.post(f'{base}marks/', {'action': 'check', 'refs': [target['ref']]}, format='json').json()
    assert answer['changed'] == 1
    assert [(plan['id'], plan['flags']) for plan in answer['plans']] == [(gd1.refs['CG2'], 1)]
    strip = admin_api.get(f'{base}sources/', {'documents': cigna.id}).json()['warnings']
    assert strip == {'open': 1, 'check': 1, 'unflagged': 0}
    board = {plan['id']: plan for plan in admin_api.get(base, {'line': 'medical'}).json()['plans']}
    assert board[gd1.refs['CG2']]['facts']['flags'] == 1 == Plan.objects.get(pk=gd1.refs['CG2']).flags
    assert board[gd1.refs['CG2']]['cells']['rate_ee']['s'] == 'to_check'
    row = Activity.objects.get(pk=answer['activity_id'])
    assert target['value'] not in repr(row.changes) and row.action == 'marked'
    assert admin_api.post(f'/api/activity/{row.id}/revert/').status_code == 200
    assert Plan.objects.get(pk=gd1.refs['CG2']).flags == 0
    assert admin_api.post(f'/api/activity/{row.id}/revert/').status_code == 409


def test_F76_F87_GD1_five_percent_off_previews_its_total_and_commits_a_copy_behind_its_original(gd1, user):
    """Slice 35's done-when: "5% off" CG2 previews its total, and commits a copy right behind CG2 that prices the same
    people (A's 10·3·2·5). By hand: 454.29 × 10 + 976.72 × 3 + 851.33 × 2 + 1,401.39 × 5 = $16,182.67 → $16,183 a
    month; against A's $18,251 a month, −11.3%. GD1's medical line has stars and room, so the version is starred
    (F83)."""
    from quotes.services import priced

    refs, deal = gd1.refs, gd1.deal
    five_off = {'kind': 'concession', 'all': {'op': 'pct_off', 'value': 5}}
    (draft,) = priced.price(user, deal, [refs['CG2']], five_off, dry_run=True).drafts
    assert (draft['premium']['monthly'], draft['change']['pct']) == (16183, -11.3)
    before = line_state(deal, 'medical')
    (version,) = priced.price(user, deal, [refs['CG2']], five_off).plans
    after = line_state(deal, 'medical')
    ids = [plan.id for plan in after.plans]
    assert ids.index(version.id) == ids.index(refs['CG2']) + 1
    assert [plan_id for plan_id in ids if plan_id != version.id] == [plan.id for plan in before.plans]  # none moved
    result = after.results[version.id]
    assert (result['monthly'], result['change']) == (draft['premium']['monthly'], draft['change'])
    people = {'EE': 10, 'ES': 3, 'EC': 2, 'FAM': 5}
    assert result['enrollment_used'] == before.results[refs['CG2']]['enrollment_used'] == people
    assert Plan.objects.get(pk=version.id).starred
