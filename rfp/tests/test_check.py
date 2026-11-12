"""The export check, its pills and its stamp (plan.md §7.11, §8.12; K52, K69–K76, K121, K122, K123)."""

import pytest

from census import services as census_services
from rfp import services, summary
from rfp.check import report
from rfp.check.stamp import stamp

from .request import ask, ctx, get
from .roster import family

pytestmark = pytest.mark.django_db


def check(api, deal, key):
    return api.get(f'/api/deals/{deal.id}/rfp/check/', {'file': key})


def test_K69_K70_a_stable_digest_and_a_stale_ack_answers_409_with_the_fresh_report(api, user, deal):
    members = family(user, deal)
    first = check(api, deal, 'census-uhc').json()
    assert first == check(api, deal, 'census-uhc').json()
    census_services.edit_values(user, members[0].id, {'gender': ''})  # UHC requires *Gender: a new problem
    response = get(api, deal, 'census-uhc', ack=first['ack'])
    assert response.status_code == 409
    fresh = response.json()['report']
    assert fresh['ack'] != first['ack'] and response.json()['detail'].startswith('Something changed')
    assert get(api, deal, 'census-uhc', ack=fresh['ack']).status_code == 200


def test_K74_census_problems_name_people_on_our_screen_only_and_send_to_the_lens(api, user, deal):
    members = family(user, deal)
    values = {'first_name': 'Zelda', 'last_name': 'Synthetic', 'relationship': 'Cousin', 'dob': '2010-01-01'}
    census_services.add_member(user, deal.id, 'dependent', employee_id=members[0].id, values=values)
    found = check(api, deal, 'census-uhc').json()
    assert found['label'] == 'UnitedHealthcare census'
    named = [problem for problem in found['problems'] if 'Zelda Synthetic' in problem.get('people', [])]
    assert named and all('Zelda' not in problem['text'] for problem in found['problems'])
    assert named[0]['fix'] == {'tab': 'census', 'lens': 'census-uhc'}


def test_K122_a_deal_with_no_owner_says_what_prints_instead(api, user, deal):
    deal.owner = None
    deal.save(update_fields=['owner'])
    found = check(api, deal, 'cover').json()
    assert [problem['code'] for problem in found['problems']] == ['no_owner']
    assert 'No owner on this deal' in found['problems'][0]['text']


def test_K72_an_unknown_key_is_400(api, deal):
    assert check(api, deal, 'census-cigna').status_code == 400
    assert check(api, deal, 'draft-nobody').status_code == 400


def test_K52_every_row_gets_a_pill(api, user, deal):
    family(user, deal)
    data = api.get(f'/api/deals/{deal.id}/rfp/checks/').json()
    rows = api.get(f'/api/deals/{deal.id}/rfp/').json()['packet']['rows']
    keys = {row['key'] for row in rows if row['available']}
    assert set(data['cards']) == keys and data['checks_stamp']
    assert {pill['status'] for pill in data['cards'].values()} <= {'ready', 'problems', 'unsigned'}


def test_K121_a_draft_past_20_mb_is_a_problem():
    assert report._size({'size': 16_000_000})[0]['code'] == 'too_large'
    assert report._size({'size': 10_000_000}) == []


def test_K52_the_stamp_moves_with_the_census_never_with_marks_sends_or_notes(user, deal):
    ask(user, deal, 'aetna', route='direct')
    before = stamp(ctx(deal))
    services.set_done(user, deal.id, 'packet', True)
    services.update(user, deal.id, {'notes': 'A note for the carriers.', 'due_date': '2026-12-01'})
    services.mark_sent(user, deal.id, 'aetna', True)
    assert stamp(ctx(deal)) == before
    family(user, deal)
    assert stamp(ctx(deal)) != before


def test_K123_summary_facts_count_sends_and_who_is_still_awaited(user, deal):
    ask(user, deal, 'aetna', 'cigna', route='direct')
    services.mark_sent(user, deal.id, 'aetna', True)
    services.set_done(user, deal.id, 'request', True)
    found = summary.facts([deal.id])[deal.id]
    assert (found['route'], found['drafts_sent'], found['drafts_total'], found['cards_done']) == ('direct', 1, 2, 1)
    assert found['first_sent_on'] == found['last_sent_on'] and found['awaiting'] == ['Aetna']
