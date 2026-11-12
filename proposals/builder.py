"""`GET deals/{id}/proposal/`: the proposal builder (plan.md §7.12, §8.14; J17, J18, J23, J28–J31, J38–J46,
J47–J67; J.6.5).

{config, marks: {done, total, stored}, lines: [line block], ready: {ok, missing, sentence, draft}, checks: [item],
 output: {layout, package_summary, compare_tabs, disclaimers, compare_slots, pages: {page: bool}}, experience:
 {summary, rows}, next_steps, summary: {on, picked, standard, blocks, medicare}, markets: {has_asks, auto, override,
 on, lines}, ledger: [page], best_only: sentence | null, issues: [issue], stamps: {files, firm}}

The builder's lines are the lines holding plans plus the lines the intent keeps as-is (their incumbent stands as the
recommendation, J47), in the producer's order (`config.order`, J31), each laid out as the files print it
(`line_layout`, so its option numbers are the ones Pages shows and Issue stamps). A line the intent keeps off stays in
the list with its notice (J30) and prints nowhere. The deal cards (`deal_cards`) read the lines on the proposal.
Reads only, in a fixed number of queries whatever the plan count (Q.3 #2, #4): `deal_state`, the intent, the config
row, the option-number tops, the census's ages, who the RFP asked and the firm's pages (the ledger, slice 29), and
the issued versions (`issues.selectors`, slice 32; the packet card's Issued list). `stamps` keys the Export viewer's
previews (slice 28; `stamps.py`).
"""

from deals import rules
from intake import coverage as intent
from intake.selectors import intent_rows_for, line_facts
from quotes import presented
from quotes import selectors as quotes
from quotes.selectors.state import empty
from rfp.selectors import asked_by_line

from . import checks, config, deal_cards, line_block, line_layout, marks, ready, stamps
from . import summary_read as read
from .issues import selectors as issue_list
from .models import ProposalConfig
from .story import firm_read


def best_only(sheets):
    """Why "The recommendation only" layout waits (J38: it waits for every pick), or None; the old words."""
    missing = ready.missing_by_line(sheets)
    waiting = [sheet['label'] for sheet in sheets if sheet['line'] in missing]
    return f'Pick a recommendation on {", ".join(waiting)} first' if waiting else None


def stored_rows(deal):
    row = ProposalConfig.objects.filter(deal=deal).values_list('config', 'marks').first()
    return row or ({}, {})


def proposal_lines(deal, states=None):
    """(the builder's line keys in order, {line: intent state}, {line: off reason}, states)."""
    states = quotes.deal_state(deal) if states is None else states
    held = {line: {'sold': any(plan.sold for plan in state.plans)} for line, state in states.items()}
    line_states, off = line_facts(deal, held)
    kept = [line for line, state in line_states.items() if state == intent.PRESENTED and line not in states]
    return [*states, *kept], line_states, off, states


def laid_lines(deal, stored, stored_marks):
    """(builder line blocks, fact sheets, deal-card entries) in the producer's order: the lines as the files print
    them. Issue's gate reads the same sheets (`issues.gate`), so the builder's banner and Issue never disagree."""
    keys, line_states, off, states = proposal_lines(deal)
    keys = config.ordered(stored, keys)
    tops = line_layout.tops(deal, keys)
    layout = line_layout.layout_of(stored)
    intent_rows = {row['line']: row for row in intent_rows_for(deal.id)}
    blocks, sheets, entries = [], [], []
    for line in keys:
        state = states.get(line) or empty(line)
        laid = line_layout.lay_out(state, off.get(line), layout, tops.get(line, 0))
        kept = line_states.get(line) == intent.PRESENTED
        ctx = {
            'config': stored,
            'marks': stored_marks,
            'state': line_states.get(line, ''),
            'off': off.get(line),
            'spec': config.line_spec(stored, line),
            'incumbent': line_block.incumbent(intent_rows.get(line) if kept else None),
        }
        blocks.append(line_block.block(line, laid.state, laid, ctx))
        sheets.append(line_block.facts(line, laid.state, laid, ctx))
        if line not in off:
            entries.append((line, laid.state, laid, line_states.get(line, ''), intent_rows.get(line)))
    return blocks, sheets, entries


def payload(deal):
    stored, stored_marks = stored_rows(deal)
    blocks, sheets, entries = laid_lines(deal, stored, stored_marks)
    on = [entry[0] for entry in entries]
    gate = ready.ready(sheets)
    cards = deal_cards.cards(
        stored,
        entries,
        asked=asked_by_line(deal),
        ages=read.ages(deal) if 'medical' in on else None,
        renewal_offer=read.renewal_offer(deal),
        new_business=rules.deal_type(deal) == rules.NEW_BUSINESS,
        ready_ok=gate['ok'],
        firm=firm_read.ledger(stored),
    )
    deal_items = checks.deal_checks(
        next_steps=config.get(stored, 'next_steps'),
        summary=cards['summary'],
        markets_on=cards['markets']['on'],
        summary_lines=cards['facts']['lines'],
    )
    return {
        'config': stored,
        'marks': {**marks.done(stored_marks, on), 'stored': stored_marks},
        'lines': blocks,
        'ready': gate,
        'checks': checks.checks(
            sheets,
            cap=presented.MAX_COLUMNS,
            deal_words=config.get(stored, 'recommendation'),
            deal_items=deal_items,
        ),
        'output': config.output(stored),
        'experience': config.experience(stored),
        'next_steps': config.get(stored, 'next_steps'),
        'summary': cards['summary'],
        'markets': cards['markets'],
        'ledger': cards['ledger'],
        'best_only': best_only(sheets),
        'issues': issue_list.issues(deal),
        'stamps': stamps.stamps(deal),
    }
