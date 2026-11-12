"""The builder on the golden deals (plan.md §13.8 row 25, "done when"; Q.9 row 25; J47–J62, J159; Q.3 #5). `gd1` is
built once for the module; the tests that write go through the services and roll back with each test's transaction."""

import pytest

from intake import services as intake
from proposals import line_layout
from quotes import services as plans

pytestmark = pytest.mark.django_db


def builder(api, deal):
    response = api.get(f'/api/deals/{deal.id}/proposal/')
    assert response.status_code == 200, response.content
    return response.json()


def line_of(body, key):
    return next(line for line in body['lines'] if line['line'] == key)


def pages(api, deal, line='medical'):
    return api.get(f'/api/deals/{deal.id}/proposal/pages/', {'line': line, 'preset': 'key'}).json()


def test_J52_J55_GD1_two_picks_for_one_current_plan_each_show_their_own_change(api, gd1):
    medical = line_of(builder(api, gd1.deal), 'medical')
    picks = {pick['plan_id']: pick for pick in medical['recommendation']['plans']}
    cg1, cg1n = picks[gd1.refs['CG1']], picks[gd1.refs['CG1N']]
    assert cg1['replacing'] == cg1n['replacing'] == ['Current 1']  # both answer for the HDHP 3300
    assert cg1['change'] and cg1n['change'] and cg1['change']['text'] != cg1n['change']['text']
    assert picks[gd1.refs['C2']]['kind'] == 'renewal' and picks[gd1.refs['C2']]['replacing'] == ['Current 3']
    groups = {group['number']: group for group in medical['recommendation']['groups']}
    assert groups[1]['plan_ids'] == [gd1.refs['CG1'], gd1.refs['CG1N']] and all(g['answered'] for g in groups.values())
    assert medical['recommendation']['covered'] and medical['reasons']


def test_J52_B36_GD1_a_kept_line_needs_no_pick(api, user, gd1):
    deal, refs = gd1.deal, gd1.refs
    plans.set_recommended(user, refs['VS2'], False)
    body = builder(api, deal)
    assert body['ready']['missing'] == ['Vision']
    intake.set_intent(user, deal.id, line='vision', has_today=True, this_year='keep')
    body = builder(api, deal)
    vision = line_of(body, 'vision')
    assert vision['state'] == 'presented' and vision['recommendation']['needs_pick'] is False
    assert body['ready']['ok'] is True and body['ready']['sentence'] is None
    assert not any(item['code'] == 'no_recommendation' for item in body['checks'])


def test_J159_GD1_predicted_option_numbers_match_pages_and_issue_stamps_them(api, gd1):
    deal = gd1.deal
    body = builder(api, deal)
    predicted = {}
    for key in ('medical', 'dental', 'vision'):
        shown = {plan['plan_id']: plan['option'] for plan in pages(api, deal, key)['plans']}
        for pick in line_of(body, key)['recommendation']['plans']:
            assert pick['option'] == shown[pick['plan_id']]
        predicted.update({pid: n for pid, n in shown.items() if n})
    stamped = plans.stamp_option_numbers(deal, line_layout.reading_ids(deal))
    assert stamped == predicted
    after = pages(api, deal)['plans']
    assert all(plan['predicted'] is False for plan in after if plan['option'])
    assert {plan['plan_id']: plan['option'] for plan in after if plan['option']} == {
        pid: n for pid, n in predicted.items() if pid in {plan['plan_id'] for plan in after}
    }


def test_J159_GD1_stamped_numbers_hold_across_stars_and_order(api, user, gd1):
    deal, refs = gd1.deal, gd1.refs
    plans.stamp_option_numbers(deal, line_layout.reading_ids(deal))
    before = {plan['plan_id']: plan['option'] for plan in pages(api, deal)['plans'] if plan['option']}
    plans.star(user, deal, [refs['CG2']], True)
    plans.arrange(user, deal, 'medical', ('reset',))
    after = {plan['plan_id']: plan for plan in pages(api, deal)['plans'] if plan['option']}
    assert {pid: after[pid]['option'] for pid in before} == before
    assert after[refs['CG2']]['option'] == max(before.values()) + 1 and after[refs['CG2']]['predicted'] is True


def test_J16_key_rows_show_the_field_sets_few_rows_with_the_rx_tiers_as_one(api, gd1):
    rows = pages(api, gd1.deal)['rows']
    keys = [row['key'] for row in rows]
    assert keys[:3] == ['deductible_single', 'coinsurance', 'oop_max_single']
    assert 'sl_lasers' not in keys and all(row['section'] == '' for row in rows)


def test_J31_J59_J61_GD1_lines_follow_the_producers_order_and_carry_their_section(api, user, gd1):
    deal = gd1.deal
    from proposals import services

    services.set_config(user, deal, {'order': ['vision', 'medical']})
    body = builder(api, deal)
    assert [line['line'] for line in body['lines']] == ['vision', 'medical', 'dental']
    medical = line_of(body, 'medical')
    assert medical['card_stats_standard'] is True and medical['card_stats'][0] == {
        'key': 'deductible_single',
        'label': 'Deductible',
    }
    assert medical['spec'] == {
        'parts': {'comparison': True, 'cost': True, 'recommendation': True},
        'rows': None,
        'card_stats': None,
        'table_note': '',
    }
    assert {row['key'] for row in medical['rows']} >= {'deductible_single', 'pcp_copay'}
    assert 'sl_lasers' not in {row['key'] for line in body['lines'] for row in line['rows']}
    assert medical['pages'] == 3 and medical['quotes'] > 0 and body['marks']['total'] == 6


def test_Q3_5_J48_GD3_the_enrollment_strip_reads_typed_counts_then_the_census(api, quote_first):
    deal = quote_first.built.deal
    strip = line_of(builder(api, deal), 'medical')['enrollment']
    assert strip['source'] == 'line' and strip['words'] == 'Typed for the whole line'
    assert strip['typed'] == strip['figures'] == {'EE': 30, 'ES': 8, 'EC': 6, 'FAM': 8} and strip['editable']
    quote_first.census()
    strip = line_of(builder(api, deal), 'medical')['enrollment']
    assert strip['source'] == 'census' and strip['figures'] != strip['typed']
