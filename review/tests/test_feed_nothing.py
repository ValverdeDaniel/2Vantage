"""Q.9 row 55 on GD6 (plan.md §5.8, §13.10 row 55; OQ85; L120): pending entries feed nothing — not the answers that
print, the intake's readiness, the census's counts and rollup, nor a carrier's census file — until a person approves
them; then the approved answer is stored with origin `client`. The export check says what waits, in counts, with
the words "not in the file until approved", and its stamp moves when a link is submitted."""

import pytest

from census import facts as census_facts
from census.models import Member
from intake import summary as intake_summary
from intake.models import Intake
from intake.selectors import answers_of

from .decision_world import census_answers, employee, intake_answers, link_on, submitted, typing

pytestmark = pytest.mark.django_db


def _stored(deal):
    deal.refresh_from_db()
    intake = Intake.objects.get(deal=deal)
    facts = census_facts.stored(deal.id)
    found = intake_summary.facts([deal.id])[deal.id]
    counts = (facts['rollup'], facts['missing'], facts['employees'])
    return answers_of(deal, intake), (found['answered'], found['ready_state']), counts


def _angle_csv(api, deal):
    response = api.get(f'/api/deals/{deal.id}/rfp/files/census-angle-csv/')
    assert response.status_code == 200, response.content
    return b''.join(response.streaming_content).decode('utf-8-sig')


def test_Q9_55_GD6_pending_entries_feed_nothing_until_approved_with_origin_client(api, user, get_to_market):
    deal = get_to_market.step('census_arrives').built.deal
    member = Member.objects.filter(deal=deal, kind='employee').order_by('position').first()
    link = link_on(user, deal)
    before = _stored(deal)
    intake_answers(deal, link, {'payroll_vendor': 'Other Payroll Inc.', 'website': ''})
    census_answers(deal, link, {(member.id, 'zip'): '33699'})
    submitted(link)
    assert _stored(deal) == before  # OQ85: nothing reads a pending answer
    assert '33699' not in _angle_csv(api, deal)  # a carrier's census file prints approved values only
    answer = api.post(f'/api/deals/{deal.id}/review/approve/', {'refs': ['intake:payroll_vendor']}, format='json')
    assert answer.json()['approved'] == ['intake:payroll_vendor']
    intake = Intake.objects.get(deal=deal)
    assert intake.answers['payroll_vendor'] == 'Other Payroll Inc.'
    assert (intake.sources['payroll_vendor']['origin'], intake.sources['payroll_vendor']['link']) == ('client', link.id)
    api.post(f'/api/deals/{deal.id}/review/approve/', {'refs': [f'census:{member.id}:zip']}, format='json')
    assert Member.objects.get(pk=member.pk).sources['zip']['origin'] == 'client'
    assert '33699' in _angle_csv(api, deal)


def test_L120_the_export_check_counts_the_clients_census_answers_and_its_stamp_moves(api, user, deal):
    people = [employee(user, deal, f'P{n}', 'Synthetic', zip='33602') for n in range(3)]
    link, other = link_on(user, deal, name='Dana'), link_on(user, deal, name='Lee')
    census_answers(deal, link, {(people[0].id, 'zip'): '33606', (people[1].id, 'zip'): '33607'})
    census_answers(deal, other, {(people[2].id, 'zip'): '33608'})
    typing(link)
    typing(other)
    stamp = api.get(f'/api/deals/{deal.id}/rfp/checks/').json()['checks_stamp']
    found = {
        p['code']: p for p in api.get(f'/api/deals/{deal.id}/rfp/check/', {'file': 'census-uhc'}).json()['problems']
    }
    assert found['client_typing']['count'] == 3 and 'client_waiting' not in found
    assert found['client_typing']['text'].endswith('not in the file until approved.')
    assert found['client_typing']['fix'] == {'tab': 'review', 'view': 'queue'}
    submitted(link)
    found = {
        p['code']: p for p in api.get(f'/api/deals/{deal.id}/rfp/check/', {'file': 'census-uhc'}).json()['problems']
    }
    assert (found['client_waiting']['count'], found['client_typing']['count']) == (2, 1)
    assert '33606' not in str(found) and 'Synthetic' not in found['client_waiting']['text']
    assert api.get(f'/api/deals/{deal.id}/rfp/checks/').json()['checks_stamp'] != stamp
    deal_lines = {p['code'] for p in api.get(f'/api/deals/{deal.id}/rfp/checks/').json()['deal']}
    assert {'client_waiting', 'client_typing'} <= deal_lines
