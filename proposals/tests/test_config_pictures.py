"""The cover, the pictures and the team picks as proposal settings (plan.md §6.11; J34, J35, J43; J.6.2): what each
path takes, what it reads unset, which card owns it, and what a layout template holds. Pure."""

import pytest

from proposals import catalog, config, template_store
from proposals.cleaners import Invalid


def test_J34_the_cover_page_switch_and_its_upload():
    assert config.default('output.cover.on') is True
    assert config.default('output.cover.image') is None  # not True: a 3-part output path is not a switch
    assert config.clean('output.cover.on', False) == ('output.cover.on', False)
    assert config.clean('output.cover.image', 7) == ('output.cover.image', 7)
    assert config.clean('output.cover.image', None) == ('output.cover.image', None)
    for bad in ('7', True, -2, 1.5):
        with pytest.raises(Invalid):
            config.clean('output.cover.image', bad)
    assert config.card_of('output.cover.on') == ('cover', None)
    assert config.card_of('output.cover.image') == ('cover', None)
    assert config.card_of('title') == ('cover', None)


def test_J35_each_place_takes_a_stock_picture_an_upload_or_none_and_reads_its_default_unset():
    for place, _label in catalog.PICTURE_PLACES:
        assert config.default(f'output.pictures.{place}') == catalog.DEFAULT_PICTURES.get(place)
    assert config.clean('output.pictures.agenda', 'gold_lights')[1] == 'gold_lights'
    assert config.clean('output.pictures.closing', None)[1] is None
    assert config.clean('output.pictures.sections', 'upload:12')[1] == 'upload:12'
    with pytest.raises(Invalid):
        config.clean('output.pictures.cover', 'upload:12')  # the cover's upload is output.cover.image
    with pytest.raises(Invalid):
        config.clean('output.pictures.agenda', 'asset:logos/mark.png')
    with pytest.raises(Invalid):
        config.clean('output.pictures.hallway', 'gold_lights')
    assert config.card_of('output.pictures.agenda') == ('pictures', None)


def test_J35_a_place_left_at_its_default_is_not_stored_and_none_is():
    stored, diff = config.merge({}, {'output.pictures.cover': None, 'output.pictures.agenda': None})
    assert diff == {'output.pictures.cover': ['blue_light', None]}  # agenda's default is already none
    assert stored == {'output': {'pictures': {'cover': None}}}
    assert config.output(stored)['pictures'] == {
        'cover': None,
        'agenda': None,
        'sections': None,
        'closing': 'at_the_table',
    }
    back, _diff = config.merge(stored, {'output.pictures.cover': 'blue_light'})
    assert back == {}


def test_J43_team_picks_are_member_ids_in_order_or_null_for_the_firm_default():
    assert config.default('team') is None
    assert config.clean('team', [3, 1, 3])[1] == [3, 1]
    assert config.clean('team', [])[1] == []  # nobody: the team page prints nothing
    assert config.clean('team', None)[1] is None
    for bad in ('3', [0], ['3'], [True]):
        with pytest.raises(Invalid):
            config.clean('team', bad)
    assert config.card_of('team') == ('pages', None)


def test_J34_J35_the_output_read_carries_the_cover_and_pictures():
    found = config.output({'output': {'cover': {'on': False, 'image': 4}}})
    assert found['cover'] == {'on': False, 'image': 4}
    assert found['pictures']['cover'] == 'blue_light'


def test_J68_a_layout_template_holds_every_output_path_and_vantage_default_is_the_defaults():
    (default,) = template_store.built_in('layout')
    assert set(default['config']) == set(config.output_paths())
    assert all(config.default(path) == value for path, value in default['config'].items())
    cleaned = template_store.clean_config('layout', {'output.layout': 'side_by_side', 'title': 'Not a look'})
    assert cleaned['output.layout'] == 'side_by_side' and 'title' not in cleaned
    assert cleaned['output.cover.on'] is True  # an absent path is its default
    assert template_store.clean_config('layout', {'output.layout': 'sideways'})['output.layout'] == 'by_carrier'
    assert template_store.built_in('rows') == [] and template_store.built_in('summary') == []


def test_J68_rows_and_summary_templates_hold_their_own_paths():
    rows = template_store.clean_config('rows', {'rows': ['coinsurance', 'coinsurance', 'nope'], 'x': 1}, 'medical')
    assert rows == {'rows': ['coinsurance'], 'card_stats': None}
    anywhere = template_store.clean_config('rows', {'rows': ['coinsurance', 'den_ortho'], 'card_stats': []})
    assert anywhere == {'rows': ['coinsurance', 'den_ortho'], 'card_stats': None}  # each line drops what it lacks
    summary = template_store.clean_config('summary', {'summary.on': False, 'summary.blocks': [{'key': 'nope'}]})
    assert summary == {'summary.on': False, 'summary.blocks': []}
