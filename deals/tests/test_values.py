"""values.apply, the only writer of values and their sources (plan.md §3.7, O.3.1; A31, A33, E66, F141)."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest import mock

import pytest

from deals import clock, values

NOW = datetime(2026, 11, 20, 15, 4, 40, tzinfo=UTC)
AT, EARLIER = NOW.isoformat(), '2026-11-19T10:00:00+00:00'
PERSON = SimpleNamespace(id=7)
LINE = 'Deductible $3,300 / $6,600'
MARK = {'state': 'check', 'by': 5, 'at': EARLIER}
CONFIRMED = {'by': 5, 'at': EARLIER, 'via': 'recheck'}
LOC = {'state': 'found', 'page': 2, 'hits': 1, 'printed': '$3,300', 'v': 3, 'at': EARLIER}
READ = {
    'origin': 'ai',
    'by': None,
    'at': EARLIER,
    'doc': 41,
    'page': 2,
    'line': LINE,
    'low': 'two figures for one tier',
    'loc': LOC,
    'mark': MARK,
    'confirmed': CONFIRMED,
    'read_value': '3300',
}
TYPED_OVER_READ = {'origin': 'typed', 'by': 7, 'at': EARLIER, 'doc': 41, 'page': 2, 'line': LINE, 'read_value': '3300'}
IMPORTED = {'origin': 'import', 'by': 3, 'at': EARLIER, 'doc': 9, 'cell': 'Medical!D12'}
OLD_TYPED = {'origin': 'typed', 'by': 3, 'at': EARLIER, 'mark': MARK, 'confirmed': CONFIRMED}
NEW_READ = {'origin': 'ai', 'by': None, 'at': AT, 'doc': 50, 'page': 1, 'read_value': '3600'}


def typed():
    return values.source('typed', PERSON)


# (stored value, stored source, write, entry for the write, value after, source after, before/after returned)
TABLE = {
    'a new value gets its source': (
        None,
        None,
        '25',
        typed,
        '25',
        {'origin': 'typed', 'by': 7, 'at': AT},
        [None, '25'],
    ),
    'an unchanged value writes nothing, not even its source': ('25', OLD_TYPED, '25', typed, '25', OLD_TYPED, None),
    'a changed value replaces its source, dropping mark and confirmed': (
        '25',
        OLD_TYPED,
        '30',
        typed,
        '30',
        {'origin': 'typed', 'by': 7, 'at': AT},
        ['25', '30'],
    ),
    "'' clears the value and its source": ('25', OLD_TYPED, '', typed, None, None, ['25', None]),
    "'' on no value writes nothing": (None, None, '', typed, None, None, None),
    'a typed value over a read one keeps doc, page, line and read_value; drops low and loc (E66, F141)': (
        '3300',
        READ,
        '3500',
        typed,
        '3500',
        {'origin': 'typed', 'by': 7, 'at': AT, 'doc': 41, 'page': 2, 'line': LINE, 'read_value': '3300'},
        ['3300', '3500'],
    ),
    'a typed value over an import keeps its file and cell': (
        '1500',
        IMPORTED,
        '2000',
        typed,
        '2000',
        {'origin': 'typed', 'by': 7, 'at': AT, 'doc': 9, 'cell': 'Medical!D12'},
        ['1500', '2000'],
    ),
    'a typed value over a typed-over-read one still keeps the file': (
        '3500',
        TYPED_OVER_READ,
        '3700',
        typed,
        '3700',
        {**TYPED_OVER_READ, 'at': AT},
        ['3500', '3700'],
    ),
    'a new read replaces the whole entry': (
        '3500',
        TYPED_OVER_READ,
        '3600',
        NEW_READ,
        '3600',
        NEW_READ,
        ['3500', '3600'],
    ),
    'None puts back the read value with its file (A33)': (
        '3500',
        TYPED_OVER_READ,
        None,
        typed,
        '3300',
        {'origin': 'ai', 'by': None, 'at': AT, 'doc': 41, 'page': 2, 'line': LINE, 'read_value': '3300'},
        ['3500', '3300'],
    ),
    'None without a read value writes nothing': ('25', OLD_TYPED, None, typed, '25', OLD_TYPED, None),
    'None on the read value itself writes nothing': ('3300', READ, None, typed, '3300', READ, None),
    'None on no value writes nothing': (None, None, None, typed, None, None, None),
}


@pytest.mark.parametrize('case', TABLE.values(), ids=TABLE.keys())
def test_A31_A33_values_apply_table(case):
    stored, stored_source, write, entry, value_after, source_after, returned = case
    data = {} if stored is None else {'k': stored}
    sources = {} if stored_source is None else {'k': dict(stored_source)}
    with mock.patch.object(clock, 'now', return_value=NOW):
        changed = values.apply(data, sources, {'k': write}, entry() if callable(entry) else entry)
    assert data.get('k') == value_after
    assert sources.get('k') == source_after
    assert changed == ({'k': returned} if returned else {})


def test_A31_a_source_per_key_and_only_the_changed_keys_return():
    data, sources = {'a': '1', 'b': '2'}, {'a': {'origin': 'typed'}, 'b': {'origin': 'typed'}}
    changed = values.apply(data, sources, {'a': '1', 'b': '3', 'c': '4'}, lambda key: values.source('import', cell=key))
    assert changed == {'b': ['2', '3'], 'c': [None, '4']}
    assert sources['a'] == {'origin': 'typed'}
    assert (sources['b']['cell'], sources['c']['cell']) == ('b', 'c')


def test_A31_the_source_entry_has_one_shape():
    entry = values.source('ai', None, doc=4, page=1, line='x' * 400, low=None)
    assert set(entry) == {'origin', 'by', 'at', 'doc', 'page', 'line'}
    assert len(entry['line']) == values.LINE_LIMIT
    with pytest.raises(ValueError):
        values.source('guessed')
    with pytest.raises(ValueError):
        values.source('typed', note='not a source key')


# ---- set_loc: the locator's answer on an entry (slice 16; E83) ------------------------------------------------------
FOUND_P3 = {'state': 'found', 'page': 3, 'hits': 1, 'v': 1, 'at': AT}


def test_E83_set_loc_stores_the_answer_and_keeps_everything_else():
    vals, srcs = {'deductible_single': '3300'}, {'deductible_single': dict(READ)}
    assert values.set_loc(vals, srcs, 'deductible_single', '3300', 41, FOUND_P3)
    assert srcs['deductible_single'] == {**READ, 'loc': FOUND_P3}
    assert vals == {'deductible_single': '3300'}


@pytest.mark.parametrize(
    'value, doc',
    [('3400', 41), ('3300', 42)],  # the value changed while its file was searched, or it names another file now
)
def test_E83_set_loc_writes_nothing_about_an_old_value(value, doc):
    vals, srcs = {'deductible_single': '3300'}, {'deductible_single': dict(READ)}
    assert not values.set_loc(vals, srcs, 'deductible_single', value, doc, FOUND_P3)
    assert srcs['deductible_single'] == READ


def test_E83_the_same_answer_again_writes_nothing():
    vals, srcs = {'deductible_single': '3300'}, {'deductible_single': {**READ, 'loc': FOUND_P3}}
    later = {**FOUND_P3, 'at': '2026-11-21T10:00:00+00:00'}
    assert not values.set_loc(vals, srcs, 'deductible_single', '3300', 41, later)
    assert srcs['deductible_single']['loc']['at'] == AT
