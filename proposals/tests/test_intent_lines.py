"""The builder's lines follow the coverage intent, not the shopping list (plan.md §5.2, §5.4; J2, J30, J47, J52, B24,
B36): a line kept as-is is presented and never blocks Issue; a line left off stays in the builder with its notice and
prints nowhere."""

import pytest

from intake import services as intake
from quotes import services as plans

pytestmark = pytest.mark.django_db


def _body(api, deal):
    return api.get(f'/api/deals/{deal.id}/proposal/').json()


def test_J2_J30_J52_kept_lines_need_no_pick_and_left_off_lines_print_nowhere(api, user, deal):
    for line in ('medical', 'dental', 'vision'):
        current = plans.create_plan(user, deal, line=line, role='current', carrier='Carrier', name=f'{line} plan')
        plans.create_plan(
            user, deal, line=line, role='alternate', carrier='Other', name='Quote', replaces_ids=[current.id]
        )
    intake.set_intent(user, deal.id, lines=['medical', 'dental', 'vision'], has_today=True)
    intake.set_intent(user, deal.id, line='dental', this_year='keep')
    intake.set_intent(user, deal.id, line='vision', this_year='off')
    body = _body(api, deal)
    lines = {line['line']: line for line in body['lines']}
    assert list(lines) == ['medical', 'dental', 'vision']
    assert lines['dental']['state'] == 'presented' and lines['dental']['chip']['text'] == 'guaranteed'
    assert lines['dental']['recommendation']['needs_pick'] is False
    assert lines['vision']['off']['reason'] == 'left_off' and lines['vision']['presented_ids'] == []
    assert body['ready']['missing'] == ['Medical'] and 'Medical' in body['ready']['sentence']
    codes = {(item['code'], item['line']) for item in body['checks']}
    assert ('no_recommendation', 'medical') in codes and ('line_off', 'vision') in codes
    assert not any(code == 'no_recommendation' and line in ('dental', 'vision') for code, line in codes)


def test_J47_a_kept_line_with_no_plans_shows_its_incumbent(api, user, deal):
    intake.set_intent(user, deal.id, line='dental', has_today=True, this_year='keep')
    body = _body(api, deal)
    dental = next(line for line in body['lines'] if line['line'] == 'dental')
    assert dental['state'] == 'presented' and dental['incumbent'] is not None
    assert dental['recommendation']['needs_pick'] is False
