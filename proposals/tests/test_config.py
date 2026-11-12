"""The proposal configuration by path, and the marks it clears (plan.md §6.11; J18–J20, J59–J62; J.6.3). Pure."""

import pytest

from proposals import config, marks


def test_J20_a_write_merges_by_path_and_keeps_every_other_path():
    stored = {'title': 'Plan year 2027', 'lines': {'medical': {'rows': ['coinsurance']}}}
    merged, diff = config.merge(stored, {'lines.medical.table_note': '* Specialists only', 'intro': 'Hello'})
    assert merged['title'] == 'Plan year 2027' and merged['lines']['medical']['rows'] == ['coinsurance']
    assert merged['lines']['medical']['table_note'] == '* Specialists only' and merged['intro'] == 'Hello'
    assert diff == {'lines.medical.table_note': ['', '* Specialists only'], 'intro': ['', 'Hello']}
    assert stored == {'title': 'Plan year 2027', 'lines': {'medical': {'rows': ['coinsurance']}}}  # left as it was


def test_J20_an_unchanged_write_changes_nothing_and_a_default_unsets_the_path():
    stored = {'title': 'Plan year 2027', 'lines': {'dental': {'parts': {'cost': False}}}}
    assert config.merge(stored, {'title': '  Plan year 2027  '})[1] == {}
    merged, diff = config.merge(stored, {'lines.dental.parts.cost': True, 'title': ''})
    assert merged == {} and diff == {'lines.dental.parts.cost': [False, True], 'title': ['Plan year 2027', '']}


@pytest.mark.parametrize(
    ('path', 'value', 'stored'),
    [
        ('title', 'x' * 400, 'x' * 300),
        ('reasons.medical', '  Why  ', 'Why'),
        ('lines.medical.rows', ['coinsurance', 'nope', 'coinsurance', 'sl_lasers'], ['coinsurance']),
        ('lines.medical.rows', [], []),  # "show no benefit rows" is a real answer
        ('lines.medical.card_stats', ['pcp_copay', 'a', 'b', 'c'], ['pcp_copay']),
        ('lines.medical.card_stats', [], None),  # an empty pick is the standard set again
        ('lines.medical.table_note', ' one  line \n\n two \n3\n4\n5', 'one line\ntwo\n3\n4'),
        ('order', ['dental', 'medical', 'dental'], ['dental', 'medical']),
        (
            'next_steps',
            [{'date': '2027-01-01', 'text': ' Sign '}, {'text': ''}],
            [{'date': '2027-01-01', 'text': 'Sign'}],
        ),
    ],
)
def test_J59_J62_each_path_is_cleaned_on_its_own(path, value, stored):
    assert config.clean(path, value) == (path, stored)


@pytest.mark.parametrize(
    ('path', 'value'),
    [
        ('colour', 'red'),
        ('lines.nope.rows', []),
        ('reasons.nope', 'x'),
        ('lines.medical.parts.cost', 'yes'),
        ('lines.medical.parts.unknown', True),
        ('lines.medical.rows', 'coinsurance'),
        ('order', ['nope']),
        ('output.layout', 'sideways'),
        ('next_steps', [{'date': 'tomorrow', 'text': 'Sign'}]),
    ],
)
def test_J20_a_bad_path_or_value_is_refused_with_a_sentence(path, value):
    with pytest.raises(config.Invalid) as refused:
        config.clean(path, value)
    assert refused.value.message.endswith('.')


def test_J19_each_path_belongs_to_one_card():
    assert config.card_of('title') == ('cover', None)
    assert config.card_of('reasons.dental') == ('quotes', 'dental')
    assert config.card_of('lines.dental.table_note') == ('rows', 'dental')
    assert config.card_of('order') is None


def test_J18_J19_marks_count_the_cards_on_screen_and_an_edit_clears_only_its_own():
    stamp = {'by': 'Pat', 'at': '2026-11-12T10:00:00'}
    stored = {'cover': stamp, 'lines': {'medical': {'quotes': stamp, 'rows': stamp}, 'dental': {'quotes': stamp}}}
    assert marks.done(stored, ['medical', 'dental']) == {'done': 3, 'total': 4}  # the cover card is not on screen yet
    assert marks.line_done(stored, 'medical') and not marks.line_done(stored, 'dental')
    owners = {('rows', 'medical'), ('rows', 'dental')}
    assert marks.cleared_by(stored, owners) == ['marks.lines.medical.rows']  # dental's rows card was never marked
