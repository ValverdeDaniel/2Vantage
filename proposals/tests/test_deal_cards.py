"""The builder's deal cards on the golden deal and through the API (plan.md §13.8 row 26, "done when": every card saves
and marks itself done; Markets checked lists the quoting carriers, with "no RFP sent"; J38–J46, J63–J67)."""

from datetime import date

import pytest

from conftest import make_deal
from deals.models import Activity
from intake import services as intake
from proposals import config
from quotes import services as plans

pytestmark = pytest.mark.django_db

# One write per card, as the builder sends it: (card, path, value).
WRITES = [
    ('output', 'output.layout', 'side_by_side'),
    ('output', 'output.compare_slots', 5),
    ('pages', 'output.pages.team', False),
    ('pages', 'experience.rows', [{'period': 'Jan–Dec 2025', 'premium': '410,000', 'claims': '298,000'}]),
    ('summary', 'summary.blocks', [{'key': 'recommended'}, {'key': 'enrollment', 'line': 'dental'}]),
    ('next_steps', 'next_steps', [{'date': '2026-12-01', 'text': 'Decide on the medical plan'}]),
    ('markets', 'markets.lines.medical.notes.cigna', 'Competitive'),
]


def _builder(api, deal):
    response = api.get(f'/api/deals/{deal.id}/proposal/')
    assert response.status_code == 200, response.content
    return response.json()


def _mark(api, deal, card, done=True):
    line = 'medical' if card == 'markets' else ''
    response = api.post(
        f'/api/deals/{deal.id}/proposal/marks/', {'card': card, 'line': line, 'done': done}, format='json'
    )
    assert response.status_code == 200, response.content
    return response.json()


def _stamp(body, card):
    stored = body['marks']['stored']
    return (stored.get('lines', {}).get('medical', {}) if card == 'markets' else stored).get(card)


@pytest.mark.parametrize(('card', 'path', 'value'), WRITES)
def test_S26_J18_J19_GD1_every_card_saves_and_marks_itself_done(api, gd1, card, path, value):
    deal = gd1.deal
    _mark(api, deal, card)
    response = api.patch(f'/api/deals/{deal.id}/proposal/', {path: value}, format='json')
    assert response.status_code == 200, response.content
    mark = f'marks.lines.medical.{card}' if card == 'markets' else f'marks.{card}'
    assert response.json()['cleared'] == [mark]  # the edit took its own card's mark off (J19)
    body = _builder(api, deal)
    assert config.get(body['config'], path) == config.clean(path, value)[1] and _stamp(body, card) is None
    _mark(api, deal, card)
    assert _stamp(_builder(api, deal), card)['by']


def test_J63_GD1_markets_checked_lists_the_quoting_carriers_with_no_rfp_sent(api, gd1):
    markets = _builder(api, gd1.deal)['markets']
    assert markets['has_asks'] is False and markets['on'] is False and markets['override'] is None
    medical = next(line for line in markets['lines'] if line['key'] == 'medical')
    assert [(row['carrier'], row['quoted']) for row in medical['rows']] == [
        ('Aetna', None),
        ('Cigna', True),
        ('UnitedHealthcare', True),
    ]
    assert all(not row['asked'] for row in medical['rows'])
    api.patch(f'/api/deals/{gd1.deal.id}/proposal/', {'markets.on': True}, format='json')
    assert _builder(api, gd1.deal)['markets']['on'] is True


def test_J64_GD1_the_summary_previews_the_standard_set_until_a_pick_and_says_why_a_figure_is_missing(api, gd1):
    summary = _builder(api, gd1.deal)['summary']
    assert summary['on'] is True and summary['picked'] == []
    assert [spec['key'] for spec in summary['standard']][:2] == ['total_current', 'lines_shopped']
    dental = next(b for b in summary['blocks'] if b['line'] == 'dental' and b['key'] == 'recommended')
    assert dental['available'] and dental['value_label'].endswith('/mo')
    medical = next(b for b in summary['blocks'] if b['line'] == 'medical' and b['key'] == 'recommended')
    assert not medical['available'] and 'one current plan' in medical['reason']  # two picks for current plan A
    api.patch(
        f'/api/deals/{gd1.deal.id}/proposal/', {'summary.blocks': [{'key': 'spread', 'line': 'medical'}]}, format='json'
    )
    picked = _builder(api, gd1.deal)['summary']
    assert [(b['key'], b['line']) for b in picked['blocks']] == [('spread', 'medical')]


def test_J42_J45_J67_GD1_the_ledger_and_checks_follow_what_is_typed(api, gd1):
    body = _builder(api, gd1.deal)
    ledger = {row['key']: row for row in body['ledger']}
    assert ledger['experience']['ready'] is False and ledger['experience']['fix'] == {'card': 'pages'}
    assert 'no_next_steps' in {item['code'] for item in body['checks']}
    changes = {'experience.summary': 'Claims ran at 74% of premium.', 'next_steps': [{'text': 'Sign by 12/1'}]}
    api.patch(f'/api/deals/{gd1.deal.id}/proposal/', changes, format='json')
    body = _builder(api, gd1.deal)
    ledger = {row['key']: row for row in body['ledger']}
    assert ledger['experience']['ready'] and ledger['next_steps']['ready']
    assert 'no_next_steps' not in {item['code'] for item in body['checks']}


def test_J46_an_intent_edit_takes_the_coverage_cards_mark_off_and_revert_of_a_setting_works(api, user, deal):
    plans.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='PPO')
    _mark(api, deal, 'coverage')
    assert _stamp(_builder(api, deal), 'coverage')
    intake.set_intent(user, deal.id, line='dental', remove=True)
    assert _stamp(_builder(api, deal), 'coverage') is None
    written = api.patch(f'/api/deals/{deal.id}/proposal/', {'output.disclaimers': False}, format='json').json()
    reverted = api.post(f'/api/activity/{written["activity_id"]}/revert/')
    assert reverted.status_code == 200, reverted.content
    assert config.get(_builder(api, deal)['config'], 'output.disclaimers') is True
    assert Activity.objects.filter(pk=written['activity_id']).exists()


def test_J66_members_65_or_older_the_summary_leaves_out_are_flagged_until_ticked(api, user):
    from census.tests.helpers import family, imported, roster, xlsx

    deal = make_deal(user, effective_date=date(2027, 1, 1))
    plans.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='PPO')
    rows = roster(
        family('1', 'Rivera', dob='03/02/1958'),
        family('2', 'Okafor', dob='07/09/1990', deps=[('Spouse', 'Lee', '05/05/1960')]),
    )
    imported(user, deal, xlsx(rows))
    body = _builder(api, deal)
    assert body['summary']['medicare'] == 2
    assert 'medicare_eligible' in [spec['key'] for spec in body['summary']['standard']]
    api.patch(f'/api/deals/{deal.id}/proposal/', {'summary.blocks': [{'key': 'current_cost'}]}, format='json')
    body = _builder(api, deal)
    assert 'medicare_not_shown' in {item['code'] for item in body['checks']}
    api.patch(f'/api/deals/{deal.id}/proposal/', {'summary.blocks': [{'key': 'medicare_eligible'}]}, format='json')
    body = _builder(api, deal)
    found = body['summary']['blocks'][0]
    assert found['value_label'] == '2 members 65+' and 'Rivera' not in str(body)  # counts only, never a name
    assert 'medicare_not_shown' not in {item['code'] for item in body['checks']}
