"""The executive summary: calculations, not prose (plan.md §8.14; J64–J66). Pure.

Stephanie (2026-09-03): the decision-maker wants "What are my options? What am I looking at? What should I do?" — and
the summary is picked, not written: a list of blocks, each a function over the deal's facts. Ported from old Vantage
891f1b3 `pipeline/exec_summary.py` (`build`, `default_blocks`), split by what a block is about: `cost` (a line's
money), `design` (a line's plan design), `people` (enrollment, markets, the 65+ count), `deal` (the whole deal's
totals) and `renewal` (the carrier's letter).

`build(facts, picked)`: the picked blocks, or the deal's standard set while nothing is picked, each resolved. A line
block with no pin is worked out once per line; one that belongs to a line (the Medicare count) only on that line.
Blocks that cannot be worked out are returned with their reason, never dropped: the builder shows the producer why a
figure is not on the page, and the files print only `available` ones. The result is grouped by line, deal blocks
together, so a renderer prints each line's heading once.
"""

from deals import lines as line_vocab

from . import catalog, cost, deal, design, people, renewal
from .reading import Refused

FUNCTIONS = {
    'current_cost': cost.current_cost,
    'carriers_quoted': people.carriers_quoted,
    'best_option': cost.best_option,
    'recommended': cost.recommended,
    'spread': cost.spread,
    'annual_delta': cost.annual_delta,
    'ee_only': design.ee_only,
    'deductible_move': design.deductible_move,
    'oop_move': design.oop_move,
    'enrollment': people.enrollment,
    'lf_claims_pct': design.lf_claims_pct,
    'stop_loss_mal': design.stop_loss_mal,
    'medicare_eligible': people.medicare_eligible,
    'total_current': deal.total_current,
    'total_recommended': deal.total_recommended,
    'total_annual_delta': deal.total_annual_delta,
    'lines_shopped': deal.lines_shopped,
    'first_year_cost': deal.first_year_cost,
    'lines_proposed': deal.lines_proposed,
    'renewal_offer': renewal.renewal_offer,
    'renewal_vs_recommended': renewal.renewal_vs_recommended,
}


def medicare_count(facts):
    ages = facts.get('ages') or {}
    return (ages.get('employees_65') or 0) + (ages.get('dependents_65') or 0)


def standard(facts):
    """The un-picked summary, shaped by the deal: the standard set when any line has a current plan, else the
    new-business set (keyed on plan facts, not the deal type, as the old app did), plus the Medicare figure when the
    census holds someone 65 or older and the renewal blocks when the letter's figures are on file."""
    has_current = any(line['currents'] for line in facts['lines'])
    keys = catalog.DEFAULT_BLOCKS if has_current else catalog.NEW_BUSINESS_BLOCKS
    if medicare_count(facts):
        keys += catalog.MEDICARE_BLOCKS
    if facts.get('renewal_offer'):
        keys += catalog.RENEWAL_BLOCKS
    return [{'key': key} for key in keys]


def _targets(spec, line_keys):
    key = spec['key']
    if catalog.scope(key) == catalog.DEAL:
        return [None]
    if key in catalog.LINE_ONLY:
        return [catalog.LINE_ONLY[key]] if catalog.LINE_ONLY[key] in line_keys else []
    pin = spec.get('line')
    if pin:
        return [pin] if pin in line_keys else []
    return line_keys


def _resolve(key, facts, line):
    try:
        body = FUNCTIONS[key](facts, line)
    except Refused as refused:
        body = {'available': False, 'reason': str(refused)}
    return {
        'key': key,
        'label': body.get('label') or catalog.label(key),
        'scope': catalog.scope(key),
        'line': line or '',
        'line_label': line_vocab.label(line) if line else '',
        'available': body.get('available', True),
        'reason': body.get('reason', ''),
        'value': body.get('value'),
        'value_label': body.get('value_label', ''),
        'sub': body.get('sub', ''),
        'delta': body.get('delta'),
        'delta_label': body.get('delta_label', ''),
        'delta_dir': body.get('delta_dir', ''),
    }


def build(facts, picked):
    """Resolved blocks for `picked` ([{key, line?}]; [] = the standard set), grouped by line in first-appearance
    order, the picked order kept within each group."""
    specs = picked or standard(facts)
    line_keys = [line['key'] for line in facts['lines']]
    out = [_resolve(spec['key'], facts, line) for spec in specs for line in _targets(spec, line_keys)]
    order = []
    for block in out:
        if block['line'] not in order:
            order.append(block['line'])
    return [block for line in order for block in out if block['line'] == line]
