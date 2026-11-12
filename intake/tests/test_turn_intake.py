"""Work with Claude on Intake (plan.md §10.6; B39; slice 51): the intake turn sees the form as it stands, proposes
answers and coverage lines through its tool, a value the producer said lands as their own hand edit and one Claude
proposed as Claude's to check, a typed answer is never written over by Claude alone, and ↶ Undo this run puts it back.
"""

import pytest

from accounts.models import Profile
from ai import services
from ai.testing import text_block, tool_block, turn_key
from intake.models import CurrentCoverage, Intake
from intake.services import update_answers

WORDS = 'Our legal name is Example Holdings LLC; fill what you can'
TOOL = 'propose_intake_changes'
PROPOSAL = {
    'answers': [
        {'key': 'legal_name', 'value': 'Example Holdings LLC', 'dictated': True},
        {'key': 'fein', 'value': '12-3456789', 'dictated': False},
        {'key': 'dba', 'value': 'Example Shop', 'dictated': False},
        {'key': 'not_a_question', 'value': 'x', 'dictated': False},
    ],
    'coverage': [{'line': 'medical', 'carrier': 'Example Health Plan', 'funding': 'fully_insured', 'renewal_date': ''}],
}


@pytest.fixture
def direct(db):
    from django.contrib.auth import get_user_model

    person = get_user_model().objects.create_user('dee', 'dee@example.com', 'pw-Example-1')
    Profile.objects.create(user=person, claude_direct=True)
    return person


def _turn(person, deal, fake, proposal=PROPOSAL):
    fake.record(turn_key(WORDS, 1), content=[tool_block(TOOL, proposal)])
    fake.record(turn_key(WORDS, 2), content=[text_block('Done.')])
    _chat, _message, job = services.send_message(person, deal, text=WORDS, tab='intake')
    job.refresh_from_db()
    return job


def test_B39_the_intake_turn_sees_the_form_and_its_tool(direct, deal, fake_claude):
    update_answers(direct, deal.id, {'sic_code': '1234'})
    _turn(direct, deal, fake_claude)
    first = fake_claude.log[0]['params']
    assert TOOL in [tool['name'] for tool in first['tools']]
    assert next(tool for tool in first['tools'] if tool['name'] == TOOL)['strict'] is False  # the grammar limit (s37)
    context = first['messages'][-1]['content'][-2]['text']
    assert '<intake>' in context and 'sic_code = NAICS / SIC Code: 1234' in context
    assert 'Needed and still blank:' in context
    said = fake_claude.log[-1]['params']['messages'][-1]['content'][0]['content']
    assert '"not_a_question" is not an intake question.' in said


def test_B39_dictated_answers_land_as_hand_edits_and_proposed_ones_as_claudes(direct, deal, fake_claude):
    job = _turn(direct, deal, fake_claude)
    assert job.resolution == 'applied'
    intake = Intake.objects.get(deal=deal)
    assert intake.answers['legal_name'] == 'Example Holdings LLC' and intake.sources['legal_name']['origin'] == 'typed'
    fein = intake.sources['fein']
    assert fein['origin'] == 'ai' and fein['low'] and fein['read_value'] == '12-3456789'
    assert CurrentCoverage.objects.get(deal=deal, line='medical').carrier == 'Example Health Plan'
    services.undo(direct, job.id)
    intake.refresh_from_db()
    assert 'fein' not in intake.answers and not CurrentCoverage.objects.filter(deal=deal).exists()


def test_B39_claude_never_writes_over_a_typed_answer_unless_the_producer_says_it(direct, deal, fake_claude):
    update_answers(direct, deal.id, {'dba': 'Typed Name', 'legal_name': 'Old Legal Name'})
    job = _turn(direct, deal, fake_claude)
    items = {item['key']: item for item in job.result['items'] if item['op'] == 'answer'}
    assert not items['dba']['tick'] and 'typed by a person' in items['dba']['why']
    assert items['legal_name']['tick']  # the producer said it: their own edit
    answers = Intake.objects.get(deal=deal).answers
    assert answers['dba'] == 'Typed Name' and answers['legal_name'] == 'Example Holdings LLC'


def test_D81_B39_a_malformed_input_is_refused_in_words_and_stages_nothing(direct, deal, fake_claude):
    """The tool goes without `strict` (past the API's grammar limit, slice 37), so its input is checked in code."""
    bad = [
        tool_block(TOOL, {'answers': 5}, 'toolu_a'),
        tool_block(
            TOOL, {'coverage': [{'line': 'boats', 'carrier': '', 'funding': '', 'renewal_date': ''}]}, 'toolu_b'
        ),
        tool_block(TOOL, {'answers': [{'key': 'fein', 'value': '12-3456789', 'shout': True}]}, 'toolu_c'),
        tool_block(TOOL, {'answers': [], 'fields': []}, 'toolu_d'),
        tool_block(TOOL, {'answers': [{'key': 'fein', 'value': '12-3456789', 'dictated': 'maybe'}]}, 'toolu_e'),
    ]
    fake_claude.record(turn_key(WORDS, 1), content=bad)
    fake_claude.record(turn_key(WORDS, 2), content=[text_block('I could not.')])
    _chat, _message, job = services.send_message(direct, deal, text=WORDS, tab='intake')
    job.refresh_from_db()
    results = fake_claude.log[-1]['params']['messages'][-1]['content']
    assert [result['is_error'] for result in results] == [True] * 5
    said = [result['content'] for result in results]
    assert said[0] == 'answers takes a list.' and said[1] == '"boats" is not a line of coverage.'
    assert 'not shout' in said[2] and said[3].startswith('Unknown input: fields') and 'true or false' in said[4]
    assert job.result['items'] == [] and not Intake.objects.filter(deal=deal).exists()
