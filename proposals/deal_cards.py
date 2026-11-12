"""The builder's deal cards as the GET reads them: the executive summary with its live preview, Markets checked and
the page ledger (plan.md §8.14; J42, J63–J66; J.6.5 `summary_preview`, `ledger`). Pure over what `builder` has worked
out, plus the census's 65+ count and who the RFP asked, which `builder` reads once.

- `summary`: {on, picked, standard, blocks}: `blocks` is the preview, every picked block (or the standard set while
  nothing is picked) worked out, an unavailable one with its reason (J64).
- `markets`: Markets checked per line (`markets.marketing`), with the producer's notes and hidden carriers (J63).
- `ledger`: each Presentation page, whether it prints and why not (J42; `story.ledger`).
"""

from . import config, markets, summary_blocks
from . import summary_read as read
from .story import ledger


def _market_settings(stored, keys):
    lines = {}
    for key in keys:
        notes = config.get(stored, f'markets.lines.{key}.notes') or {}
        hidden = set(config.get(stored, f'markets.lines.{key}.hidden'))
        lines[key] = (notes if isinstance(notes, dict) else {}, hidden)
    return {'on': config.get(stored, 'markets.on'), 'lines': lines}


def cards(stored, entries, *, asked, ages, renewal_offer, new_business, ready_ok, firm=None):
    """`entries`: [(line, state, laid, intent state, intent row)] for the lines on the proposal, in order; `firm`: the
    firm's pages for the ledger (`story.firm_read.ledger`, slice 29)."""
    keys = [entry[0] for entry in entries]
    market_lines = [read.market_line(line, state, laid, row) for line, state, laid, _s, row in entries]
    found = markets.marketing(market_lines, asked, _market_settings(stored, keys))
    facts = {
        'lines': [read.line_facts(line, state, laid, kind, row) for line, state, laid, kind, row in entries],
        'new_business': new_business,
        'renewal_offer': renewal_offer,
        'ages': ages,
        'markets': found,
    }
    picked = config.get(stored, 'summary.blocks')
    summary = {
        'on': config.get(stored, 'summary.on'),
        'picked': picked,
        'standard': summary_blocks.standard(facts),
        'blocks': summary_blocks.build(facts, picked),
        'medicare': summary_blocks.medicare_count(facts),
    }
    pages = ledger.rows(
        renewal=not new_business,
        recommended=ready_ok,
        negotiated=any(read.negotiated(state, laid) for _line, state, laid, _s, _r in entries),
        experience=config.experience(stored),
        next_steps=config.get(stored, 'next_steps'),
        firm=firm,
    )
    return {'summary': summary, 'markets': found, 'ledger': pages, 'facts': facts}
