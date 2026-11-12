"""What a person chose to use from a quote read's change set (plan.md §10.5; D28, D31, D67, D115, D117). Pure."""

import pytest
from rest_framework.exceptions import ValidationError

from quotes.reader.choice import choose


def value(key, tick=True):
    return {'key': key, 'new': '1', 'old': '', 'tick': tick}


CHANGE_SET = {
    'items': [
        {'id': 'i1', 'op': 'create_plan', 'tick': True, 'values': [value('rate_ee'), value('rate_es', tick=False)]},
        {
            'id': 'i2',
            'op': 'create_plan',
            'tick': True,
            'values': [],
            'replaces': {'to': [{'plan': 7}], 'tick': False},
        },
        {
            'id': 'i3',
            'op': 'pick_current',
            'tick': False,
            'values': [value('rate_ee')],
            'options': [{'plan': 7, 'label': 'A'}, {'plan': 9, 'label': 'B'}],
            'carrier': 'Harbor',
            'name': 'PPO',
        },
        {'id': 'i4', 'op': 'summary_counts', 'tick': False, 'counts': {'EE': 1}},
        {'id': 'i5', 'op': 'set_values', 'tick': True, 'stale': True, 'values': [value('rate_ee')]},
    ]
}


def test_D28_use_this_scan_takes_the_read_as_proposed():
    chosen = choose(CHANGE_SET)
    assert [entry.item['id'] for entry in chosen] == ['i1', 'i2']  # no counts, no pick, nothing stale
    assert [v['key'] for v in chosen[0].values] == ['rate_ee'] and chosen[1].replaces is False


def test_D31_D67_apply_selected_takes_what_is_ticked_values_and_links_included():
    chosen = choose(CHANGE_SET, select=['i1', 'i1:rate_es', 'i2:replaces', 'i2', 'i4'])
    assert [entry.item['id'] for entry in chosen] == ['i1', 'i2', 'i4']
    assert [v['key'] for v in chosen[0].values] == ['rate_ee', 'rate_es']
    assert chosen[1].replaces is True


def test_D117_a_pick_goes_where_the_person_says_and_to_the_first_plan_named_by_default():
    assert choose(CHANGE_SET, select=['i3'])[0].pick == 7
    assert choose(CHANGE_SET, select=['i3'], picks={'i3': '9'})[0].pick == 9
    assert choose(CHANGE_SET, select=['i3'], picks={'i3': 'new'})[0].pick == 'new'
    with pytest.raises(ValidationError):
        choose(CHANGE_SET, select=['i3'], picks={'i3': 8})  # not a plan the read named


@pytest.mark.parametrize('select', [['i9'], 'i1', [1], []])
def test_D31_a_bad_selection_is_a_400(select):
    with pytest.raises(ValidationError):
        choose(CHANGE_SET, select=select)
