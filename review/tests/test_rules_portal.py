"""The portal's pure rules, table by table (plan.md §5.8; L81, L83, L96, L103; B43): the lock rule, "we read", the
form stamp, the to-do rail, and the client-entry rule every owner shares (base, shown, next entry)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from intake import client_entries as entries
from review.rules import portal

NOW = datetime(2026, 11, 12, 15, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ('source', 'value', 'reopened', 'editable'),
    [
        ({'origin': 'typed'}, 'Acme', False, False),
        ({'origin': 'relay'}, 'Acme', False, False),
        ({'origin': 'client'}, 'Acme', False, False),
        ({'origin': 'ai'}, 'Acme', False, True),
        ({'origin': 'ai', 'confirmed': {'by': 1}}, 'Acme', False, False),
        ({'origin': 'import'}, 'Acme', False, True),
        ({'origin': 'typed'}, '', False, True),
        ({'origin': 'typed'}, 'Acme', True, True),
        (None, 'Acme', False, True),
    ],
)
def test_B43_one_lock_rule_typed_approved_or_relayed(source, value, reopened, editable):
    assert portal.editable(source, value, reopened) is editable


def test_L83_we_read_marks_only_claudes_unapproved_values():
    assert portal.we_read({'origin': 'ai'}, 'x') == 'read'
    assert portal.we_read({'origin': 'ai', 'confirmed': {'by': 1}}, 'x') == ''
    assert portal.we_read({'origin': 'typed'}, 'x') == ''
    assert portal.we_read({'origin': 'ai'}, '') == ''


def _link(**kw):
    base = {
        'blank': False,
        'security': 'link',
        'pin_version': 0,
        'submitted_at': None,
        'revoked_at': None,
        'expires_at': NOW + timedelta(days=7),
    }
    return SimpleNamespace(**{**base, **kw})


def test_L103_the_form_stamp_moves_with_what_the_page_was_built_from():
    request = SimpleNamespace(form_version=1, closed_at=None)
    first = portal.form_stamp(_link(), request, NOW)
    assert first == portal.form_stamp(_link(), request, NOW)
    for changed in ({'blank': True}, {'security': 'pin'}, {'pin_version': 1}, {'submitted_at': NOW}):
        assert portal.form_stamp(_link(**changed), request, NOW) != first
    assert portal.form_stamp(_link(), SimpleNamespace(form_version=2, closed_at=None), NOW) != first
    assert portal.form_stamp(_link(), SimpleNamespace(form_version=1, closed_at=NOW), NOW) != first


WORDS = {'intake': 'Company intake form', 'people': 'Employee details', 'census': 'Employee census file'}


def test_L81_the_rail_counts_shown_fields_and_received_files():
    intake = {'sections': [{'fields': [
        {'value': 'a', 'shown': True}, {'value': '', 'shown': True}, {'value': '', 'shown': False},
        {'value': '', 'locked': True, 'shown': True},
    ]}]}  # fmt: skip
    people = [{'fields': [{'value': '1'}, {'value': ''}]}]
    rail = portal.rail(WORDS, intake, people, {'received': []}, [{'slot': 'invoice', 'label': 'Invoice',
                                                                   'received': [{'name': 'x'}]}])  # fmt: skip
    by_key = {item['key']: item for item in rail['items']}
    assert (by_key['intake']['filled'], by_key['intake']['total'], by_key['intake']['done']) == (2, 3, False)
    assert (by_key['people']['filled'], by_key['people']['total']) == (1, 2)
    assert by_key['census']['done'] is False and by_key['doc_invoice']['done'] is True
    assert (rail['done'], rail['total']) == (1, 4)
    assert portal.rail(WORDS, None, [], None, []) == {'items': [], 'done': 0, 'total': 0}


def test_L96_a_base_is_a_stamp_never_the_value_and_a_blank_link_sees_only_its_own():
    source = {'origin': 'typed', 'at': '2026-11-01T00:00:00'}
    mine = entries.made('x', 7, '2026-11-02T00:00:00')
    theirs = entries.made('y', 8, '2026-11-03T00:00:00')
    assert entries.base(source, mine, 7) != entries.base(source, None, 7)
    assert 'x' not in entries.base(source, mine, 7)
    assert entries.base(source, theirs, 7, blank=True) == entries.base(None, None, 7, blank=True)
    assert entries.shown('stored', theirs, 7) == 'y'
    assert entries.shown('stored', theirs, 7, blank=True) == ''
    assert entries.shown('stored', mine, 7, blank=True) == 'x'
    assert entries.by_colleague(theirs, 7) and not entries.by_colleague(mine, 7)


@pytest.mark.parametrize(
    ('stored', 'entry', 'value', 'after', 'moved'),
    [
        ('a', None, 'a', None, False),  # equal to the stored value, nothing pending
        ('a', entries.made('b', 1, 't'), 'a', None, True),  # back to the stored value drops the pending one
        ('a', entries.made('b', 1, 't'), 'b', 'b', False),  # the same answer again
        ('a', entries.made('b', 2, 't'), 'c', 'c', True),  # a newer answer replaces a colleague's
        ('', None, 'c', 'c', True),
    ],
)
def test_L95_a_save_sets_drops_or_keeps_the_pending_answer(stored, entry, value, after, moved):
    result, changed = entries.next_entry(stored, entry, value, 1, 'now', prior=stored)
    assert changed is moved
    assert (result['value'] if result else None) == after
    if result and changed:
        assert (result['status'], result['link'], result['prior']) == ('pending', 1, stored)
