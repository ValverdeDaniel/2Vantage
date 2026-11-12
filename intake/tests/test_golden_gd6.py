"""GD6, Get to Market (plan.md §12.6, §13.4; Q.9 row 39): its full intake, typed through the one writer, reads back as
its hand-worked key says — every shown question answered on the four cards, the right ones hidden, nothing to warn."""

import pytest

from intake import form

pytestmark = pytest.mark.django_db


def test_B1_gd6_fills_every_shown_question_on_the_four_cards(api, gd6, golden_keys):
    key = golden_keys['GD6']['intake']
    body = api.get(f'/api/deals/{gd6.deal.id}/intake/').json()
    answers = body['answers']
    assert body['hidden'] == key['hidden']
    assert body['needed'] == key['needed']
    assert body['readiness'] == key['readiness']
    assert body['issues'] == key['issues']
    assert body['notes']['multi_state'] is key['multi_state']
    shown = [question['key'] for question in form.QUESTIONS if question['key'] not in body['hidden']]
    assert len(shown) == key['answered'] and all(answers.get(k) not in (None, '', []) for k in shown)
    assert {k: answers[k] for k in key['stored']} == key['stored']
    assert all(body['sources'][k]['origin'] == 'typed' for k in shown if k != form.EFFECTIVE_DATE)
    assert body['status'] == {}  # nothing missing, nothing to check


def test_B1_gd6_effective_date_is_the_deals(api, gd6, golden_keys):
    header = api.get(f'/api/deals/{gd6.deal.id}/').json()
    assert header['effective_date'] == golden_keys['GD6']['intake']['stored'][form.EFFECTIVE_DATE]


def test_F139_gd6_budget_answers_are_numbers_the_advisor_can_apply(api, gd6, golden_keys):
    hints = golden_keys['GD6']['intake']['budget_hints']
    answers = api.get(f'/api/deals/{gd6.deal.id}/intake/').json()['answers']
    assert float(answers['budget_target']) == hints['target_monthly']
    assert float(answers['acceptable_increase_pct']) == hints['accepts_up_to_pct']
