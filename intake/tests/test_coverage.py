"""The coverage intent's pure rules (plan.md §5.2; B16–B21, B24; F13). No database: rows are plain objects."""

from datetime import date
from types import SimpleNamespace

import pytest

from deals import lines
from intake import coverage


def _row(line, in_force=True, on_proposal=True, row_id=1, **extra):
    fields = {'carrier': '', 'funding': '', 'renewal_date': None, 'rate_guarantee_through': None, 'notes': ''}
    fields.update(extra)
    return SimpleNamespace(id=row_id, line=line, in_force=in_force, on_proposal=on_proposal, **fields)


def _rows(requested, rows):
    return coverage.intent_rows(lines.LINE_KEYS, requested, rows)


@pytest.mark.parametrize(
    ('has_today', 'this_year', 'facts', 'state'),
    [
        (True, 'market', (True, True, True), 'shopped'),
        (True, 'keep', (True, False, True), 'presented'),
        (True, 'off', (True, False, False), 'dormant'),
        (False, 'market', (False, True, True), 'gap'),
        (False, 'keep', (False, False, True), 'gap'),
    ],
)
def test_B17_two_controls_write_three_facts(has_today, this_year, facts, state):
    assert coverage.controls_to_intent(has_today, this_year) == facts
    assert coverage.this_year_of(facts[1], facts[2]) == this_year
    assert coverage.line_state(*facts) == state


def test_B16_rows_follow_the_line_order_and_an_unanswered_line_is_asked_not_a_gap():
    rows = _rows(['vision', 'medical'], [_row('dental', on_proposal=True)])
    assert [r['line'] for r in rows] == ['medical', 'dental', 'vision']
    medical = rows[0]
    assert medical['answered'] is False and medical['state'] == '' and medical['this_year'] == 'market'
    dental = rows[1]
    assert dental['answered'] and dental['this_year'] == 'keep' and dental['this_year_label'] == 'Keep as-is'
    assert dental['state_label'] == 'Presented as in force'


def test_B16_a_line_not_in_force_reads_the_gap_words():
    rows = _rows([], [_row('std', in_force=False)])
    assert rows[0]['this_year_label'] == 'Present it' and rows[0]['state_label'] == 'Proposed addition'


def test_B20_confirmation_holds_while_the_decisions_stand():
    def rows(requested=('medical',), **medical):
        return _rows(list(requested), [_row('medical', **medical), _row('dental', on_proposal=False, row_id=2)])

    stored = {'decisions': coverage.decisions(rows())}
    assert coverage.confirmation({}, rows()) == 'open'
    assert coverage.confirmation(stored, rows()) == 'done'
    assert coverage.confirmation(stored, rows(notes='Renews in March', carrier='Aetna')) == 'done'  # not decisions
    assert coverage.confirmation(stored, rows(requested=())) == 'stale'  # medical left the lines to quote
    assert coverage.confirmation(stored, rows(rate_guarantee_through=date(2027, 6, 30))) == 'stale'


def test_B24_line_states_read_the_intent_and_unknown_lines_are_shopped():
    rows = _rows(['medical'], [_row('dental', on_proposal=False), _row('std', in_force=False, row_id=2)])
    states = coverage.line_states(rows, {'vision': {'sold': False}})
    assert states == {'medical': 'shopped', 'dental': 'dormant', 'std': 'gap', 'vision': 'shopped'}


def test_F13_lines_off_the_proposal():
    rows = _rows(['medical'], [_row('dental', on_proposal=False)])
    held = {'medical': {'sold': False}, 'dental': {'sold': False}, 'vision': {'sold': False}}
    assert coverage.lines_off(rows, held, recorded=True) == {'dental': 'left_off', 'vision': 'not_in_intent'}
    assert coverage.lines_off(rows, held, recorded=False) == {'dental': 'left_off'}
    sold = {**held, 'dental': {'sold': True}, 'vision': {'sold': True}}
    assert coverage.lines_off(rows, sold, recorded=True) == {}  # a sale is the later, explicit fact


def test_B21_documents_count_per_line_and_an_unscoped_file_counts_for_every_line():
    found = coverage.documents_by_line(
        [(1, 'invoice', []), (2, 'renewal', ['dental']), (3, 'sbc', ['life']), (4, 'quote', [])],
        ['medical', 'dental'],
    )
    assert found == {'medical': {'invoice': [1]}, 'dental': {'invoice': [1], 'renewal': [2]}}
    assert coverage.needs_documents(True, 'market')
    assert not coverage.needs_documents(True, 'keep') and not coverage.needs_documents(False, 'market')


def test_B20_counts_name_the_tally_and_the_gaps():
    answered = [_row('medical'), _row('dental', on_proposal=True, row_id=2), _row('std', in_force=False, row_id=3)]
    rows = _rows(['medical', 'vision'], answered)
    assert coverage.counts(rows) == {'in_force': 2, 'shopping': 2, 'proposal': 4, 'keep': 1, 'new': 1, 'unanswered': 1}
