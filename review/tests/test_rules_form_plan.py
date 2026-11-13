"""The Ask card's plan (plan.md §5.8; L42, L59; old 891f1b3 `link_form._apply`, `client_request.shrink`/`widen`): pure,
table by table — removals, what is switched on, what the drafts add, and what cannot come off alone."""

import pytest

from review.rules import form_plan
from review.rules.join import TooMany


def change(**kw):
    data = {'off': kw.pop('off', {}), 'on': kw.pop('on', {})}
    found, errors = form_plan.parse(data)
    assert not errors, errors
    return found


def plan(asks, **kw):
    add = kw.pop('add', ())
    carried = kw.pop('carried', frozenset())
    columns = kw.pop('columns', ())
    return form_plan.plan(asks, change(**kw), add=add, carried=carried, columns=columns)


PICKED = {'intake': {'scope': 'selected', 'keys': ['fein', 'dba'], 'blocks': ['bor']}, 'census': {'scope': 'none'}}


def test_L59_a_picked_question_comes_off_and_the_rest_stays():
    found = plan(PICKED, off={'refs': ['intake:fein']}, carried={'intake:fein', 'intake:dba'})
    assert found.asks['intake'] == {'scope': 'selected', 'keys': ['dba'], 'blocks': ['bor']}
    assert (found.removed, found.refused, found.changed) == (['intake:fein'], [], True)


def test_L59_a_question_a_scope_carries_cannot_come_off_alone():
    asks = {'intake': {'scope': 'missing', 'keys': [], 'blocks': []}}
    found = plan(asks, off={'refs': ['intake:fein']}, carried={'intake:fein'})
    assert found.refused == ['intake:fein']


def test_L59_a_question_no_scope_carries_comes_off_quietly():
    asks = {'intake': {'scope': 'missing', 'keys': [], 'blocks': []}}
    found = plan(asks, off={'refs': ['intake:fein']}, carried=set())
    assert (found.refused, found.removed, found.changed) == ([], [], False)


def test_L59_the_last_picked_question_takes_the_intake_off_unless_a_part_stays():
    found = plan(PICKED, off={'refs': ['intake:fein', 'intake:dba', 'intake:block:bor']},
                 carried={'intake:fein', 'intake:dba', 'intake:block:bor'})  # fmt: skip
    assert found.asks['intake'] is None
    found = plan(PICKED, off={'refs': ['intake:fein', 'intake:dba']}, carried={'intake:fein', 'intake:dba'})
    assert found.asks['intake'] == {'scope': '', 'keys': [], 'blocks': ['bor']}


@pytest.mark.parametrize(
    ('part', 'gone'),
    [
        ('intake', lambda asks: asks['intake'] is None),
        ('census', lambda asks: asks['census'] == {'scope': 'none', 'columns': [], 'cells': [], 'file': False}),
        ('documents', lambda asks: asks['documents'] == {'slots': [], 'missing': False}),
    ],
)
def test_L42_a_part_switched_off_goes_whole(part, gone):
    asks = {
        'intake': {'scope': 'all', 'keys': [], 'blocks': ['contacts']},
        'census': {'scope': 'missing', 'columns': [], 'cells': [[4, 'dob']], 'file': True},
        'documents': {'slots': ['claims'], 'missing': True},
    }
    found = plan(asks, off={'parts': [part]})
    assert gone(found.asks) and found.changed


def test_L42_a_census_column_comes_off_a_scope_that_asked_them_all():
    asks = {'census': {'scope': 'blank', 'columns': [], 'cells': [[4, 'zip']], 'file': False}}
    found = plan(asks, off={'columns': ['zip']}, columns=['dob', 'zip', 'gender'])
    assert found.asks['census'] == {'scope': 'blank', 'columns': ['dob', 'gender'], 'cells': [], 'file': False}


def test_L42_the_last_census_column_off_leaves_no_census_ask():
    asks = {'census': {'scope': 'missing', 'columns': ['dob'], 'cells': [], 'file': False}}
    assert plan(asks, off={'columns': ['dob']}).asks['census']['scope'] == 'none'


def test_L42_switching_parts_on_and_the_drafts_join():
    asks = {'intake': None, 'census': {'scope': 'none', 'columns': [], 'cells': [], 'file': False}}
    found = plan(
        asks,
        on={
            'intake': 'required',
            'census': 'missing',
            'census_file': True,
            'documents_missing': True,
            'blocks': ['bor'],
        },  # fmt: skip
        add=['intake:dba', 'doc:claims'],
    )
    assert found.asks['intake'] == {'scope': 'required', 'keys': ['dba'], 'blocks': ['bor']}
    assert found.asks['census']['scope'] == 'missing' and found.asks['census']['file'] is True
    assert found.asks['documents'] == {'slots': ['claims'], 'missing': True}
    assert found.added == ['intake:dba', 'doc:claims']


def test_L42_a_column_ticked_on_asks_its_blanks():
    asks = {'census': {'scope': 'none', 'columns': [], 'cells': [], 'file': False}}
    assert plan(asks, on={'columns': ['dob']}).asks['census'] == {
        'scope': 'blank', 'columns': ['dob'], 'cells': [], 'file': False,
    }  # fmt: skip


def test_L42_the_whole_intake_drops_the_picked_keys():
    found = plan(PICKED, on={'intake': 'all'})
    assert found.asks['intake'] == {'scope': 'all', 'keys': [], 'blocks': ['bor']}


def test_L46_too_many_census_values_is_refused():
    with pytest.raises(TooMany):
        plan({}, add=[f'census:{n}:dob' for n in range(501)])


@pytest.mark.parametrize(
    ('body', 'field'),
    [
        ({'off': {'parts': ['everything']}}, 'off.parts'),
        ({'on': {'intake': 'selected'}}, 'on.intake'),
        ({'on': {'census': 'none'}}, 'on.census'),
        ({'off': {'columns': ['not_a_column']}}, 'columns'),
        ({'on': {'census_file': 'yes'}}, 'on.census_file'),
        ({'off': {'refs': 'intake:fein'}}, 'off.refs'),
    ],
)
def test_L42_a_bad_body_is_refused_by_field(body, field):
    _change, errors = form_plan.parse(body)
    assert field in errors


def test_L42_a_settings_only_body_touches_no_form():
    assert not form_plan.touches(change())
    assert form_plan.touches(change(on={'census_file': False}))
