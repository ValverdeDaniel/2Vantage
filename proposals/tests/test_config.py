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
        ('output.package_summary', False, False),
        ('output.compare_slots', 10, 10),
        ('output.pages.team', False, False),
        ('experience.summary', '  Claims ran at 78% of premium. ', 'Claims ran at 78% of premium.'),
        (
            'experience.rows',
            [{'period': 'Jan–Dec 2025', 'premium': '$1,234,000', 'claims': '901,500.50'}, {'period': ' '}],
            [{'period': 'Jan–Dec 2025', 'premium': 1234000, 'claims': 901500.5}],
        ),
        ('summary.on', False, False),
        (
            'summary.blocks',
            [{'key': 'recommended', 'line': 'dental'}, {'key': 'nope'}, {'key': 'medicare_eligible', 'line': 'dental'}],
            [{'key': 'recommended', 'line': 'dental'}, {'key': 'medicare_eligible'}],
        ),
        ('markets.on', None, None),
        ('markets.lines.medical.notes.cigna', '  Competitive ', 'Competitive'),
        ('markets.lines.medical.hidden', ['n:eyemed', 'cigna', 'cigna'], ['cigna', 'n:eyemed']),
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
        ('output.compare_slots', 7),
        ('output.pages.history', False),
        ('output.style', 'classic'),
        ('experience.rows', [{'period': '2025', 'premium': 'lots'}]),
        ('summary.blocks', 'recommended'),
        ('markets.on', 'yes'),
        ('markets.lines.medical.notes.Not A Carrier', 'x'),
        ('markets.lines.medical.hidden', 'cigna'),
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


def test_J38_J42_J63_J64_the_deal_cards_own_their_paths():
    assert config.card_of('output.layout') == ('output', None)
    assert config.card_of('output.pages.team') == ('pages', None)
    assert config.card_of('experience.rows') == ('pages', None)
    assert config.card_of('summary.blocks') == ('summary', None)
    assert config.card_of('next_steps') == ('next_steps', None)
    assert config.card_of('markets.lines.dental.hidden') == ('markets', 'dental')
    assert config.card_of('markets.on') == ('markets', config.EVERY_LINE)  # a deal-wide switch on a line card


def test_J63_markets_show_it_takes_the_card_mark_off_every_line():
    stamp = {'by': 'Pat', 'at': '2026-11-12T10:00:00'}
    stored = {'lines': {'medical': {'markets': stamp}, 'dental': {'markets': stamp, 'rows': stamp}}}
    owners = {config.card_of('markets.on')}
    assert marks.cleared_by(stored, owners) == ['marks.lines.dental.markets', 'marks.lines.medical.markets']


def test_J18_J19_marks_count_the_cards_on_screen_and_an_edit_clears_only_its_own():
    stamp = {'by': 'Pat', 'at': '2026-11-12T10:00:00'}
    medical = {'quotes': stamp, 'rows': stamp, 'markets': stamp}
    stored = {'cover': stamp, 'pages': stamp, 'lines': {'medical': medical, 'dental': {'quotes': stamp}}}
    counted = marks.counted(['medical', 'dental'])
    assert ('cover', None) not in counted and ('pages', None) not in counted  # not on screen yet / optional
    assert marks.done(stored, ['medical', 'dental']) == {'done': 4, 'total': len(counted)}
    assert marks.line_done(stored, 'medical') and not marks.line_done(stored, 'dental')
    owners = {('rows', 'medical'), ('rows', 'dental')}
    assert marks.cleared_by(stored, owners) == ['marks.lines.medical.rows']  # dental's rows card was never marked
