"""documents.review_rules, the one set of review rules (plan.md §10.7; E85–E92, D122, OQ28). Pure: no database."""

import pytest

from deals.values import apply, source
from documents import review_rules as rules

AT, LATER = '2026-11-11T15:00:00+00:00', '2026-11-12T09:00:00+00:00'
ME, YOU = 5, 7

READ = {'origin': 'ai', 'by': None, 'at': AT, 'doc': 3, 'page': 2}
DOUBTED = {**READ, 'low': 'two figures for one tier'}
APPROVED = {**DOUBTED, 'confirmed': {'by': YOU, 'at': AT}}
IGNORED = {**DOUBTED, 'mark': {'state': 'ignored', 'by': YOU, 'at': AT}}
FLAGGED = {**READ, 'mark': {'state': 'check', 'by': YOU, 'at': AT}}
BOTH = {**DOUBTED, 'confirmed': {'by': YOU, 'at': AT}, 'mark': {'state': 'check', 'by': YOU, 'at': AT}}
PRIORS = {'blank': None, 'unmarked': DOUBTED, 'approved': APPROVED, 'ignored': IGNORED, 'check': FLAGGED, 'both': BOTH}

MINE = {'by': ME, 'at': LATER}
# (prior, action) → the marks after, or None when nothing changes. Every action against every prior state (Q.9 17).
EXPECTED = {
    ('blank', 'approve'): None,
    ('blank', 'ignore'): None,
    ('blank', 'check'): None,
    ('blank', 'clear'): None,
    ('unmarked', 'approve'): {'confirmed': MINE},
    ('unmarked', 'ignore'): {'mark': {'state': 'ignored', **MINE}},
    ('unmarked', 'check'): {'mark': {'state': 'check', **MINE}},
    ('unmarked', 'clear'): None,
    ('approved', 'approve'): None,
    ('approved', 'ignore'): {'mark': {'state': 'ignored', **MINE}},
    ('approved', 'check'): {'mark': {'state': 'check', **MINE}},
    ('approved', 'clear'): None,
    ('ignored', 'approve'): {'confirmed': MINE},
    ('ignored', 'ignore'): None,
    ('ignored', 'check'): {'mark': {'state': 'check', **MINE}},
    ('ignored', 'clear'): {},
    ('check', 'approve'): {'confirmed': MINE},
    ('check', 'ignore'): {'mark': {'state': 'ignored', **MINE}},
    ('check', 'check'): None,
    ('check', 'clear'): {},
    ('both', 'approve'): {'confirmed': MINE},
    ('both', 'ignore'): {'mark': {'state': 'ignored', **MINE}},
    ('both', 'check'): {'mark': {'state': 'check', **MINE}},
    ('both', 'clear'): {'confirmed': {'by': YOU, 'at': AT}},
}


@pytest.mark.parametrize(('prior', 'action'), sorted(EXPECTED))
def test_E85_every_action_against_every_prior_state(prior, action):
    entry = PRIORS[prior]
    after = rules.apply_mark(entry, action, ME, LATER)
    expected = EXPECTED[(prior, action)]
    if expected is None:
        assert after is None
        return
    assert (rules.marks_of(after) or {}) == expected
    # The value's own facts ride along untouched: a mark never changes where the value came from.
    assert {k: v for k, v in after.items() if k not in rules.MARK_KEYS} == {
        k: v for k, v in entry.items() if k not in rules.MARK_KEYS
    }


def test_E85_unknown_action_is_refused():
    with pytest.raises(ValueError):
        rules.apply_mark(DOUBTED, 'confirm', ME, LATER)


def test_E85_a_changed_value_drops_its_marks_and_a_typed_change_keeps_its_file():
    values, sources = {'rate_ee': '512.34'}, {'rate_ee': dict(APPROVED)}
    apply(values, sources, {'rate_ee': '515.00'}, source('typed'))
    entry = sources['rate_ee']
    assert rules.marks_of(entry) is None and not rules.open_warning(entry)
    assert entry['doc'] == 3 and entry['page'] == 2 and 'low' not in entry


OPEN = [
    ('a read value Claude did not doubt', READ, False),
    ('a read value Claude doubted', DOUBTED, True),
    ('a read value the locator could not find', {**READ, 'loc': {'state': 'absent'}}, True),
    ('a read value the locator could not pin down', {**READ, 'loc': {'state': 'weak'}}, True),
    ('a read value the file cannot settle', {**READ, 'loc': {'state': 'nocheck', 'why': 'image'}}, False),
    ('a read value found in its file', {**READ, 'loc': {'state': 'found', 'page': 2}}, False),
    ('a doubted value a person approved', APPROVED, False),
    ('a doubted value a person ignored', IGNORED, False),
    ('any value a person flagged', {'origin': 'typed', 'mark': {'state': 'check', 'by': YOU, 'at': AT}}, True),
    ('a typed value the locator could not find', {'origin': 'typed', 'doc': 3, 'loc': {'state': 'absent'}}, False),
    ('an imported value the locator could not find', {'origin': 'import', 'doc': 3, 'loc': {'state': 'absent'}}, False),
    ('no entry', None, False),
]


@pytest.mark.parametrize(('why', 'entry', 'expected'), OPEN, ids=[row[0] for row in OPEN])
def test_OQ28_only_values_claude_doubted_or_could_not_find_need_review(why, entry, expected):
    assert rules.open_warning(entry) is expected


def test_E50_potential_errors_add_any_value_the_file_does_not_print():
    typed_absent = {'origin': 'typed', 'doc': 3, 'loc': {'state': 'absent'}}
    assert rules.potential_error(typed_absent) and not rules.open_warning(typed_absent)
    assert not rules.potential_error({**typed_absent, 'confirmed': {'by': YOU, 'at': AT}})
    assert rules.potential_error(DOUBTED) and not rules.potential_error(READ)


def test_E92_an_approval_shows_only_where_it_settles_a_doubt():
    assert rules.shows_approval(APPROVED)
    assert rules.shows_approval({**READ, 'loc': {'state': 'weak'}})
    assert not rules.shows_approval({**READ, 'confirmed': {'by': YOU, 'at': AT}})


BUCKETS = [
    ({**READ, 'loc': {'state': 'absent'}}, 'absent'),
    ({**READ, 'loc': {'state': 'weak'}}, 'eye'),
    ({**READ, 'loc': {'state': 'nocheck', 'why': 'text_layer'}}, 'eye'),
    ({**READ, 'loc': {'state': 'nocheck', 'why': 'no_printed_form'}}, 'other'),
    (DOUBTED, 'review'),
    (READ, 'unchecked'),
    ({**READ, 'loc': {'state': 'derived', 'page': 2}}, 'derived'),
    ({**READ, 'loc': {'state': 'found', 'page': 3}}, 'moved'),
    ({**READ, 'loc': {'state': 'found', 'page': 2}}, 'found'),
    ({**APPROVED, 'loc': {'state': 'found', 'page': 2}}, 'found'),
]


@pytest.mark.parametrize(('entry', 'bucket'), BUCKETS)
def test_D122_review_bucket_worst_first(entry, bucket):
    assert rules.review_bucket(entry) == bucket
    assert bucket in rules.BUCKET_KEYS


def test_D122_buckets_run_worst_first():
    order = [rules.BUCKET_ORDER[key] for key in ('absent', 'eye', 'review', 'unchecked', 'found')]
    assert order == sorted(order)


def test_E57_dealt_means_approved_or_ignored():
    assert rules.is_dealt(APPROVED) and rules.is_dealt(IGNORED)
    assert not rules.is_dealt(FLAGGED) and not rules.is_dealt(DOUBTED)


def test_M83_origin_bucket():
    assert rules.origin_bucket(READ) == 'scanned'
    assert rules.origin_bucket({'origin': 'typed', 'doc': 3}) == 'corrected'
    assert rules.origin_bucket({'origin': 'typed'}) == 'typed'
    assert rules.origin_bucket({'origin': 'import', 'doc': 3}) == 'typed'
    assert rules.origin_bucket({'origin': 'client'}) == 'client'
    assert rules.origin_bucket(None) == ''


@pytest.mark.parametrize(
    ('counts', 'label'),
    [
        ((0, 0, 0), 'Not scanned yet'),
        ((9, 1, 0), 'Clean scan'),
        ((7, 2, 1), 'Mostly clean — review flags'),
        ((6, 3, 1), 'Needs review'),
    ],
)
def test_E34_quality_headline(counts, label):
    assert rules.quality_headline(*counts)['label'] == label


def test_E48_warning_counts():
    counts = rules.warning_counts([DOUBTED, FLAGGED, APPROVED, READ, None])
    assert counts == {'open': 2, 'check': 1, 'unflagged': 1}
