"""The board's config (plan.md §6.7; F18–F28, Q.9 row 10): `board.clean_config` takes a saved setup or a patch, checks
every key against the board's lists and refuses what the board has no control for. Pure."""

import pytest

from quotes import board


def test_F28_a_config_with_nothing_set_is_the_defaults():
    config = board.clean_config({})
    assert config == board.defaults()
    assert config['find'] == '' and config['rules'] == [] and config['budget_pct'] is None
    assert config['sort'] == {'key': 'proposal', 'dir': 1} and config['layout'] == 'rows'


def test_F28_defaults_are_fresh_each_time():
    board.defaults()['rules'].append({'key': 'total'})
    assert board.defaults()['rules'] == []


def test_F28_a_whole_setup_comes_back_cleaned():
    raw = {
        'find': '  UHC hdhp ',
        'budget_pct': '-10',
        'rules': [
            {'key': 'total', 'op': '≤', 'value': '$45,000', 'line': 'medical'},
            {'key': 'diagnostic_test', 'op': 'excludes', 'value': ' not covered '},
        ],
        'sliders': {'deductible_single': '3,000', 'den_annual_max': 1500},
        'ee_rate_max': '600',
        'copay_max': None,
        'hide': ['noncompliant', 'incomplete', 'noncompliant'],
        'starred_only': True,
        'needs_check': False,
        'to_review': True,
        'carriers': ['Cigna', ' Cigna ', 'UnitedHealthcare'],
        'preset': 'rates',
        'sort': {'key': 'total', 'dir': -1},
        'layout': 'cols',
    }
    assert board.clean_config(raw) == {
        'find': 'UHC hdhp',
        'budget_pct': -10,
        'rules': [
            {'key': 'total', 'op': '<=', 'value': 45000, 'line': 'medical'},
            {'key': 'diagnostic_test', 'op': 'excludes', 'value': 'not covered'},
        ],
        'sliders': {'deductible_single': 3000, 'den_annual_max': 1500},
        'ee_rate_max': 600,
        'copay_max': None,
        'hide': ['incomplete', 'noncompliant'],
        'starred_only': True,
        'needs_check': False,
        'to_review': True,
        'carriers': ['Cigna', 'UnitedHealthcare'],
        'preset': 'rates',
        'sort': {'key': 'total', 'dir': -1},
        'layout': 'cols',
    }


@pytest.mark.parametrize(
    'raw, key',
    [
        ({'network': 'Open Access'}, 'network'),  # the old finder key: not a board setting any more
        ({'pick': {'plan_ids': [1]}}, 'pick'),  # Claude's pick names plans and is never saved (F25)
        ({'budget_pct': 12}, 'budget_pct'),
        ({'budget_pct': True}, 'budget_pct'),
        ({'rules': [{'key': 'total', 'op': 'contains', 'value': 'x'}]}, 'rules'),
        ({'rules': [{'key': 'network', 'op': '<', 'value': 5}]}, 'rules'),
        ({'rules': [{'key': 'secret', 'op': '<', 'value': 5}]}, 'rules'),
        ({'rules': [{'key': 'total', 'op': '<=', 'value': '$25 – $135'}]}, 'rules'),
        ({'rules': [{'key': 'total', 'op': '<=', 'value': 1, 'line': 'boats'}]}, 'rules'),
        ({'rules': [{'key': 'total', 'op': '<=', 'value': 1, 'why': 'x'}]}, 'rules'),
        ({'rules': [{'key': 'total', 'op': '<', 'value': n} for n in range(9)]}, 'rules'),
        ({'sliders': {'rate_ee': 500}}, 'sliders'),
        ({'sliders': {'deductible_single': -50}}, 'sliders'),
        ({'ee_rate_max': 'cheap'}, 'ee_rate_max'),
        ({'hide': ['sold']}, 'hide'),
        ({'starred_only': 'yes'}, 'starred_only'),
        ({'carriers': 'Cigna'}, 'carriers'),
        ({'preset': 'everything'}, 'preset'),
        ({'sort': {'key': 'nope', 'dir': 1}}, 'sort'),
        ({'sort': {'key': 'total', 'dir': 2}}, 'sort'),
        ({'layout': 'grid'}, 'layout'),
        ({'find': 'x' * 121}, 'find'),
    ],
)
def test_F24_F28_clean_config_refuses_what_the_board_has_no_control_for(raw, key):
    with pytest.raises(board.ConfigError) as refused:
        board.clean_config(raw)
    assert set(refused.value.errors) == {key}
    assert refused.value.errors[key].endswith('.')


def test_F24_rules_collapse_repeats_and_number_ops_read_numbers():
    rules = board.clean_config(
        {
            'rules': [
                {'key': 'deductible_single', 'op': '<', 'value': '2,000'},
                {'key': 'deductible_single', 'op': '<', 'value': 2000},
            ]
        }
    )['rules']
    assert rules == [{'key': 'deductible_single', 'op': '<', 'value': 2000}]


def test_F24_a_patch_cleans_only_the_keys_it_names():
    assert board.clean_config({'find': 'Aetna', 'preset': 'rx'}, partial=True) == {'find': 'Aetna', 'preset': 'rx'}


def test_F29_stop_loss_settings_take_their_four_controls_and_nothing_else():
    assert board.clean_config({}, view='stop-loss') == {
        'rank_by': 'max_annual_liability',
        'annual_mode': False,
        'show_terms': True,
        'hide_unscored': False,
    }
    assert board.clean_config({'annual_mode': True}, view='stop-loss', partial=True) == {'annual_mode': True}
    with pytest.raises(board.ConfigError) as refused:
        board.clean_config({'rank_by': 'total', 'show_terms': 'yes', 'without': [1]}, view='stop-loss')
    assert set(refused.value.errors) == {'rank_by', 'show_terms', 'without'}  # the what-if is never saved (F104)


def test_F29_a_view_without_a_board_is_refused():
    with pytest.raises(board.ConfigError) as refused:
        board.clean_config({}, view='census-review')
    assert set(refused.value.errors) == {'view'}
