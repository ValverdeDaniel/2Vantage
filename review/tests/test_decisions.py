"""Approving and rejecting what the client sent (plan.md §5.8, §13.10 row 55 "An approved answer is stored with origin
`client`"; L.6 the owner contract; L17, L43, L90, B38, C28, C32; OQ84, OQ85; Q.9 row 55): an approval moves the
answer into the values through the owner with origin `client`, the approver and the link; Keep ours changes nothing
but the entry; a staff edit closes a waiting answer as `replaced`; census Activity keeps keys only."""

import pytest

from census.models import CensusFacts, Member
from census.services import edit_values
from deals import activity
from deals.models import Activity
from intake.models import Intake
from intake.selectors import answers_of
from intake.services import update_answers

from .decision_world import (
    added,
    cell_entry,
    census_answers,
    employee,
    entry,
    intake_answers,
    link_on,
    submitted,
)

pytestmark = pytest.mark.django_db

CANARY = 'Zqcanaryvalue'


def _approve(api, deal, refs):
    answer = api.post(f'/api/deals/{deal.id}/review/approve/', {'refs': refs}, format='json')
    assert answer.status_code == 200, answer.content
    return answer.json()


def test_B38_done_when_an_approved_intake_answer_is_stored_with_origin_client(api, user, deal):
    link = link_on(user, deal)
    intake_answers(deal, link, {'fein': '123456789', 'dba': 'Example Trading'})
    submitted(link)
    assert 'fein' not in answers_of(deal, Intake.objects.get(deal=deal))  # OQ85: nothing lands before approval
    body = _approve(api, deal, ['intake:fein'])
    assert body['approved'] == ['intake:fein'] and len(body['activity_ids']) == 1
    intake = Intake.objects.get(deal=deal)
    assert intake.answers['fein'] == '12-3456789'
    source = intake.sources['fein']
    assert (source['origin'], source['link'], source['by']) == ('client', link.id, user.id)
    assert (intake.client['fein']['status'], intake.client['fein']['by']) == ('approved', user.id)
    assert intake.client['dba']['status'] == 'pending' and 'dba' not in intake.answers
    row = Activity.objects.get(pk=body['activity_ids'][0])
    assert (row.area, row.action, row.summary) == ('intake', 'approved', 'Approved 1 client intake answer')
    assert row.changes == [{'t': f'intake:{deal.id}', 'k': {'fein': [None, '12-3456789']}}]
    assert _approve(api, deal, ['intake:fein'])['approved'] == []  # decided already: nothing again


def test_C32_done_when_an_approved_census_answer_is_stored_with_origin_client(api, user, deal):
    member = employee(user, deal, zip='33602')
    link = link_on(user, deal)
    census_answers(deal, link, {(member.id, 'zip'): '33606', (member.id, 'job_title'): CANARY})
    submitted(link)
    assert CensusFacts.objects.get(deal=deal).pending_answers == 2
    body = _approve(api, deal, [f'census:{member.id}:zip'])
    fresh = Member.objects.get(pk=member.pk)
    assert fresh.values['zip'] == '33606'
    assert (fresh.sources['zip']['origin'], fresh.sources['zip']['link']) == ('client', link.id)
    approved = fresh.client['zip']
    assert (approved['status'], approved['prior']) == ('approved', '33602')
    assert CensusFacts.objects.get(deal=deal).pending_answers == 1
    row = Activity.objects.get(pk=body['activity_ids'][0])
    assert row.changes == [{'t': f'member:{member.id}', 'k': ['zip']}]  # keys only (rule 4, §3.8)
    assert not row.revertible
    assert CANARY not in str(Activity.objects.filter(deal=deal).values_list('summary', 'changes'))


def test_L17_keep_ours_rejects_and_changes_nothing_else(api, user, deal):
    member = employee(user, deal, zip='33602')
    link = link_on(user, deal)
    intake_answers(deal, link, {'dba': 'Their Name'})
    census_answers(deal, link, {(member.id, 'zip'): '33606'})
    answer = api.post(
        f'/api/deals/{deal.id}/review/reject/', {'refs': ['intake:dba', f'census:{member.id}:zip']}, format='json'
    )
    assert answer.status_code == 200 and set(answer.json()['rejected']) == {'intake:dba', f'census:{member.id}:zip'}
    assert entry(deal, 'dba')['status'] == 'rejected' and 'dba' not in Intake.objects.get(deal=deal).answers
    assert cell_entry(member, 'zip')['status'] == 'rejected'
    assert Member.objects.get(pk=member.pk).values['zip'] == '33602'
    rows = Activity.objects.filter(deal=deal, action='rejected')
    assert {row.area for row in rows} == {'intake', 'census'}
    assert all(isinstance(change['k'], list) for row in rows for change in row.changes)


def test_L90_an_added_person_approved_joins_the_roster_and_one_turned_away_never_shows(api, user, deal):
    link = link_on(user, deal)
    kept, turned = added(deal, link, ('Rowan', 'Synthetic'), ('Sky', 'Synthetic'))
    assert not Member.objects.filter(pk__in=[kept.pk, turned.pk]).exists()  # waiting whole (Ch. 12)
    _approve(api, deal, [f'census:{kept.id}:*'])
    reject = api.post(f'/api/deals/{deal.id}/review/reject/', {'refs': [f'census:{turned.id}:*']}, format='json')
    assert reject.status_code == 200
    assert list(Member.objects.filter(deal=deal).values_list('pk', flat=True)) == [kept.pk]
    approved = Member.objects.get(pk=kept.pk)
    assert approved.sources['first_name']['origin'] == 'client' and approved.client['*']['status'] == 'approved'
    assert Member.all_objects.get(pk=turned.pk).removed_at is not None
    facts = CensusFacts.objects.get(deal=deal)
    assert (facts.employees, facts.pending_people) == (1, 0)


def test_L17_Ch13d_a_staff_edit_closes_a_waiting_answer_as_replaced(user, deal):
    member = employee(user, deal, zip='33602')
    link = link_on(user, deal)
    intake_answers(deal, link, {'dba': 'Their Name', 'website': 'https://example.com'})
    census_answers(deal, link, {(member.id, 'zip'): '33606'})
    update_answers(user, deal.id, {'dba': 'Our Name'})
    edit_values(user, member.id, {'zip': '33607'})
    closed = entry(deal, 'dba')
    assert (closed['status'], closed['by']) == ('replaced', user.id)
    assert entry(deal, 'website')['status'] == 'pending'  # another question's answer still waits
    assert cell_entry(member, 'zip')['status'] == 'replaced'
    assert CensusFacts.objects.get(deal=deal).pending_answers == 0


def test_L17_Claudes_edit_leaves_the_clients_answer_waiting(user, deal):
    link = link_on(user, deal)
    intake_answers(deal, link, {'dba': 'Their Name'})
    update_answers(user, deal.id, {'dba': 'Read Name'}, by_claude=True)
    assert entry(deal, 'dba')['status'] == 'pending'


def test_B38_reverting_an_intake_approval_puts_the_value_back_and_the_answer_waits_again(api, user, deal):
    update_answers(user, deal.id, {'dba': 'Our Name'})
    link = link_on(user, deal)
    intake_answers(deal, link, {'dba': 'Their Name'})
    row_id = _approve(api, deal, ['intake:dba'])['activity_ids'][0]
    assert Intake.objects.get(deal=deal).answers['dba'] == 'Their Name'
    activity.revert(row_id, user)
    intake = Intake.objects.get(deal=deal)
    assert intake.answers['dba'] == 'Our Name' and intake.client['dba']['status'] == 'pending'


def test_C28_undo_approval_puts_back_what_it_replaced_and_refuses_after_a_later_edit(api, user, deal):
    member = employee(user, deal, zip='33602')
    before = Member.objects.get(pk=member.pk).sources['zip']
    link = link_on(user, deal)
    census_answers(deal, link, {(member.id, 'zip'): '33606'})
    intake_answers(deal, link, {'dba': 'Their Name'})
    refs = [f'census:{member.id}:zip', 'intake:dba']
    _approve(api, deal, refs)
    undone = api.post(f'/api/deals/{deal.id}/review/undo/', {'refs': refs}, format='json')
    assert undone.status_code == 200 and set(undone.json()['undone']) == set(refs)
    fresh = Member.objects.get(pk=member.pk)
    assert fresh.values['zip'] == '33602' and fresh.sources['zip'] == before
    assert cell_entry(member, 'zip')['status'] == 'pending' and entry(deal, 'dba')['status'] == 'pending'
    assert 'dba' not in Intake.objects.get(deal=deal).answers
    _approve(api, deal, refs)
    edit_values(user, member.id, {'zip': '33610'})
    refused = api.post(f'/api/deals/{deal.id}/review/undo/', {'refs': refs[:1]}, format='json')
    assert refused.status_code == 409 and 'ZIP' in refused.json()['detail'].upper()
    assert Member.objects.get(pk=member.pk).values['zip'] == '33610'


def test_B4_bad_refs_answer_400_and_another_deals_person_is_never_decided(api, user, deal):
    from conftest import make_deal

    url = f'/api/deals/{deal.id}/review/approve/'
    for body in ({'refs': ['intake:not_a_question']}, {'refs': 'intake:fein'}, {'refs': ['census:x:zip']}, {}):
        assert api.post(url, body, format='json').status_code == 400
    assert api.post(url, {'surface': 'payroll'}, format='json').status_code == 400
    other = make_deal(user, name='Other Co.')
    stranger = employee(user, other, zip='33602')
    link = link_on(user, other)
    census_answers(other, link, {(stranger.id, 'zip'): '33606'})
    assert _approve(api, deal, [f'census:{stranger.id}:zip'])['approved'] == []
    assert cell_entry(stranger, 'zip')['status'] == 'pending'
