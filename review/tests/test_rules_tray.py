"""The tray's pure rules (plan.md §5.8; L49–L53, L58, L64; slice 56): where a draft goes or why it cannot, asking more
on an open request (`rules.join`), what a link carries beside its scope, when a sent ask is still open, and which client
answers went back to the client."""

from collections import namedtuple
from datetime import UTC, datetime, timedelta

import pytest

from review.rules import ask_words, join, policy, rail
from review.rules import refs as ref_rules
from review.rules import tray as tray_rules
from review.rules.asks import CELL_LIMIT, clean
from review.rules.requests import carries

NOW = datetime(2026, 11, 12, 15, tzinfo=UTC)
Entry = namedtuple('Entry', 'ref at')


def candidate(request_id, *, days=0, sections=('intake',), security='link'):
    return tray_rules.Candidate(request_id, NOW - timedelta(days=days), list(sections), security, ['Dana'])


def item(ref='intake:fein', section='intake', *, gone=False, own=None, named=None, pin=False):
    return tray_rules.Item(ref, section, gone, own, named, pin)


def test_L52_a_draft_goes_to_its_own_request_then_one_asking_its_section_then_the_newest():
    old_census = candidate(1, days=5, sections=['census'])
    old_intake = candidate(2, days=3, sections=['intake'])
    newest = candidate(3, days=1, sections=['census'])
    pool = [old_census, old_intake, newest]
    assert tray_rules.target(item(own=1), pool) == (old_census, '')
    assert tray_rules.target(item(), pool) == (old_intake, '')
    assert tray_rules.target(item(section='questionnaire'), pool) == (newest, '')


def test_L52_with_no_open_request_a_draft_needs_a_new_link_and_a_gone_one_says_so():
    assert tray_rules.target(item(), []) == (None, tray_rules.NEEDS_LINK)
    assert tray_rules.target(item(gone=True), [candidate(1)]) == (None, tray_rules.GONE)


def test_L52_B18_a_census_value_goes_only_on_a_pin_link():
    private, pinned = candidate(1, days=1, sections=['census']), candidate(2, days=4, security='pin')
    assert tray_rules.target(item('census:4:dob', 'census', pin=True), [private]) == (None, tray_rules.NEEDS_PIN)
    assert tray_rules.target(item('census:4:dob', 'census', pin=True), [private, pinned]) == (pinned, '')
    assert tray_rules.target(item('census:file', 'census'), [private]) == (private, '')


def test_L52_a_draft_named_for_a_request_never_rides_another():
    one, two = candidate(1), candidate(2)
    assert tray_rules.target(item(named=1), [one, two]) == (one, '')
    assert tray_rules.target(item(named=9), [one, two]) == (None, tray_rules.NEEDS_LINK)
    assert tray_rules.target(item('census:4:dob', 'census', named=1, pin=True), [one]) == (None, tray_rules.NEEDS_PIN)


def test_L53_join_adds_what_the_request_does_not_name_and_keeps_its_scope():
    asks = clean({'intake': {'scope': 'missing'}, 'documents': {'slots': ['claims']}})[0]
    joined, added = join.join(asks, ['intake:fein', 'intake:dba', 'doc:claims', 'doc:renewal@medical', 'census:file'])
    assert added == ['intake:fein', 'intake:dba', 'doc:renewal@medical', 'census:file']
    assert joined['intake']['scope'] == 'missing'
    assert joined['intake']['keys'].index('dba') < joined['intake']['keys'].index('fein')  # the form's order
    assert joined['documents']['slots'] == ['claims', 'renewal@medical']
    assert joined['census'] == {'scope': 'none', 'columns': [], 'cells': [], 'file': True}
    assert asks['intake']['keys'] == []  # never changed in place
    assert clean(joined)[1] == {}


def test_L53_join_census_values_start_a_selected_ask_and_stop_at_the_limit():
    joined, added = join.join({}, ['census:7:dob', 'census:7:dob', 'intake:block:bor'])
    assert added == ['census:7:dob', 'intake:block:bor']
    assert joined['census']['scope'] == 'selected' and joined['census']['cells'] == [[7, 'dob']]
    assert joined['intake'] == {'scope': 'selected', 'keys': [], 'blocks': ['bor']}
    assert policy.floor(joined)['level'] == policy.PIN
    many = [f'census:{n}:dob' for n in range(CELL_LIMIT + 1)]
    with pytest.raises(join.TooMany):
        join.join({}, many)


def test_L53_keys_and_cells_named_beside_a_scope_are_carried_and_named_on_the_card():
    asks = clean(
        {
            'intake': {'scope': 'missing', 'keys': ['website']},
            'census': {'scope': 'missing', 'columns': ['zip'], 'cells': [[3, 'dob']]},
        }
    )[0]
    assert asks['intake']['keys'] == ['website'] and asks['census']['cells'] == [[3, 'dob']]
    assert carries(asks, 'intake:website') and not carries(asks, 'intake:dba')
    assert carries(asks, 'census:3:dob') and not carries(asks, 'census:3:email')
    assert carries(asks, 'census:4:zip', missing={'census:4:zip'})
    assert ask_words.words(asks) == ['1 census column', '1 more census value', 'Intake gaps', '1 more intake question']


def test_L22_note_refs_round_trip():
    for ref in ('intake:fein', 'intake:block:bor', 'census:12:dob', 'census:file', 'doc:invoice@medical'):
        assert ref_rules.ref_of_note(*ref_rules.note_of(ref)) == ref
    assert ref_rules.note_of('census:12:ssn') == ('census', 'ssn', 12)  # named; resolving it refuses (no SSN asks)
    for bad in ('census:12:*', 'intake:block:payroll', 'intake:nope', 'q:form:x', 7):
        assert ref_rules.note_of(bad) is None


def test_L16_a_sent_ask_is_open_until_someone_answers_it_or_its_link_stops_opening():
    sent = NOW - timedelta(days=1)
    assert tray_rules.open_ask(sent, opens=True)
    assert not tray_rules.open_ask(sent, opens=False)
    assert not tray_rules.open_ask(sent, opens=True, answered_at=NOW.isoformat())
    assert tray_rules.open_ask(sent, opens=True, answered_at=(sent - timedelta(hours=1)).isoformat())
    assert not tray_rules.open_ask(sent, opens=True, decided_at=NOW)


def test_L16_an_answer_goes_back_while_its_send_back_waits_or_went_out_after_it():
    sent = NOW - timedelta(hours=2)
    before, after = (sent - timedelta(hours=1)).isoformat(), (sent + timedelta(hours=1)).isoformat()
    entries = [Entry('intake:fein', before), Entry('intake:dba', after), Entry('intake:sic', after)]
    back = tray_rules.going_back(entries, {'intake:sic'}, {'intake:fein': sent, 'intake:dba': sent})
    assert back == {'intake:fein', 'intake:sic'}


def test_L29_one_status_per_item_in_one_order():
    assert rail.status(question=True, draft=True) == rail.QUESTION
    assert rail.status(draft=True, pending=True) == rail.IN_CART
    assert rail.status(pending=True, asked=True) == rail.ANSWERED
    assert rail.status(asked=True, filled=True) == rail.ASKED
    assert rail.status(filled=True) == rail.ON_FILE
    assert rail.status() == rail.MISSING
    counted = rail.counts([{'status': 'missing'}, {'status': 'missing'}, {'status': 'asked'}])
    assert (counted['all'], counted['missing'], counted['asked'], counted['question']) == (3, 2, 1, 0)
