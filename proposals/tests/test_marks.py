"""The builder's completed marks (plan.md §8.14; J18, J19; J.6.4, J.6.10): `POST deals/{id}/proposal/marks/`, the
counts, and quotes' `plans_changed` taking the line's Plans card mark off."""

import pytest

from deals import activity
from deals.models import Activity
from proposals.models import ProposalConfig
from quotes import services as plans

pytestmark = pytest.mark.django_db


@pytest.fixture
def line(user, deal):
    current = plans.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='PPO')
    quote = plans.create_plan(
        user, deal, line='medical', role='alternate', carrier='Cigna', name='HDHP', replaces_ids=[current.id]
    )
    return current, quote


def _mark(api, deal, **body):
    return api.post(f'/api/deals/{deal.id}/proposal/marks/', body, format='json')


def test_J18_a_mark_is_stamped_counted_and_logged_and_undo_takes_it_off(api, user, deal, line):
    response = _mark(api, deal, card='quotes', line='medical', done=True)
    assert response.status_code == 200 and response.json()['stamp']['at']
    body = api.get(f'/api/deals/{deal.id}/proposal/').json()
    assert body['marks']['done'] == 1 and body['marks']['total'] == 2
    assert body['marks']['stored']['lines']['medical']['quotes']['by']
    row = Activity.objects.get(pk=response.json()['activity_id'])
    assert row.action == 'marked' and row.summary == 'Marked Plans on the proposal (Medical) completed'
    assert _mark(api, deal, card='quotes', line='medical', done=True).json()['activity_id'] is None  # unchanged
    off = _mark(api, deal, card='quotes', line='medical', done=False).json()
    assert off['stamp'] is None
    assert api.get(f'/api/deals/{deal.id}/proposal/').json()['marks']['done'] == 0
    activity.revert(off['activity_id'], user)
    assert ProposalConfig.objects.get(deal=deal).marks['lines']['medical']['quotes']


def test_J18_marks_never_reach_the_config(api, deal, line):
    _mark(api, deal, card='rows', line='medical', done=True)
    assert api.get(f'/api/deals/{deal.id}/proposal/').json()['config'] == {}


@pytest.mark.parametrize(
    'body',
    [
        {'card': 'colours', 'done': True},
        {'card': 'quotes', 'line': 'dental', 'done': True},  # no dental plans: not on the proposal
        {'card': 'quotes', 'line': 'medical', 'done': 'yes'},
    ],
)
def test_J18_a_bad_mark_answers_400(api, deal, line, body):
    assert _mark(api, deal, **body).status_code == 400


def test_J19_a_star_takes_the_lines_plans_mark_off_and_leaves_the_others(
    api, user, deal, line, django_capture_on_commit_callbacks
):
    _current, quote = line
    for card in ('quotes', 'rows'):
        _mark(api, deal, card=card, line='medical', done=True)
    with django_capture_on_commit_callbacks(execute=True):
        plans.star(user, deal, [quote.id], True)
    stored = ProposalConfig.objects.get(deal=deal).marks
    assert 'quotes' not in stored['lines']['medical'] and stored['lines']['medical']['rows']
