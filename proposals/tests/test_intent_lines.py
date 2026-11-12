"""The proposal's lines follow the coverage intent, not the shopping list (plan.md §5.2, §5.4; J2, J52, B24): a line
kept as-is is presented and never blocks Issue; a line left off presents nothing."""

import pytest

from intake import services as intake
from quotes import services as plans

pytestmark = pytest.mark.django_db


def _lines(api, deal):
    return {line['line']: line for line in api.get(f'/api/deals/{deal.id}/proposal/').json()['lines']}


def test_J2_J52_kept_lines_stay_on_the_proposal_and_left_off_lines_leave_it(api, user, deal):
    for line in ('medical', 'dental', 'vision'):
        plans.create_plan(user, deal, line=line, role='current', carrier='Carrier', name=f'{line} plan')
    intake.set_intent(user, deal.id, lines=['medical', 'dental', 'vision'], has_today=True)
    intake.set_intent(user, deal.id, line='dental', this_year='keep')
    intake.set_intent(user, deal.id, line='vision', this_year='off')
    body = api.get(f'/api/deals/{deal.id}/proposal/').json()
    assert [line['line'] for line in body['lines']] == ['medical', 'dental']
    blocked = ' '.join(body['issue_blockers'])
    assert 'Medical' in blocked and 'Dental' not in blocked  # a kept line needs no pick
