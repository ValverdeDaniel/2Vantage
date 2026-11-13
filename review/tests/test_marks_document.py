"""Marks across every owner (plan.md §10.7, §8.6, §13.10 row 64 "done when"; Q.9 row 64; M88–M91, O.6 #30): Confirm all
for one file marks its values on intake, census, quotes and the questionnaire in one transaction, as one Activity row
of marks — never values — and one Revert puts every owner back; the same call again changes nothing; a later write
keeps its value out of the Revert; a sold plan refuses it; the lock order holds; the stored counts stay right."""

import json

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import ValidationError

from census.models import Member
from conftest import make_deal
from deals import activity
from deals.models import Activity
from deals.stored_counts import rebuild_all
from documents.review_rules import is_approved, mark_state
from intake.models import Intake
from questionnaire.models import Questionnaire
from quotes import services as quotes
from quotes.models import Plan
from quotes.tests.review_world import add_file
from review.services import marks

from .confidence_world import CANARY_ANSWER, CANARY_LASER, CANARY_NAME, world

pytestmark = pytest.mark.django_db


@pytest.fixture
def w(user):
    return world(user)


def approved(w):
    plan, intake = Plan.objects.get(pk=w.plan.id), Intake.objects.get(deal=w.deal)
    people = [Member.objects.get(pk=person.id) for person in w.people]
    form = Questionnaire.objects.get(pk=w.form.id)
    return {
        'plan': [key for key, entry in plan.sources.items() if is_approved(entry)],
        'intake': sorted(key for key, entry in intake.sources.items() if is_approved(entry)),
        'census': sum(1 for person in people for entry in person.sources.values() if is_approved(entry)),
        'form': [key for key, entry in form.sources.items() if is_approved(entry)],
        'stop': [key for key, entry in Plan.objects.get(pk=w.stop.id).sources.items() if is_approved(entry)],
    }


def test_M88_confirm_all_for_one_file_marks_every_owner_and_one_revert_puts_them_back(user, w):
    done = marks.mark(user, w.deal.id, 'approve', document_id=w.quote.id)
    assert done.changed == {'intake': 2, 'census': 4, 'quotes': 3, 'questionnaire': 1}
    now = approved(w)
    assert sorted(now['plan']) == ['deductible_single', 'network', 'rate_ee'] and now['intake'] == ['fein', 'sic_code']
    assert now['census'] == 4 and now['form'] == ['txtAdd2'] and now['stop'] == []  # the other file's stay
    row = done.row
    assert (row.area, row.action, row.count, row.document_id) == ('review', 'marked', 10, w.quote.id)
    assert row.summary == 'Approved 10 values from one file' and row.revertible
    keys = [key for entry in row.changes for key in entry['k']]
    assert all(key.startswith('mark.') for key in keys) and len(keys) == 10
    text = json.dumps(row.changes) + row.summary
    assert all(canary not in text for canary in (CANARY_NAME, CANARY_ANSWER, CANARY_LASER, '512.34', '00-1112223'))
    assert not any(rebuild_all([w.deal.id]).values())  # flags rewritten with the marks (Q.3 #9)

    reverted = activity.revert(row.id, user)
    assert len([key for entry in reverted.changes for key in entry['k']]) == 10
    assert approved(w) == {'plan': [], 'intake': [], 'census': 0, 'form': [], 'stop': []}
    assert not any(rebuild_all([w.deal.id]).values())
    with pytest.raises(activity.Refused):  # once (Q.3 #1)
        activity.revert(row.id, user)


def test_Q3_1_the_same_confirm_again_changes_nothing(user, w):
    marks.mark(user, w.deal.id, 'approve', document_id=w.quote.id)
    before = Activity.objects.filter(deal=w.deal).count()
    stamp = Plan.objects.get(pk=w.plan.id).updated_at
    again = marks.mark(user, w.deal.id, 'approve', document_id=w.quote.id)
    assert again.changed == {} and again.row is None
    assert Activity.objects.filter(deal=w.deal).count() == before
    assert Plan.objects.get(pk=w.plan.id).updated_at == stamp  # marks are bookkeeping (§3.7)


def test_M89_ignore_and_check_take_the_files_open_warnings_only(user, w):
    done = marks.mark(user, w.deal.id, 'ignore', document_id=w.quote.id)
    assert done.changed == {'intake': 1, 'census': 2, 'quotes': 1}  # SIC code, two birth dates, the EE rate
    plan = Plan.objects.get(pk=w.plan.id)
    assert mark_state(plan.sources['rate_ee']) == 'ignored' and not mark_state(plan.sources['network'])
    assert Plan.objects.get(pk=w.plan.id).flags == 0
    cleared = marks.mark(user, w.deal.id, 'clear', document_id=w.quote.id)
    assert cleared.changed == done.changed and Plan.objects.get(pk=w.plan.id).flags == 1


def test_M90_M91_refs_across_owners_undo_approve_and_undo_all(user, w):
    refs = [f'plan:{w.plan.id}:rate_ee', 'intake:sic_code', f'census:{w.people[0].id}:dob']
    flagged = marks.mark(user, w.deal.id, 'check', refs=refs)
    assert flagged.changed == {'intake': 1, 'census': 1, 'quotes': 1} and flagged.row.document_id is None
    approve = marks.mark(user, w.deal.id, 'approve', refs=refs[:1])  # ✓ Approve on one row
    assert approve.changed == {'quotes': 1}
    undo_all = marks.mark(user, w.deal.id, 'clear', refs=refs[1:])  # Undo all
    assert undo_all.changed == {'intake': 1, 'census': 1}
    assert not mark_state(Intake.objects.get(deal=w.deal).sources['sic_code'])


def test_M88_a_later_write_keeps_its_value_out_of_the_revert(user, w):
    done = marks.mark(user, w.deal.id, 'approve', document_id=w.quote.id)
    quotes.update_plan(user, w.plan.id, {'values': {'rate_ee': '600.00'}})  # a later edit drops its approval
    reverted = activity.revert(done.row.id, user)
    assert len([key for entry in reverted.changes for key in entry['k']]) == 9
    assert approved(w)['plan'] == [] and Plan.objects.get(pk=w.plan.id).values['rate_ee'] == '600'


def test_Q3_1_a_revert_is_refused_when_every_value_changed_since(user, w):
    done = marks.mark(user, w.deal.id, 'approve', refs=[f'plan:{w.plan.id}:network'])
    quotes.update_plan(user, w.plan.id, {'values': {'network': 'Open Access Plus'}})
    with pytest.raises(activity.Refused) as refused:
        activity.revert(done.row.id, user)
    assert 'changed after this' in refused.value.sentence


def test_rule4_a_sold_plan_refuses_the_revert(user, w):
    done = marks.mark(user, w.deal.id, 'approve', document_id=w.quote.id)
    Plan.objects.filter(pk=w.plan.id).update(sold=True)  # set-up: the plan sold since (the sale is quotes' door)
    with pytest.raises(activity.Refused) as refused:
        activity.revert(done.row.id, user)
    assert 'sold' in refused.value.sentence
    assert approved(w)['intake'] == ['fein', 'sic_code']  # nothing went back


def test_O3_7_the_deal_locks_first_then_the_owners_in_chain_order(user, w):
    with CaptureQueriesContext(connection) as queries:
        marks.mark(user, w.deal.id, 'approve', document_id=w.quote.id)
    locks = [q['sql'] for q in queries.captured_queries if 'FOR UPDATE' in q['sql']]
    tables = ['"deals_deal"', '"intake_intake"', '"census_member"', '"quotes_plan"', '"questionnaire_questionnaire"']
    firsts = [next(i for i, sql in enumerate(locks) if f'FROM {table}' in sql) for table in tables]
    assert firsts == sorted(firsts) and firsts[0] == 0


def test_M88_bad_targets_answer_400_and_another_deals_file_404(api, user, w):
    url = f'/api/deals/{w.deal.id}/review/marks/'
    assert api.post(url, {'action': 'approve'}, format='json').status_code == 400
    both = {'action': 'approve', 'document_id': w.quote.id, 'refs': ['intake:fein']}
    assert api.post(url, both, format='json').status_code == 400
    assert api.post(url, {'action': 'shout', 'document_id': w.quote.id}, format='json').status_code == 400
    assert api.post(url, {'action': 'approve', 'refs': ['link:4']}, format='json').status_code == 400
    assert api.post(url, {'action': 'approve', 'document_id': True}, format='json').status_code == 400
    assert api.post(url, {'action': 'approve', 'document_id': 2**64}, format='json').status_code == 404
    elsewhere = add_file(user, make_deal(user, name='Other (synthetic)'))
    assert api.post(url, {'action': 'approve', 'document_id': elsewhere.id}, format='json').status_code == 404
    assert api.post(f'/api/deals/{2**64}/review/marks/', both, format='json').status_code == 404
    with pytest.raises(ValidationError):
        marks.mark(user, w.deal.id, 'approve', refs=[f'plan:{w.plan.id}:no_such_field'])
    assert approved(w)['plan'] == []


def test_M88_the_endpoint_answers_what_changed_and_undo_reverts_it(api, w):
    url = f'/api/deals/{w.deal.id}/review/marks/'
    body = api.post(url, {'action': 'approve', 'document_id': w.quote.id}, format='json').json()
    assert body['changed'] == {'intake': 2, 'census': 4, 'quotes': 3, 'questionnaire': 1} and body['count'] == 10
    undone = api.post(f'/api/activity/{body["activity_id"]}/revert/')
    assert undone.status_code == 200
    assert api.post(f'/api/activity/{body["activity_id"]}/revert/').status_code == 409
    assert approved(w)['census'] == 0
