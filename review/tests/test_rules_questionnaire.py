"""Review's pure rules for questionnaire refs (plan.md §5.8, §6.12; G78, G80, L21, L64; slice 58): the refs a
decision and a note name, what a request asks when an ask joins it, and the floor a form online sets."""

import pytest

from review.rules import join as join_rules
from review.rules import policy
from review.rules import refs as ref_rules
from review.rules.asks import empty
from review.rules.requests import carries

FL = 'fl_blue_51'


def test_L21_split_names_questionnaire_answers_as_form_and_slot():
    found = ref_rules.split([f'q:{FL}:txtRsnBid', f'q:{FL}:plans.3.txtCurrPlanName', 'intake:fein'])
    assert found['questionnaire'] == [(FL, 'txtRsnBid'), (FL, 'plans.3.txtCurrPlanName')]
    assert found['intake'] == ['fein']
    with pytest.raises(ref_rules.Bad):
        ref_rules.split([f'q:{FL}:noSuchField'])
    with pytest.raises(ref_rules.Bad):
        ref_rules.split(['q:no_form:txtRsnBid'])


def test_L22_a_note_keeps_a_questionnaire_ref_and_gives_it_back():
    for ref in (f'q:{FL}:txtRsnBid', f'qform:{FL}', f'q:{FL}:conditions.2.drpMedCat'):
        surface, key, member = ref_rules.note_of(ref)
        assert surface == 'questionnaire' and member is None
        assert ref_rules.ref_of_note(surface, key, member) == ref
    assert ref_rules.note_of('qform:nothing') is None


def test_G80_an_ask_joins_its_forms_picks_and_a_whole_form_drops_them():
    asks, added = join_rules.join(empty(), [f'q:{FL}:txtRsnBid', f'q:{FL}:plans.4.txtCurrPlanName'])
    form = asks['questionnaires'][0]
    assert added and form['mode'] == 'online' and form['picks'] == {'fields': ['txtRsnBid'], 'blocks': ['plans']}
    assert carries(asks, f'q:{FL}:txtRsnBid') and not carries(asks, f'q:{FL}:chkMedCon')
    whole, added = join_rules.join(asks, [f'qform:{FL}'])
    assert added == [f'qform:{FL}'] and whole['questionnaires'][0]['picks'] == {'fields': [], 'blocks': []}
    assert join_rules.join(whole, [f'q:{FL}:chkMedCon'])[1] == []  # the whole form asks it already


def test_L64_a_form_online_needs_a_pin_and_a_signed_copy_does_not():
    online = {'questionnaires': [{'form': FL, 'mode': 'online', 'picks': {}}]}
    paper = {'questionnaires': [{'form': FL, 'mode': 'upload', 'picks': {}}]}
    assert policy.floor(online)['level'] == policy.PIN
    assert policy.floor(paper)['level'] == policy.LINK


def test_L59_a_picked_question_comes_off_its_form_and_a_whole_form_comes_off_whole():
    from review.rules import form_plan

    def plan(asks, refs, carried):
        found, errors = form_plan.parse({'off': {'refs': refs}, 'on': {}})
        assert not errors
        return form_plan.plan(asks, found, add=(), carried=carried, columns=())

    picked = {'questionnaires': [{'form': FL, 'mode': 'online', 'picks': {'fields': ['txtRsnBid', 'chkMedCon'],
                                                                          'blocks': []}}]}  # fmt: skip
    found = plan(picked, [f'q:{FL}:txtRsnBid'], {f'q:{FL}:txtRsnBid', f'q:{FL}:chkMedCon'})
    assert found.asks['questionnaires'][0]['picks']['fields'] == ['chkMedCon'] and found.removed
    whole = {'questionnaires': [{'form': FL, 'mode': 'online', 'picks': {'fields': [], 'blocks': []}}]}
    refused = plan(whole, [f'q:{FL}:txtRsnBid'], {f'q:{FL}:txtRsnBid', f'qform:{FL}'})
    assert refused.refused == [f'q:{FL}:txtRsnBid']
    gone = plan(whole, [f'qform:{FL}'], {f'qform:{FL}'})
    assert not gone.asks.get('questionnaires')
