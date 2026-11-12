"""The form's rules (plan.md §4.5, §5.2; B2, B6, B9): the seven shown-when rules, the one `needed` rule behind the star
and "Missing", readiness's share, statuses and the two notes. Pure: no database."""

import pytest

from intake import form, status, values


@pytest.mark.parametrize(
    ('key', 'shows', 'hides'),
    [
        ('waive_reason', {'waiving_count': '1'}, [{}, {'waiving_count': '0'}, {'waiving_count': 'some'}]),
        ('locations_list', {'multi_location': 'Yes'}, [{}, {'multi_location': 'No'}]),
        ('section_125_handler', {'section_125': 'Yes'}, [{}, {'section_125': 'No'}]),
        ('form_5500_handler', {'form_5500_required': 'Yes'}, [{}, {'form_5500_required': 'No'}]),
        ('aca_1095c_handler', {'aca_1095c': 'Yes'}, [{}, {'aca_1095c': 'No'}]),
        ('aca_1095b_handler', {'aca_1095b': 'Yes'}, [{}, {'aca_1095b': 'No'}]),
        ('pcori_handler', {'pcori_filing': 'Yes'}, [{}, {'pcori_filing': 'No'}]),
    ],
)
def test_B2_each_shown_when_rule(key, shows, hides):
    assert values.shown(key, shows)
    for answers in hides:
        assert not values.shown(key, answers), answers
    assert key in values.hidden({}) and key not in values.hidden(shows)


def test_B2_seven_questions_have_a_rule_and_the_rest_always_show():
    ruled = [question['key'] for question in form.QUESTIONS if question.get('shown_when')]
    assert len(ruled) == 7
    assert set(values.hidden({})) == set(ruled)


@pytest.mark.parametrize(
    ('key', 'answers', 'rules', 'needed'),
    [
        ('legal_name', {}, {}, True),  # quote-blocking
        ('dba', {}, {}, False),  # optional
        ('waive_reason', {}, {}, False),  # conditional, hidden
        ('waive_reason', {'waiving_count': '3'}, {}, True),  # conditional, shown
        ('dba', {}, {'dba': 'required'}, True),
        ('fein', {}, {'fein': 'waived'}, False),
        ('fein', {}, {'fein': {'state': 'waived', 'note': 'Not a US company'}}, False),
        ('waive_reason', {}, {'waive_reason': 'required'}, False),  # hidden wins over Required
        ('fein', {}, {'fein': 'auto'}, True),
    ],
)
def test_B6_one_needed_rule(key, answers, rules, needed):
    assert values.needed(key, answers, rules) is needed


def test_B6_eight_questions_are_needed_on_a_blank_deal():
    assert values.needed_keys({}) == [question['key'] for question in form.QUESTIONS if question['need'] == 'Q']
    assert len(values.needed_keys({})) == 8


def test_B6_readiness_counts_answered_needed_questions():
    needed = values.needed_keys({})
    assert values.readiness({}, needed) == {'needed': 8, 'answered': 0, 'pct': 0}
    answers = {'legal_name': 'Example', 'fein': '12-3456789', 'states_operating': ['FL'], 'dba': 'Ex'}
    assert values.readiness(answers, needed) == {'needed': 8, 'answered': 3, 'pct': 38}
    assert values.readiness({}, []) == {'needed': 0, 'answered': 0, 'pct': 100}


def test_B6_statuses_name_missing_and_to_check_only():
    answers = {'legal_name': 'Example', 'dba': 'Ex', 'union': 'No'}
    sources = {
        'legal_name': {'origin': 'typed'},
        'dba': {'origin': 'ai', 'low': 'two names on the page'},
        'union': {'origin': 'typed', 'mark': {'state': 'check', 'by': 1, 'at': '2026-11-11T10:00:00Z'}},
    }
    needed = values.needed_keys(answers)
    found = status.statuses(answers, sources, needed, values.hidden(answers), pending={'sic_code'})
    assert found['dba'] == found['union'] == 'to_check'
    assert found['fein'] == 'missing' and 'legal_name' not in found
    assert 'sic_code' not in found  # a client answer waits on it
    assert 'waive_reason' not in found  # hidden
    assert status.flags(answers, sources, values.hidden(answers)) == 2


@pytest.mark.parametrize(
    ('answers', 'multi'),
    [
        ({}, False),
        ({'states_operating': ['FL']}, False),
        ({'states_operating': ['FL', 'GA']}, True),
        ({'location_count': '1'}, False),
        ({'location_count': '2'}, True),
        ({'location_count': 'two'}, False),
    ],
)
def test_B9_multi_state_note(answers, multi):
    assert status.notes(answers, [])['multi_state'] is multi


def test_B9_salary_note_follows_life_and_disability_lines():
    assert status.notes({}, ['medical', 'dental'])['census'] == ''
    assert 'salary and job title' in status.notes({}, ['medical', 'ltd'])['census']


@pytest.mark.parametrize(
    ('raw', 'cleaned', 'errors'),
    [
        ({'fein': '123456789', 'union': 'y'}, {'fein': '12-3456789', 'union': 'Yes'}, {}),
        ({'fein': None}, {'fein': None}, {}),  # put back what was read
        ({'dba': ''}, {'dba': ''}, {}),
        ({'shoe_size': '9'}, {}, {'shoe_size': 'Not an intake question.'}),
        ({'dba': ['a']}, {}, {'dba': values.NOT_TEXT}),
        ({'states_operating': ['FL', 'GA']}, {'states_operating': ['FL', 'GA']}, {}),
        ({'client_guidance': '  Keep the HMO  '}, {'client_guidance': 'Keep the HMO'}, {}),
        ({'client_guidance': 'x' * 4001}, {}, {'client_guidance': values.GUIDANCE_LONG}),
    ],
)
def test_B4_clean_answers_checks_every_key(raw, cleaned, errors):
    assert values.clean_answers(raw) == (cleaned, errors)
