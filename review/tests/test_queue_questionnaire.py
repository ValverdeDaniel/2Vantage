"""The questionnaire in review (plan.md §7.13, §8.8; G68–G70, G73, G81, L21; slice 58): the client's answers on a form
wait in the queue's Questionnaire section, labelled by the form's own words; Approve lands them through the
questionnaire, Keep ours waits for a reopen on a signed form, and the counts reach `summary.facts` (Agenda's
questionnaire step) and the Board's To review lane. Synthetic data."""

import pytest

from questionnaire.models import Questionnaire
from questionnaire.selectors import portal
from questionnaire.services import client as questionnaire_client
from questionnaire.services import sign_from_link
from questionnaire.tests.world import make_world
from review import summary
from review.selectors import items as item_rows
from review.services import decisions, tray

from .decision_world import link_on, submitted

pytestmark = pytest.mark.django_db
FL = 'fl_blue_51'
ASKS = {'questionnaires': [{'form': FL, 'mode': 'online'}]}


@pytest.fixture
def world(user):
    return make_world(user)


def answered(deal, link, values):
    lv = portal.link_view(deal, FL, link.id)
    sent = {slot: {'value': value, 'base': portal.base_of(lv, slot)} for slot, value in values.items()}
    saved = questionnaire_client.save_client(deal.id, link.id, FL, sent)
    assert not saved.conflicts


def test_L21_G69_the_queue_lists_the_forms_answers_in_its_words(api, user, world):
    link = link_on(user, world, ASKS)
    answered(world, link, {'txtRsnBid': 'Renewal Increase', 'chkMedCon': 'No'})
    submitted(link)
    found = api.get(f'/api/deals/{world.id}/review/queue/', {'surface': 'questionnaire'}).json()
    by_ref = {item['ref']: item for item in found['items']}
    item = by_ref[f'q:{FL}:txtRsnBid']
    assert item['label'].startswith('12. Reason') and item['theirs'] == 'Renewal Increase'
    assert item['ready_why'] == 'submitted' and item['form'] == FL and item['editable'] is True
    assert by_ref[f'q:{FL}:chkMedCon']['sensitive'] is True
    assert found['groups'] and all(group['label'].startswith('Florida Blue 51+') for group in found['groups'])


def test_G73_approve_ready_takes_the_forms_submitted_answers(api, user, world):
    link = link_on(user, world, ASKS)
    answered(world, link, {'txtRsnBid': 'Renewal Increase'})
    submitted(link)
    body = {'surface': 'questionnaire', 'ready_only': True}
    answer = api.post(f'/api/deals/{world.id}/review/approve/', body, format='json')
    assert answer.status_code == 200 and answer.json()['approved'] == [f'q:{FL}:txtRsnBid']
    row = Questionnaire.objects.get(deal=world, form=FL)
    assert row.answers['txtRsnBid'] == 'Renewal Increase' and row.sources['txtRsnBid']['origin'] == 'client'


def test_G70_keep_ours_on_a_signed_form_answers_409_and_approve_files_the_copy(api, user, world):
    link = link_on(user, world, ASKS)
    answered(world, link, {'txtRsnBid': 'Renewal Increase'})
    sign_from_link(world.id, link.id, FL, 'Robin Example', sign_anyway=True)
    submitted(link)
    ref = f'q:{FL}:txtRsnBid'
    item = api.get(f'/api/deals/{world.id}/review/queue/', {'surface': 'questionnaire'}).json()['items'][0]
    assert item['signed'] is True and item['editable'] is False
    kept = api.post(f'/api/deals/{world.id}/review/reject/', {'refs': [ref]}, format='json')
    assert kept.status_code == 409
    approved = api.post(f'/api/deals/{world.id}/review/approve/', {'refs': [ref]}, format='json')
    assert approved.status_code == 200
    assert Questionnaire.objects.get(deal=world, form=FL).signed_document_id is not None


def test_L118_the_facts_count_questionnaire_answers_waiting(user, world):
    link = link_on(user, world, ASKS)
    answered(world, link, {'txtRsnBid': 'Renewal Increase', 'chkFBPrior': 'No'})
    found = summary.facts([world.id])[world.id]
    assert found['pending']['questionnaire'] == 2 and found['pending']['total'] >= 2
    assert found['sections']['questionnaire']['in_progress'] == 2
    submitted(link)
    found = summary.facts([world.id])[world.id]
    assert found['ready']['questionnaire'] == 2


def test_L9_the_board_lists_the_questionnaire_in_to_review(api, user, world):
    link = link_on(user, world, ASKS)
    answered(world, link, {'txtRsnBid': 'Renewal Increase'})
    submitted(link)
    board = api.get(f'/api/deals/{world.id}/review/board/').json()
    row = next(row for row in board['lanes']['to_review'] if row['key'] == 'questionnaire')
    assert row['count'] == 1 and row['fix'] == {'tab': 'review', 'view': 'queue', 'section': 'questionnaire'}


def test_G76_an_ask_for_a_question_names_it_and_needs_a_pin_link(user, world):
    found = item_rows.resolve(world, [f'q:{FL}:txtRsnBid', f'qform:{FL}'])
    one, whole = found[f'q:{FL}:txtRsnBid'], found[f'qform:{FL}']
    assert one.section == 'questionnaire' and one.pin and 'Reason' in one.label
    assert whole.label.startswith('Florida Blue 51+') and not whole.gone
    drafts = tray.ask(user, world.id, [f'q:{FL}:txtRsnBid']).drafts
    assert drafts and drafts[0].surface == 'questionnaire' and drafts[0].key == f'{FL}:txtRsnBid'


def test_G81_decisions_name_a_bad_questionnaire_ref(api, world):
    answer = api.post(f'/api/deals/{world.id}/review/approve/', {'refs': [f'q:{FL}:noSuchField']}, format='json')
    assert answer.status_code == 400
    assert decisions.approve(None, world.id, refs=[f'q:{FL}:txtRsnBid']).refs == []


def test_G76_the_missing_lane_names_a_forms_blanks_and_asks_it_online(api, user, world):
    board = api.get(f'/api/deals/{world.id}/review/board/').json()
    row = next(row for row in board['lanes']['missing'] if row['key'] == f'questionnaire:{FL}')
    assert row['count'] == len(row['items']) and row['ask'] == {'refs': [f'qform:{FL}']}
    assert row['ask_label'] == '＋ Ask them to fill it out online'
    assert row['fix'] == {'tab': 'questionnaire', 'form': FL}
    assert board['sections']['questionnaire']['missing'] == row['count']
    tray.ask(user, world.id, [f'qform:{FL}'])
    board = api.get(f'/api/deals/{world.id}/review/board/').json()
    row = next(row for row in board['lanes']['missing'] if row['key'] == f'questionnaire:{FL}')
    assert row['ask'] is None and row['left'] == 0


def test_G79_enter_it_writes_the_answer_as_the_clients_entered_by_us(api, user, world):
    link = link_on(user, world, ASKS)
    answered(world, link, {'txtRsnBid': 'Other'})
    body = {'answers': {f'q:{FL}:txtRsnBid': 'Renewal Increase'}, 'origin': 'relay'}
    answer = api.post(f'/api/deals/{world.id}/review/enter/', body, format='json')
    assert answer.status_code == 200 and answer.json()['saved'] == [f'q:{FL}:txtRsnBid']
    row = Questionnaire.objects.get(deal=world, form=FL)
    assert row.sources['txtRsnBid']['origin'] == 'relay' and row.client['txtRsnBid']['status'] == 'replaced'


def test_G78_the_request_page_lists_a_forms_questions_by_section(api, user, world):
    page = api.get(f'/api/deals/{world.id}/review/request/', {'pane': 'questionnaire'}).json()
    refs = [item['ref'] for item in page['items']]
    assert refs[0] == f'qform:{FL}' and f'q:{FL}:txtRsnBid' in refs
    item = next(item for item in page['items'] if item['ref'] == f'q:{FL}:txtRsnBid')
    assert item['needed'] is True and item['status'] == 'missing'
    assert any(item['gate'] for item in page['items'] if item['ref'].startswith('q:'))
    assert any(pane['key'] == 'questionnaire' for pane in page['panes'])
