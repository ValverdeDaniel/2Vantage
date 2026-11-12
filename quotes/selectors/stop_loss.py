"""The stop-loss analysis (plan.md §8.14, §9.13; F98–F107; the old StopLossAnalysis.jsx and the comparison payload's
`computed.stop_loss` at 891f1b3): the Stop-Loss line's contracts read as reinsurance, not as plan designs.

`read(deal, without)` works every figure out once, exactly (`math.stop_loss.summary`), on ONE basis: the line's
enrolled employees × 12 months (F98) — the single in-force contract's enrollment (typed on it, else the line's typed
figure, else the medical enrolled employees, else the census), and with no or several in-force contracts the line's
typed figure, else medical's, else the census. The basis names its source, so a quick quote never reads 0. Every
option is compared on that one basis, as the old workbook's "Census used for all columns" did.

`payload(found)` is the board's JSON: every money figure rounded once in quotes' math, the deltas against the one
in-force contract worked out here (F103), each option's rank on every rank key, lowest first with the unscored last
(F100), and the punchline, which always compares the lowest premium with the lowest maximum annual liability (F101,
bug 20). Lasers are named by position, never by claimant (F104, rule 10); `sl_lasers` itself never leaves quotes.
The laser what-if (`without`, {plan id: {positions}}) is a parameter of the read: never stored, never in Activity.
GETs write nothing (Q.3 #2).
"""

from dataclasses import dataclass

from .. import math as m
from .. import stop_loss_board as board
from ..math import stop_loss as sl
from .state import line_state

LINE = board.LINE


@dataclass
class Column:
    plan: object  # the model row: carrier, name, client_name, role, starred, recommended, sold
    figures: dict  # `math.stop_loss.summary`, exact
    vs: dict | None = None  # against the one in-force contract, exact; None for an in-force contract


@dataclass
class Analysis:
    lives: object  # Decimal, or None: no enrolled employees anywhere
    source: str | None
    months: int
    currents: list
    options: list  # in the board's layout order

    @property
    def current(self):
        """The one in-force contract every option is measured against; None with none or several (CUR-1)."""
        return self.currents[0] if len(self.currents) == 1 else None

    @property
    def columns(self):
        return self.currents + self.options


def refusal(count):
    """Why the workbook cannot be built with `count` in-force contracts (F106), else ''."""
    if count < 2:
        return ''
    return (
        f'This deal has {count} in-force stop-loss contracts — the analysis compares the options against one. '
        'Remove the others as current first.'
    )


def read(deal, without=None):
    """The Stop-Loss line's analysis, exactly. `without`: the laser what-if, {plan id: {laser positions}}."""
    without = without or {}
    state = line_state(deal, LINE)
    found = m.people(state.data, state.results)
    lives = found[0].get('lives') if found else None
    source = found[1] if found else None
    currents, options = [], []
    for plan in state.plans:
        figures = sl.summary(plan.values, lives, sl.MONTHS, without.get(plan.id, ()))
        (currents if plan.role == 'current' else options).append(Column(plan, figures))
    analysis = Analysis(lives, source, sl.MONTHS, currents, options)
    if analysis.current is not None:
        for column in options:
            column.vs = sl.against_current(column.figures, analysis.current.figures)
    return analysis


def ranked(options, key):
    """Option ids ranked on `key`, lowest first; an option the key cannot score comes last, in board order."""
    scored = [column for column in options if column.figures[key] is not None]
    unscored = [column for column in options if column.figures[key] is None]
    return [column.plan.id for column in sorted(scored, key=lambda column: column.figures[key]) + unscored]


def _lowest(options, key):
    found = [column for column in options if column.figures[key] is not None]
    return min(found, key=lambda column: column.figures[key]) if found else None


def punchline(options):
    """The option with the lowest premium when it is not the one with the lowest maximum annual liability ("That flip
    is the whole analysis"), else None. Independent of the rank key, so it is never false (bug 20)."""
    cheapest, safest = _lowest(options, 'annual_premium'), _lowest(options, 'max_annual_liability')
    if cheapest is None or safest is None or cheapest is safest:
        return None
    if cheapest.figures['max_annual_liability'] is None:
        return None  # a premium with no liability to weigh it against proves nothing
    return {'plan_id': cheapest.plan.id, 'carrier': cheapest.plan.carrier, 'name': cheapest.plan.name}


def _terms(plan):
    return {key: plan.values.get(key, '') for key in board.TERM_KEYS}


def _column(column):
    plan, figures = column.plan, column.figures
    return {
        'id': plan.id,
        'carrier': plan.carrier,
        'name': plan.name,
        'role': plan.role,
        'current': plan.role == 'current',
        'starred': plan.starred,
        'recommended': plan.recommended,
        'sold': plan.sold,
        'figures': sl.shown(figures),
        'vs': {key: sl.money(value) for key, value in column.vs.items()} if column.vs else None,
        'scored': figures['max_annual_liability'] is not None,
        'what_if': figures['what_if'],
        'terms': _terms(plan),
    }


def payload(found):
    """The board's JSON (plan.md §7.8 `plans/stop-loss/`)."""
    lives = m.plain(found.lives)
    return {
        'line': LINE,
        'basis': {
            'lives': lives,
            'months': found.months,
            'source': found.source,
            'words': board.basis_words(found.source) if lives else '',
        },
        'currents': [column.plan.id for column in found.currents],
        'current_id': found.current.plan.id if found.current else None,
        'columns': [_column(column) for column in found.columns],
        'ranks': {key: ranked(found.options, key) for key in board.RANK_KEY_SET},
        'punchline': punchline(found.options),
        'what_if': any(column.figures['what_if'] for column in found.columns),
        'refusal': refusal(len(found.currents)),
    }


def analysis(deal, without=None):
    return payload(read(deal, without))


def verdicts(state):
    """{plan id: {max_annual_liability, vs_current}} for a Stop-Loss `LineState` already read, rounded once here: the
    proposal summary's "Maximum annual liability" block (J64; the old `_b_stop_loss_mal`). No query."""
    found = m.people(state.data, state.results)
    lives = found[0].get('lives') if found else None
    figures = {plan.id: sl.summary(plan.values, lives) for plan in state.plans}
    currents = [plan.id for plan in state.plans if plan.role == 'current']
    base = figures[currents[0]]['max_annual_liability'] if len(currents) == 1 else None
    return {
        plan_id: {
            'max_annual_liability': sl.money(found['max_annual_liability']),
            'vs_current': None if plan_id in currents else sl.money(sl.difference(found['max_annual_liability'], base)),
        }
        for plan_id, found in figures.items()
    }
