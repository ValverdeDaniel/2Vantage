"""The questionnaire reader's parts (plan.md §10.4, §10.6, §10.8; D55, G99, G101, G102, G106, PHI7; slice 52): the
merge and the cleaner on their own, which form a file fills, what Claude is sent, the chat context, and the PHI-gate
switch both ways."""

import json
from types import SimpleNamespace

import pytest
from rest_framework.exceptions import ValidationError

from ai import registry, services
from ai.services.jobs import PHI_OFF
from questionnaire import forms, turn_context
from questionnaire import reader as questionnaire_reader
from questionnaire import services as q_services
from questionnaire.reader import clean, merge, prompt, schema
from questionnaire.selectors import context

from .reader_world import ANSWER, FL, MEDICAL, SIIA, answer, condition, form_pdf, form_read, key, upload
from .world import make_world

pytestmark = pytest.mark.django_db


def _part(*pages):
    return SimpleNamespace(pages=pages)


def _file(doc_id, order=0):
    return SimpleNamespace(id=doc_id, order=order, document=None, kind='questionnaire')


def test_G99_the_first_reading_of_an_answer_wins_and_a_different_one_is_doubted():
    target = merge.empty()
    form = forms.FORMS[FL]
    merge._answers(form, target, {'answers': [answer('numTAP', '61', page=2)]}, 7, 1, 3)
    merge._answers(form, target, {'answers': [answer('numTAP', '64'), answer('nope', 'x')]}, 7, 4, 4)
    assert target['answers']['numTAP'] == {'value': '61', 'page': 2, 'low': merge.TWICE, 'doc': 7}
    assert target['twice'] == 1 and target['unknown'] == 1


def test_G99_rows_past_a_section_s_maximum_are_counted_never_lost():
    target = merge.empty()
    form = forms.FORMS[FL]
    rows = [condition(people=str(n)) for n in range(1, 63)]
    merge._rows(form, target, {'rows': rows}, 7, 1, 1)
    assert len(target['rows']['conditions']) == 60 and target['dropped'] == {'conditions': 2}


def test_G99_a_page_outside_its_range_falls_back_to_the_range_s_first():
    target = merge.empty()
    merge._answers(forms.FORMS[FL], target, {'answers': [answer('numTAP', '61', page=9)]}, 7, 3, 4)
    assert target['answers']['numTAP']['page'] == 3


def test_G16_G99_answers_go_through_the_form_s_own_cleaner():
    read = {
        **merge.empty(),
        'documents': [7],
        'answers': {
            'State': {'value': 'florida', 'page': 1, 'low': ''},
            'drpSIC': {'value': '3441 — Fabricated Structural Metal', 'page': 1, 'low': ''},
            'numTAP': {'value': 'about sixty', 'page': 1, 'low': ''},
            'dteAnnivDate': {'value': '1/1/2027', 'page': 1, 'low': ''},
        },
        'rows': {
            'conditions': [
                {'values': {'drpMedCat': 'CANCER', 'drpMedCondition': 'breast cancer'}, 'page': 1, 'low': []}
            ]
        },
    }
    cleaned = clean.clean(forms.FORMS[FL], read)
    answers = cleaned['answers']
    assert answers['State']['value'] == 'FL' and answers['drpSIC']['value'] == '3441'
    sic = dict(forms.FORMS[FL]['tables']['sic_codes'])
    assert answers['drpSICDesc']['value'] == sic['3441']  # its twin, from the code
    assert answers['dteAnnivDate']['value'] == '2027-01-01' and 'numTAP' not in answers
    assert cleaned['rows']['conditions'][0]['values'] == {'drpMedCat': 'Cancer', 'drpMedCondition': 'Breast Cancer'}
    assert cleaned['counts']['not_taken'] == 1


def test_D55_one_prompt_and_schema_for_every_form_and_the_note_names_the_form_never_the_file(user, fake_claude):
    deal = make_world(user)
    job, document = form_read(user, deal, fake_claude)
    [call] = fake_claude.log
    sent = json.dumps(call['params'])
    assert 'filled questionnaire (synthetic)' not in sent and document.original_name not in sent
    assert 'Florida Blue 51+' in sent and f'"{FL}"' in prompt.note(
        SimpleNamespace(kind='questionnaire', document=document, id=document.id), {}
    )
    assert set(schema.ANSWER_KEYS) >= {
        field['key']
        for form in forms.FORMS.values()
        for s in form['sections']
        for field in s['fields']
        if not field.get('auto')
    }
    for form in forms.FORMS.values():
        assert f'## {form["key"]}:' in prompt.PROMPT  # every form's questions, in the one cached prompt


def test_G101_G102_a_stop_loss_disclosure_s_file_fills_the_deal_s_disclosure(user, fake_claude):
    deal = make_world(user, lines=('medical', 'stop_loss'))
    q_services.choose_form(user, deal.id, 'stop_loss_disclosure', SIIA)
    raw = form_pdf(['Standard stop loss disclosure (synthetic, filled)', 'Plan sponsor: Example Fabrication LLC'])
    read = {
        'answers': [answer('plan_sponsor', 'Example Fabrication LLC'), answer('claims_admin', 'Example TPA')],
        'rows': [],
    }
    document = upload(user, deal, raw, kind='stop_loss')
    fake_claude.record(key(raw), read)
    [(job, _made)], not_read = services.start_send(user, deal, [document.id], tab='documents')  # a Documents send
    job.refresh_from_db()
    assert not not_read and job.target == 'questionnaire'
    assert job.result['items'][0]['form'] == SIIA and job.result['items'][0]['answers'] == 1  # the sponsor is prefilled


def test_G99_a_file_whose_kind_has_no_form_on_the_deal_is_refused_before_any_call(user, fake_claude):
    deal = make_world(user)  # no stop-loss disclosure chosen
    raw = form_pdf(['A stop-loss disclosure (synthetic)'])
    job, _document = form_read(user, deal, fake_claude, {'answers': [], 'rows': []}, raw=raw, kind='stop_loss')
    assert job.status == 'failed' and 'no fillable stop-loss disclosure' in job.error and fake_claude.log == []


def test_G106_a_chat_on_the_questionnaire_tab_sees_medical_answers_only_as_answered(user):
    deal = make_world(user)
    q_services.set_answers(user, deal.id, FL, {'chkMedCon': 'Yes', 'txtMcComments': MEDICAL, 'chkFBPrior': 'No'})
    row = q_services.add_row(user, deal.id, FL, 'conditions')
    q_services.set_answers(user, deal.id, FL, {f'conditions.{row.row_id}.drpMedCat': 'Cancer'})
    text = turn_context.provide(deal, {'tab': 'questionnaire'})
    assert '<questionnaire>' in text and 'chkFBPrior) = No [typed]' in text
    assert 'txtMcComments) = answered' in text and MEDICAL not in text and 'Cancer' not in text
    assert 'values not shown' in text and 'Florida Blue' in text
    assert turn_context.provide(deal, {'tab': 'advisor'}) == ''


@pytest.fixture
def switch_off(settings):
    settings.AI_PHI_READERS = False
    registry.readers.pop('questionnaire', None)
    registry.context.pop('questionnaire', None)
    yield
    settings.AI_PHI_READERS = True
    questionnaire_reader.register()


def test_PHI7_the_questionnaire_reader_waits_for_the_phi_gate_switch(user, fake_claude, switch_off):
    assert questionnaire_reader.register() is False
    assert 'questionnaire' not in registry.readers and 'questionnaire' not in registry.context
    deal = make_world(user)
    document = upload(user, deal)
    with pytest.raises(ValidationError) as refused:
        services.start_read(user, deal, [document.id], target='questionnaire')
    assert refused.value.detail['target'] == [PHI_OFF]
    assert services.start_send(user, deal, [document.id], tab='questionnaire') == ([], [document.id])


def test_PHI7_with_the_switch_on_the_questionnaire_reader_and_its_context_register(settings):
    settings.AI_PHI_READERS = True
    assert questionnaire_reader.register() is True
    assert registry.readers['questionnaire'].must_review and 'questionnaire' in registry.context
    assert registry.readers['questionnaire'].kinds == ('questionnaire', 'stop_loss')


def test_G102_a_file_fills_the_form_its_checklist_item_arms(user):
    deal = make_world(user, lines=('medical', 'stop_loss'))
    q_services.choose_form(user, deal.id, 'medical_questionnaire', 'wp_lg')
    q_services.choose_form(user, deal.id, 'stop_loss_disclosure', SIIA)
    from questionnaire.reader import which

    ctx = context.deal_context(deal)
    assert which.form_for(ctx, 'questionnaire') == 'wp_lg' and which.form_for(ctx, 'stop_loss') == SIIA
    assert which.form_for(ctx, 'quote') == ''
    assert ANSWER['answers']  # the recorded answer is the Florida Blue one; Warner's keys would be left out
