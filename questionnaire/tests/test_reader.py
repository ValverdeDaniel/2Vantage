"""The questionnaire reader (plan.md §10.4, §10.5, §10.8; D73, D74, D113, G99, G100; slice 52), run inline with the
fake client on a synthetic filled form: what Claude read waits as a staged read the job only points at, a person
uses it slot by slot, it never lands on a signed form, and no medical answer leaves the questionnaire."""

import json

import pytest

from ai import kinds, services
from ai.services import landing
from deals.activity import Refused
from deals.models import Activity
from questionnaire import services as q_services
from questionnaire.models import Questionnaire, StagedRead
from questionnaire.services import reads

from .reader_world import ANSWER, FL, ILLNESS, MEDICAL, condition, form_read, leaks
from .world import make_world

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(user):
    return make_world(user)


def _staged(job):
    return StagedRead.objects.get(job=job)


def _form(deal):
    return Questionnaire.objects.get(deal=deal, form=FL)


def test_D113_G99_a_filled_form_is_staged_and_its_job_only_points_at_it(user, world, fake_claude):
    job, document = form_read(user, world, fake_claude)
    assert job.status == kinds.DONE and job.land == 'staged' and landing.waiting(job)
    [item] = job.result['items']
    staged = _staged(job)
    assert item['op'] == 'questionnaire_read' and item['read'] == staged.id and item['form'] == FL
    assert staged.status == StagedRead.WAITING and staged.document_id == document.id and staged.form == FL
    assert staged.read['answers']['txtRsnBid']['value'] == 'Renewal Increase'  # cleaned to the option
    assert staged.read['answers']['chkFBPrior']['value'] == 'No'
    assert not Questionnaire.objects.filter(deal=world).exists()  # nothing written until a person acts
    assert 'Florida Blue 51+' in job.result['summary'] and 'ready for review' in job.result['summary']
    proposed = Activity.objects.get(deal=world, area='questionnaire', action='proposed')
    assert proposed.actor_kind == 'claude' and not proposed.changes


def test_G99_the_card_lists_old_and_new_with_page_and_doubt(user, api, world, fake_claude):
    job, _document = form_read(user, world, fake_claude)
    answer = api.get(f'/api/deals/{world.id}/questionnaires/reads/{_staged(job).id}/').json()
    by_ref = {entry['ref']: entry for entry in answer['entries']}
    assert 'txtCoName' not in by_ref and 'State' not in by_ref  # equal to what the form shows (D60)
    assert (
        by_ref['numTAP']['old'] == '58' and by_ref['numTAP']['new'] == '61' and by_ref['numTAP']['state'] == 'replace'
    )
    assert (
        by_ref['chkFBPrior']['state'] == 'fill' and by_ref['chkFBPrior']['tick'] and by_ref['chkFBPrior']['page'] == 1
    )
    comments = by_ref['txtMcComments']
    assert comments['sensitive'] and not comments['tick'] and 'not sure' in comments['why']
    assert by_ref['chkMedCon']['opens'] == 'conditions' and by_ref['chkMedCon']['new'] == 'Yes'
    plan = by_ref['row:plans:1']
    assert plan['target_number'] == 1 and [v['key'] for v in plan['values']] == ['numCurrRatePrem']  # the Advisor's row
    assert by_ref['row:conditions:1']['target_number'] is None and by_ref['row:conditions:1']['sensitive']
    assert not answer['signed'] and answer['status'] == 'waiting'


def test_G99_use_lands_the_ticked_answers_as_reads_with_file_page_and_doubt(user, world, fake_claude):
    job, document = form_read(user, world, fake_claude)
    job, landed = services.apply(user, job.id)
    row = _form(world)
    assert row.answers['numTAP'] == '61' and row.answers['chkFBPrior'] == 'No' and row.answers['chkMedCon'] == 'Yes'
    entry = row.sources['numTAP']
    assert entry['origin'] == 'ai' and entry['doc'] == document.id and entry['page'] == 1 and 'low' not in entry
    assert 'txtMcComments' not in row.answers  # doubted: unticked, so "Use this scan" leaves it
    [plan] = row.rows['plans']
    assert row.answers[f'plans.{plan["id"]}.numCurrRatePrem'] == '41250' and plan['origin'] == 'prefill'
    [added] = row.rows['conditions']
    assert added['origin'] == 'ai' and added['doc'] == document.id
    assert row.answers[f'conditions.{added["id"]}.drpMedCondition'] == 'Breast Cancer'
    assert job.resolution == 'applied' and 'items' not in job.result  # emptied (D74)
    staged = _staged(job)
    assert staged.status == StagedRead.APPLIED and staged.read == {} and staged.landed['slots']
    assert landed['summary'] == 'Florida Blue 51+: 5 answers, 2 rows' and landed['areas']  # questions, then rows


def test_G99_apply_selected_takes_a_doubted_answer_when_ticked(user, world, fake_claude):
    job, _document = form_read(user, world, fake_claude)
    services.apply(user, job.id, select=[f'{FL}:txtMcComments', f'{FL}:row:conditions:1'])
    row = _form(world)
    assert row.answers['txtMcComments'] == MEDICAL and row.sources['txtMcComments']['low']
    assert row.answers['chkMedCon'] == 'Yes'  # the conditions' row brings the answer that shows them
    assert 'numTAP' not in row.answers  # not chosen


def test_G99_an_answer_a_person_stands_behind_is_a_conflict_never_written(user, api, world, fake_claude):
    q_services.set_answers(user, world.id, FL, {'drpNumCarr': '1'})
    job, _document = form_read(user, world, fake_claude)
    staged = _staged(job)
    entry = next(e for e in reads.review.entries(*_view(world, staged))[0] if e['ref'] == 'drpNumCarr')
    assert entry['state'] == 'conflict' and not entry['tick'] and 'typed' in entry['why']
    _job, landed = services.apply(user, job.id, select=[f'{FL}:drpNumCarr', f'{FL}:chkFBPrior'])
    row = _form(world)
    assert row.answers['drpNumCarr'] == '1' and row.sources['drpNumCarr']['origin'] == 'typed'
    assert row.answers['chkFBPrior'] == 'No' and any('stands behind' in said for said in landed['skipped'])


def _view(deal, staged):
    from questionnaire.selectors import context

    row = Questionnaire.objects.filter(deal=deal, form=FL).first()
    return context.form_view(FL, row, context.prefill_facts(deal)), staged.read, staged.document_id


def test_G99_D113_a_signed_form_is_never_read_into(user, world, fake_claude):
    q_services.set_answers(user, world.id, FL, {'chkFBPrior': 'Yes'})
    q_services.sign(user, world.id, FL, 'officer', 'Pat Sample', authorized=True, sign_anyway=True)
    job, _document = form_read(user, world, fake_claude)
    assert job.status == kinds.FAILED and 'signed' in job.error and 'Reopen' in job.error
    assert fake_claude.log == []  # refused before any call: it costs nothing
    assert not StagedRead.objects.filter(deal=world).exists()


def test_G99_a_read_staged_before_the_signature_is_refused_after_it(user, api, world, fake_claude):
    job, _document = form_read(user, world, fake_claude)
    q_services.set_answers(user, world.id, FL, {'txtAdd2': 'Suite 9'})
    q_services.sign(user, world.id, FL, 'officer', 'Pat Sample', authorized=True, sign_anyway=True)
    before = dict(_form(world).answers)
    shown = api.get(f'/api/deals/{world.id}/questionnaires/reads/{_staged(job).id}/').json()
    assert shown['signed'] is True
    refused = api.post(f'/api/ai/jobs/{job.id}/apply/', {}, format='json')
    assert refused.status_code == 409 and 'signed' in refused.json()['detail']
    assert _form(world).answers == before and _staged(job).status == StagedRead.WAITING


def test_G99_a_form_signed_while_claude_reads_is_staged_saying_so(user, world, fake_claude):
    q_services.set_answers(user, world.id, FL, {'txtAdd2': 'Suite 9'})

    def sign_now():
        q_services.sign(user, world.id, FL, 'officer', 'Pat Sample', authorized=True, sign_anyway=True)

    job, _document = form_read(user, world, fake_claude, during=sign_now)
    [item] = job.result['items']
    assert item['signed'] is True and item['tick'] is False
    assert 'signed while Claude read' in job.result['findings'][0]['text']
    with pytest.raises(Refused):
        services.apply(user, job.id)


def test_G100_a_reread_of_the_same_file_updates_only_its_own_untouched_rows(user, world, fake_claude):
    first = {'answers': [], 'rows': [condition(), condition('Second synthetic note', '2')]}
    job, document = form_read(user, world, fake_claude, first)
    services.apply(user, job.id)
    rows = [r['id'] for r in _form(world).rows['conditions']]
    assert len(rows) == 2
    again = {'answers': [], 'rows': [condition('Updated synthetic note'), condition('Second synthetic note', '3')]}
    job, _document = form_read(user, world, fake_claude, again, document=document)
    services.apply(user, job.id)
    row = _form(world)
    assert [r['id'] for r in row.rows['conditions']] == rows  # the same rows, updated
    assert row.answers[f'conditions.{rows[0]}.txtMedIll'] == 'Updated synthetic note'
    assert row.answers[f'conditions.{rows[1]}.numNumEEMedCon'] == '3'
    q_services.set_answers(user, world.id, FL, {f'conditions.{rows[0]}.numNumEEMedCon': '4'})  # a person's row now
    job, _document = form_read(
        user, world, fake_claude, {'answers': [], 'rows': [condition('Third synthetic note')]}, document=document
    )
    services.apply(user, job.id)
    row = _form(world)
    assert row.answers[f'conditions.{rows[0]}.txtMedIll'] == 'Updated synthetic note'  # never mixed into it
    assert row.answers[f'conditions.{rows[1]}.txtMedIll'] == 'Third synthetic note'  # the read's own row


def test_D73_undo_puts_every_answer_back_sensitive_ones_too(user, world, fake_claude):
    job, _document = form_read(user, world, fake_claude)
    services.apply(user, job.id, select=[f'form:{FL}', f'{FL}:txtMcComments'])
    assert _form(world).answers['txtMcComments'] == MEDICAL
    job, _changed = services.undo(user, job.id)
    row = _form(world)
    assert 'numTAP' not in row.answers and 'txtMcComments' not in row.answers and 'chkMedCon' not in row.answers
    assert row.rows['conditions'] == [] and len(row.rows['plans']) == 1  # its row off, the Advisor's kept
    assert _staged(job).status == StagedRead.UNDONE and _staged(job).landed == {}
    assert job.resolution == 'undone' and job.result['landed']['undone']['reverted']


def test_D73_undo_after_a_later_edit_asks_and_undo_anyway_keeps_it(user, world, fake_claude):
    job, _document = form_read(user, world, fake_claude)
    services.apply(user, job.id)
    q_services.set_answers(user, world.id, FL, {'numTAP': '63'})
    with pytest.raises(landing.UndoRefused) as refused:
        services.undo(user, job.id)
    assert 'numTAP' in refused.value.keys
    services.undo(user, job.id, force=True)
    row = _form(world)
    assert row.answers['numTAP'] == '63' and 'chkFBPrior' not in row.answers


def test_D74_discard_sets_the_staged_read_aside_emptied(user, world, fake_claude):
    job, _document = form_read(user, world, fake_claude)
    services.discard(user, job.id)
    staged = _staged(job)
    assert staged.status == StagedRead.DISCARDED and staged.read == {}
    assert not Questionnaire.objects.filter(deal=world).exists()


def test_G99_a_read_that_finds_nothing_fails(user, world, fake_claude):
    job, _document = form_read(user, world, fake_claude, {'answers': [], 'rows': []})
    assert job.status == kinds.FAILED and job.error == 'No questionnaire answers could be read from this file.'


def test_D60_a_read_that_matches_the_form_waits_for_no_one(user, world, fake_claude):
    same = {'answers': [ANSWER['answers'][0]], 'rows': []}
    job, _document = form_read(user, world, fake_claude, same)
    assert job.status == kinds.DONE and not landing.waiting(job) and job.result['items'] == []
    assert job.result['summary'].startswith('Nothing new') and not StagedRead.objects.filter(deal=world).exists()


def test_Q8_no_medical_answer_leaves_the_questionnaire(user, api, world, fake_claude):
    job, _document = form_read(user, world, fake_claude)
    seen = [
        json.dumps(job.result),
        json.dumps(job.steps),
        job.error,
        json.dumps(api.get(f'/api/deals/{world.id}/ai/').json()),
    ]
    services.apply(user, job.id, select=[f'form:{FL}', f'{FL}:txtMcComments'])
    job.refresh_from_db()
    seen.append(json.dumps(job.result))
    services.undo(user, job.id)
    job.refresh_from_db()
    seen.append(json.dumps(job.result))
    seen += [f'{a.summary} {json.dumps(a.changes)}' for a in Activity.objects.filter(deal=world)]
    assert not any(leaks(text) for text in seen)
    hidden = Activity.objects.filter(deal=world, area='questionnaire', action='read')
    assert any(isinstance(entry['k'], list) for row in hidden for entry in row.changes)  # keys only (rule 4)
    assert ILLNESS not in json.dumps([row.changes for row in hidden])


def test_Q3_a_read_of_another_deal_or_past_bigint_answers_404(user, api, world, fake_claude):
    job, _document = form_read(user, world, fake_claude)
    other = make_world(user)
    read_id = _staged(job).id
    assert api.get(f'/api/deals/{other.id}/questionnaires/reads/{read_id}/').status_code == 404
    assert api.get(f'/api/deals/{world.id}/questionnaires/reads/{2**64}/').status_code == 404
    assert api.get(f'/api/deals/{world.id}/questionnaires/reads/{read_id}/').status_code == 200


def test_G99_a_used_read_shows_no_answers_any_more(user, api, world, fake_claude):
    job, _document = form_read(user, world, fake_claude)
    services.apply(user, job.id)
    shown = api.get(f'/api/deals/{world.id}/questionnaires/reads/{_staged(job).id}/').json()
    assert shown['status'] == 'applied' and shown['entries'] == [] and not leaks(json.dumps(shown))


def test_D73_G99_a_read_is_not_undone_on_a_signed_form(user, world, fake_claude):
    job, _document = form_read(user, world, fake_claude)
    services.apply(user, job.id)
    q_services.sign(user, world.id, FL, 'officer', 'Pat Sample', authorized=True, sign_anyway=True)
    with pytest.raises(Refused) as refused:
        services.undo(user, job.id, force=True)
    assert 'signed' in refused.value.sentence and _form(world).answers['numTAP'] == '61'
