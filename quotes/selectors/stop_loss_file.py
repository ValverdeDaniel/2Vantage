"""What the stop-loss workbook prints (plan.md §9.13; J166, F106, OQ43, OQ104): the analysis (`stop_loss.read`) as a
client-safe read, for the proposals app's writer.

Only client fields leave here: the contract terms, the numbers the sheet takes as inputs and quotes' exact figures,
which are the formulas' stored results. Lasers leave as amounts on numbered rows: `shared` puts each option's laser on
its claimant's row (one person lined up across carriers, as the old sheet's shared rows did) without the claimant;
`sl_lasers` itself never leaves quotes (OQ104, rule 10). The workbook refuses two or more in-force contracts (F106)
and a line with no stop-loss plan; `refusal` says so in the producer's words.
"""

from .. import stop_loss_board as board
from ..math import stop_loss as sl
from . import stop_loss
from .state import medical_people

LASER_ROWS = 6  # the old sheet's reserve and floor: a longer list grows the block, never truncates it
NO_PLANS = (
    'No stop-loss plans on this deal yet — add the in-force contract and the incoming options on the Stop-Loss line '
    'first.'
)


def _plan(column, shared):
    plan = column.plan
    return {
        'id': plan.id,
        'carrier': plan.carrier,
        'name': plan.client_name or plan.name,
        'terms': {key: plan.values.get(key, '') for key in board.TERM_KEYS},
        'figures': column.figures,
        'vs': column.vs,
        'lasers': [laser['amount'] for laser in column.figures['lasers']],
        'shared': shared,
    }


def read(deal):
    """{lives, months, source, current, options, laser_rows, tiers, refusal}; `refusal` set means nothing to print."""
    found = stop_loss.read(deal)
    refusal = stop_loss.refusal(len(found.currents)) or ('' if found.columns else NO_PLANS)
    ordered = found.currents[:1] + found.options
    count, shared = sl.shared_rows([sl.parse_lasers(column.plan.values.get('sl_lasers')) for column in ordered])
    plans = [_plan(column, rows) for column, rows in zip(ordered, shared, strict=True)]
    current = plans[0] if found.current is not None else None
    medical = medical_people(deal)
    return {
        'lives': found.lives,
        'months': found.months,
        'source': found.source,
        'current': current,
        'options': plans[1:] if current else plans,
        'laser_rows': max(LASER_ROWS, count, len(current['lasers']) if current else 0),
        'tiers': dict(medical[0]) if medical else {},
        'refusal': refusal,
    }
