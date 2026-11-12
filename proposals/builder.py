"""`GET deals/{id}/proposal/`: the proposal builder (plan.md §7.12, §8.14; J17, J18, J23, J28–J31, J47–J62; J.6.5).

{config, marks: {done, total, stored}, lines: [line block], ready: {ok, missing, sentence, draft}, checks: [item],
 issues: []}

The builder's lines are the lines holding plans plus the lines the intent keeps as-is (their incumbent stands as the
recommendation, J47), in the producer's order (`config.order`, J31), each laid out as the files print it
(`line_layout`, so its option numbers are the ones Pages shows and Issue stamps). A line the intent keeps off stays in
the list with its notice (J30) and prints nowhere. Reads only, in a fixed number of queries whatever the plan count
(Q.3 #2, #4): `deal_state`, the intent, the config row, the option-number tops, and the intent's rows once a line is
kept. The issues list arrives with Issue (slice 32); the ledger, summary preview and file stamps with slices 26–28.
"""

from intake import coverage as intent
from intake.selectors import intent_rows_for, line_facts
from quotes import presented
from quotes import selectors as quotes
from quotes.selectors.state import empty

from . import checks, config, line_block, line_layout, marks, ready
from .models import ProposalConfig


def _stored(deal):
    row = ProposalConfig.objects.filter(deal=deal).values_list('config', 'marks').first()
    return row or ({}, {})


def proposal_lines(deal, states=None):
    """(the builder's line keys in order, {line: intent state}, {line: off reason}, states)."""
    states = quotes.deal_state(deal) if states is None else states
    held = {line: {'sold': any(plan.sold for plan in state.plans)} for line, state in states.items()}
    line_states, off = line_facts(deal, held)
    kept = [line for line, state in line_states.items() if state == intent.PRESENTED and line not in states]
    return [*states, *kept], line_states, off, states


def payload(deal):
    stored, stored_marks = _stored(deal)
    keys, line_states, off, states = proposal_lines(deal)
    keys = config.ordered(stored, keys)
    tops = line_layout.tops(deal, keys)
    layout = line_layout.layout_of(stored)
    kept_rows = {}
    if any(line_states.get(line) == intent.PRESENTED for line in keys):
        kept_rows = {row['line']: row for row in intent_rows_for(deal.id)}
    blocks, sheets = [], []
    for line in keys:
        state = states.get(line) or empty(line)
        laid = line_layout.lay_out(state, off.get(line), layout, tops.get(line, 0))
        ctx = {
            'config': stored,
            'marks': stored_marks,
            'state': line_states.get(line, ''),
            'off': off.get(line),
            'spec': config.line_spec(stored, line),
            'incumbent': line_block.incumbent(kept_rows.get(line)),
        }
        blocks.append(line_block.block(line, state, laid, ctx))
        sheets.append(line_block.facts(line, state, laid, ctx))
    on = [line for line in keys if line not in off]
    return {
        'config': stored,
        'marks': {**marks.done(stored_marks, on), 'stored': stored_marks},
        'lines': blocks,
        'ready': ready.ready(sheets),
        'checks': checks.checks(sheets, cap=presented.MAX_COLUMNS, deal_words=config.get(stored, 'recommendation')),
        'issues': [],
    }
