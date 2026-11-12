"""The review queue, "Approve N ready" and the section counts (plan.md §7.13, §8.8; L9, L11, L14, L16, L20, L43, B38,
C32, C34; old 891f1b3 `items.py`, `ReviewSectionBar.jsx`): answers ready when their link was submitted after its last
save or sat a day; still typing until then; the queue groups by column or section and change; the button takes the
submitted answers, an idle link's only with the tick, never one that blanks a value."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from census.models import Member
from intake.models import Intake
from intake.services import update_answers

from .decision_world import (
    added,
    cell_entry,
    census_answers,
    employee,
    entry,
    idle,
    intake_answers,
    link_on,
    submitted,
    typing,
)

pytestmark = pytest.mark.django_db


def _queue(api, deal, **query):
    answer = api.get(f'/api/deals/{deal.id}/review/queue/', query)
    assert answer.status_code == 200, answer.content
    assert answer['Cache-Control'] == 'private, no-store'
    return answer.json()


def test_L43_approve_ready_takes_the_submitted_answers_and_an_idle_links_only_with_the_tick(api, user, deal):
    sent, left, busy = (link_on(user, deal, name=name) for name in ('Dana', 'Lee', 'Kim'))
    intake_answers(deal, sent, {'dba': 'Dana Co'})
    intake_answers(deal, left, {'website': 'https://example.com'})
    intake_answers(deal, busy, {'sic_code': '1234'})
    submitted(sent)
    idle(left)
    typing(busy)
    url = f'/api/deals/{deal.id}/review/approve/'
    first = api.post(url, {'surface': 'intake', 'ready_only': True}, format='json').json()
    assert first['approved'] == ['intake:dba']
    second = api.post(url, {'surface': 'intake', 'ready_only': True, 'include_idle': True}, format='json').json()
    assert second['approved'] == ['intake:website']
    assert entry(deal, 'sic_code')['status'] == 'pending'  # still typing: never taken
    assert api.post(url, {'surface': 'intake', 'ready_only': 'yes'}, format='json').status_code == 400


def test_L43_approve_ready_never_takes_an_answer_that_blanks_a_value(api, user, deal):
    update_answers(user, deal.id, {'dba': 'Our Name', 'website': 'https://ours.example.com'})
    link = link_on(user, deal)
    intake_answers(deal, link, {'dba': '', 'website': 'https://theirs.example.com'})
    submitted(link)
    body = api.post(f'/api/deals/{deal.id}/review/approve/', {'surface': 'intake'}, format='json').json()
    assert body['approved'] == ['intake:website']
    assert entry(deal, 'dba')['status'] == 'pending'
    single = api.post(f'/api/deals/{deal.id}/review/approve/', {'refs': ['intake:dba']}, format='json').json()
    assert single['approved'] == ['intake:dba'] and 'dba' not in Intake.objects.get(deal=deal).answers


def test_L16_the_census_queue_groups_by_column_and_change_and_splits_the_phases(api, user, deal):
    one, two = employee(user, deal, 'Avery', 'One', zip='33602'), employee(user, deal, 'Blake', 'Two')
    link, other = link_on(user, deal, name='Dana'), link_on(user, deal, name='Lee')
    census_answers(deal, link, {(one.id, 'zip'): '33606', (two.id, 'zip'): '33611'})
    census_answers(deal, other, {(one.id, 'job_title'): 'Driver'})
    (new,) = added(deal, link, ('Rowan', 'Synthetic'))
    submitted(link)
    typing(other)
    found = _queue(api, deal, surface='census')
    assert found['phases'] == {'to_review': 3, 'in_progress': 1}
    groups = {group['key']: (group['label'], group['count']) for group in found['groups']}
    assert groups == {'zip:changed': ('ZIP', 1), 'zip:filled': ('ZIP', 1), '*:added': ('New people', 1)}
    by_ref = {item['ref']: item for item in found['items']}
    changed = by_ref[f'census:{one.id}:zip']
    assert (changed['ours'], changed['theirs'], changed['person'], changed['via']) == (
        '33602',
        '33606',
        'Avery One',
        'Dana',
    )
    assert (changed['change'], changed['phase'], changed['ready_why']) == ('changed', 'to_review', 'submitted')
    person = by_ref[f'census:{new.id}:*']
    assert person['kind'] == 'person' and {'label': 'First Name', 'value': 'Rowan'} in person['details']
    narrowed = _queue(api, deal, surface='census', group='zip:filled')
    assert [item['ref'] for item in narrowed['items']] == narrowed['ids'] == [f'census:{two.id}:zip']
    typing_now = _queue(api, deal, surface='census', phase='in_progress')
    assert [item['ref'] for item in typing_now['items']] == [f'census:{one.id}:job_title'] and not typing_now['ids']
    assert typing_now['in_progress'][0]['name'] == 'Lee' and typing_now['in_progress'][0]['ready_at']
    for bad in ({'surface': 'payroll'}, {'phase': 'later'}, {'page': 'x'}):
        assert api.get(f'/api/deals/{deal.id}/review/queue/', bad).status_code == 400


def test_B38_the_intake_queue_lists_answers_by_section_required_first_then_the_blocks(api, user, deal):
    link = link_on(user, deal)
    intake_answers(deal, link, {'dba': 'Their Name', 'legal_name': 'Their Legal LLC', 'block:lines': ['dental']})
    submitted(link)
    items = _queue(api, deal, surface='intake')['items']
    assert [item['ref'] for item in items] == ['intake:legal_name', 'intake:dba', 'intake:block:lines']
    assert items[0]['required'] and items[0]['section'] == 'Employer information'
    assert (items[2]['kind'], items[2]['theirs'], items[2]['editable']) == ('block', ['Dental'], False)


def test_L14_L9_the_board_carries_each_sections_counts_and_the_to_review_lane(api, user, deal):
    member = employee(user, deal, zip='33602')
    link, other = link_on(user, deal, name='Dana'), link_on(user, deal, name='Lee')
    intake_answers(deal, link, {'dba': 'Their Name'})
    census_answers(deal, link, {(member.id, 'zip'): '33606'})
    census_answers(deal, other, {(member.id, 'job_title'): 'Driver'})
    submitted(link)
    typing(other)
    board = api.get(f'/api/deals/{deal.id}/review/board/').json()
    census = board['sections']['census']
    assert (census['to_review'], census['in_progress'], census['ready_submitted']) == (1, 1, 1)
    assert census['names'] == ['Dana', 'Lee']
    assert board['sections']['intake']['to_review'] == 1 and board['sections']['intake']['missing'] > 0
    lane = {row['key']: row for row in board['lanes']['to_review']}
    assert lane['census']['label'] == '1 answer from the client'
    assert lane['intake']['fix'] == {'tab': 'review', 'view': 'queue', 'section': 'intake'}


def test_Q3_4_the_queue_reads_in_a_fixed_number_of_queries(api, user, deal):
    link = link_on(user, deal)
    small = employee(user, deal, 'Avery', 'One')
    census_answers(deal, link, {(small.id, 'zip'): '33606'})

    def count():
        with CaptureQueriesContext(connection) as captured:
            _queue(api, deal, surface='census')
        return len(captured.captured_queries)

    before = count()
    people = [employee(user, deal, f'P{n}', 'Synthetic') for n in range(4)]
    census_answers(deal, link, {(person.id, 'zip'): '33606' for person in people})
    assert count() == before


def test_L90_approving_a_ready_census_takes_the_added_people_with_the_answers(api, user, deal):
    member = employee(user, deal, zip='33602')
    link = link_on(user, deal)
    census_answers(deal, link, {(member.id, 'zip'): '33606'})
    (new,) = added(deal, link, ('Rowan', 'Synthetic'))
    submitted(link)
    body = api.post(f'/api/deals/{deal.id}/review/approve/', {'surface': 'census'}, format='json').json()
    assert set(body['approved']) == {f'census:{member.id}:zip', f'census:{new.id}:*'}
    assert cell_entry(member, 'zip')['status'] == 'approved'
    assert Member.objects.filter(pk=new.pk).exists()
