"""`GET proposal/pages/` on the golden deals, and the slot picks it is drawn for (plan.md §13.6 row 14, "done when";
§13.2's added row; Q.9 row 14: replace, swap, add beside, the recommendation lapses; Q.3 #5 on GD3). `gd1` is built
once for the module; the tests that write go through quotes' doors and roll back with each test's transaction."""

import pytest

from intake import services as intake
from quotes import services
from quotes.models import Plan

pytestmark = pytest.mark.django_db


def read(api, deal, line='medical', preset='primary'):
    response = api.get(f'/api/deals/{deal.id}/proposal/pages/', {'line': line, 'preset': preset})
    assert response.status_code == 200, response.content
    return response.json()


def post(api, deal, door, body):
    response = api.post(f'/api/deals/{deal.id}/plans/{door}/', body, format='json')
    assert response.status_code == 200, response.content
    return response.json()


def names(built):
    return {plan_id: ref for ref, plan_id in built.refs.items()}


def page_refs(body, built):
    named = names(built)
    return [[named[pid] for pid in page['plan_ids']] for page in body['pages']]


def column(body, built, ref):
    return next(entry for entry in body['plans'] if entry['plan_id'] == built.refs[ref])


GD1_PAGES = [['A', 'CG1', 'CG1N', 'U1', 'D1', 'D2'], ['B', 'CG3', 'U2', 'U5'], ['C', 'C2', 'CG4']]


def test_F37_J49_GD1_medical_prints_a_page_per_current_plan(api, gd1):
    body = read(api, gd1.deal)
    assert page_refs(body, gd1) == GD1_PAGES  # U5 replaces B and C: on B's page (its first)
    assert [page['label'] for page in body['pages']] == [
        'Replacing: Aetna Open Access HDHP 3300',
        'Replacing: Aetna Choice POS II PPO 1500',
        'Replacing: Aetna HMO 1000',
    ]
    assert [page['full'] for page in body['pages']] == [True, False, False]
    assert body['several'] and not body['nothing_starred'] and body['per_page'] == 6
    assert body['landing'][str(gd1.refs['A'])] == 'Page 1 is full. One more plan starts page 2.'
    assert body['landing'][str(gd1.refs['C'])] == 'Page 3 has room for 3 more plans.'
    off = {names(gd1)[entry['plan_id']] for entry in body['others']}
    assert off == {'A2', 'B2', 'CG2', 'U3'}  # OQ11: an unpicked renewal stays off a starred line


def test_F39_J159_GD1_columns_say_today_option_n_and_renewal(api, gd1, golden_keys):
    body = read(api, gd1.deal)
    plans = golden_keys['GD1']['plans']
    a = column(body, gd1, 'A')
    assert (a['title'], a['kind'], a['pickable'], a['chips'][0]['text']) == ('Today', 'current', False, 'CURRENT 1')
    assert a['replacing']['text'] == 'What they have today'
    assert a['monthly'] == f'${plans["A"]["monthly"]:,}'
    numbered = [column(body, gd1, ref)['option'] for page in GD1_PAGES for ref in page if ref not in ('A', 'B', 'C')]
    assert numbered == list(range(1, 11))  # reading order; renewals numbered, current plans not
    c2 = column(body, gd1, 'C2')
    assert (c2['kind'], c2['chips'][0]['text'], c2['chips'][0]['of'], c2['pickable']) == ('renewal', 'RENEWAL', 3, True)
    assert c2['replacing'] == {
        'ids': [gd1.refs['C']],
        'editable': False,
        'text': f'Replacing: Current 3 · ${plans["C"]["monthly"]:,}',
    }
    assert c2['change']['text'] == f'+${plans["C2"]["monthly"] - plans["C"]["monthly"]:,}/mo · +8.5%'
    cg1 = column(body, gd1, 'CG1')
    assert cg1['replacing'] == {'ids': [gd1.refs['A']], 'editable': True, 'text': ''}
    assert cg1['change']['text'] == '−$508/mo · −2.8%' and not cg1['change']['up']
    assert column(body, gd1, 'U5')['replacing']['ids'] == [gd1.refs['B'], gd1.refs['C']]


def test_F37_GD1_the_rows_are_the_presets_and_print_as_the_client_files(api, gd1):
    body = read(api, gd1.deal)
    assert [row['key'] for row in body['rows']] == ['deductible_single', 'oop_max_single']
    deductible = body['rows'][0]['cells']
    assert deductible[str(gd1.refs['A'])] == '$3,300' and deductible[str(gd1.refs['C'])] == '$1,000'
    every = read(api, gd1.deal, preset='all')['rows']
    assert {row['section'] for row in every} >= {'Plan info', 'Deductibles & maximums', 'Monthly rates'}
    assert 'mental_health_outpatient' not in {row['key'] for row in every}  # never on a client document


def test_F45_J10_GD1_a_pick_puts_the_plan_in_the_slot_with_its_star_and_link(api, gd1):
    refs = gd1.refs
    post(api, gd1.deal, 'slot', {'line': 'medical', 'plan_id': refs['CG2'], 'at': refs['CG3']})
    picked, left = Plan.objects.get(id=refs['CG2']), Plan.objects.get(id=refs['CG3'])
    assert picked.starred and list(picked.replaces.values_list('id', flat=True)) == [refs['B']]
    assert not left.starred
    body = read(api, gd1.deal)
    assert page_refs(body, gd1)[1] == ['B', 'CG2', 'U2', 'U5']  # CG3's place on B's page
    assert refs['CG3'] in {entry['plan_id'] for entry in body['others']}


def test_F45_J10_GD1_two_plans_on_the_proposal_trade_places_and_links(api, gd1):
    refs = gd1.refs
    post(api, gd1.deal, 'slot', {'line': 'medical', 'plan_id': refs['U1'], 'at': refs['CG3']})
    assert page_refs(read(api, gd1.deal), gd1)[:2] == [['A', 'CG1', 'CG1N', 'CG3', 'D1', 'D2'], ['B', 'U1', 'U2', 'U5']]


def test_J10_GD1_the_plan_picked_over_loses_its_recommendation(api, gd1):
    refs = gd1.refs
    post(api, gd1.deal, 'slot', {'line': 'medical', 'plan_id': refs['CG2'], 'at': refs['CG1']})
    left = Plan.objects.get(id=refs['CG1'])
    assert not left.starred and not left.recommended
    body = read(api, gd1.deal)
    assert page_refs(body, gd1)[0] == ['A', 'CG2', 'CG1N', 'U1', 'D1', 'D2']


def test_F46_J11_GD1_add_a_plan_beside_a_current_plan(api, gd1):
    refs = gd1.refs
    post(api, gd1.deal, 'slot', {'line': 'medical', 'plan_id': refs['CG2'], 'beside': refs['C']})
    body = read(api, gd1.deal)
    assert page_refs(body, gd1)[2] == ['C', 'C2', 'CG4', 'CG2']
    assert body['landing'][str(refs['C'])] == 'Page 3 has room for 2 more plans.'


def test_F52_J12_GD1_replacing_groups_a_quote_under_its_plan(api, gd1):
    refs = gd1.refs
    post(api, gd1.deal, 'links', {'plan_id': refs['CG3'], 'replaces_ids': [refs['C']]})
    pages = page_refs(read(api, gd1.deal), gd1)
    assert 'CG3' in pages[2] and 'CG3' not in pages[1]


def test_F52_J12_GD1_several_makes_a_consolidation(api, gd1):
    refs = gd1.refs
    post(api, gd1.deal, 'links', {'plan_id': refs['CG4'], 'replaces_ids': [refs['B'], refs['C']]})
    body = read(api, gd1.deal)
    assert 'CG4' in page_refs(body, gd1)[1]  # under the first plan it replaces
    assert column(body, gd1, 'CG4')['replacing'] == {'ids': [refs['B'], refs['C']], 'editable': True, 'text': ''}


def test_OQ13_F45_a_stop_loss_column_takes_a_slot_pick_with_the_slots_star_and_link(api, user, gd1):
    deal = gd1.deal
    intake.set_intent(user, deal.id, line='stop_loss', shop=True)

    def plan(role, name, **links):
        values = {'sl_spec_rate': '40', 'sl_lasers': 'S-1 100000'}  # synthetic
        return services.create_plan(
            user, deal, line='stop_loss', role=role, carrier='Synthetic Re', name=name, values=values, **links
        )

    s1, s2 = plan('current', 'Spec 50k'), plan('current', 'Spec 75k')
    q1 = plan('alternate', 'Spec 60k', replaces_ids=[s1.id])
    q2 = plan('alternate', 'Spec 90k', replaces_ids=[s2.id])
    services.star(user, deal, [q1.id], True)
    body = read(api, deal, 'stop_loss', 'all')
    q1_column = next(entry for entry in body['plans'] if entry['plan_id'] == q1.id)
    assert q1_column['pickable'] and q1_column['arrows'] is not None and q1_column['replacing']['editable']
    assert 'sl_lasers' not in {row['key'] for row in body['rows']}  # never on a client document (J.5 B3)
    post(api, deal, 'slot', {'line': 'stop_loss', 'plan_id': q2.id, 'at': q1.id})
    q2.refresh_from_db()
    assert q2.starred and list(q2.replaces.values_list('id', flat=True)) == [s1.id]
    body = read(api, deal, 'stop_loss')
    assert [page['plan_ids'] for page in body['pages']][0] == [s1.id, q2.id]
    assert q1.id in {entry['plan_id'] for entry in body['others']}


def test_J13_take_off_on_a_starred_line_unstars_and_says_the_recommendation(api, gd1):
    body = read(api, gd1.deal)
    assert column(body, gd1, 'CG1')['remove'] == {'unstar': True, 'unrecommend': True, 'star': [], 'why': None}
    assert column(body, gd1, 'A')['remove'] is None


def test_J13_B5_take_off_on_a_line_with_no_stars_stars_the_others_or_says_why_not(api, user, deal):
    current = services.create_plan(user, deal, line='dental', role='current', carrier='Guardian', name='Today')
    quotes = [
        services.create_plan(user, deal, line='dental', role='alternate', carrier='Delta', name=f'Quote {n}')
        for n in range(4)
    ]
    body = read(api, deal, 'dental')
    first = next(entry for entry in body['plans'] if entry['plan_id'] == quotes[0].id)
    assert body['nothing_starred'] and first['remove']['star'] == [plan.id for plan in quotes[1:]]
    for n in range(4, 17):
        services.create_plan(user, deal, line='dental', role='alternate', carrier='Delta', name=f'Quote {n}')
    first = next(entry for entry in read(api, deal, 'dental')['plans'] if entry['plan_id'] == quotes[0].id)
    assert first['remove']['star'] == []
    assert first['remove']['why'].startswith('Nothing on Dental is starred, so every quote prints.')
    assert 'star the plans to show instead' in first['remove']['why']
    assert current.id not in first['remove']['star']


def test_F37_J2_a_line_the_intent_leaves_off_shows_no_pages(api, user, deal):
    services.create_plan(user, deal, line='vision', role='current', carrier='VSP', name='Choice')
    intake.set_intent(user, deal.id, lines=['medical', 'dental', 'vision'], has_today=True)
    intake.set_intent(user, deal.id, line='vision', this_year='off')
    body = read(api, deal, 'vision')
    assert body['pages'] == [] and body['off']


def test_F37_bad_line_or_preset_answers_400(api, deal):
    assert api.get(f'/api/deals/{deal.id}/proposal/pages/', {'line': 'nope'}).status_code == 400
    assert api.get(f'/api/deals/{deal.id}/proposal/pages/').status_code == 400
    bad = api.get(f'/api/deals/{deal.id}/proposal/pages/', {'line': 'medical', 'preset': 'nope'})
    assert bad.status_code == 400 and 'preset' in bad.json()
    assert api.get('/api/deals/999999/proposal/pages/', {'line': 'medical'}).status_code == 404
