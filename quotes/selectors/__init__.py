"""Reads for the Advisor (plan.md §7.8, F.6), one module per read: `state` (`deal_state`, every line worked out in one
grouped read), `comparison` (one line's compact payload), `lines` (the per-line counts), `plans` (one plan as a write
answers it) and `sales` (what other apps ask about sales). GETs write nothing (Q.3 #2).
"""

from .comparison import comparison
from .lines import lines_summary
from .plans import payloads, plan_payload
from .sales import client_has_sold
from .state import LineState, deal_state, line_data, line_state, load, replaced_ids

__all__ = [
    'LineState',
    'client_has_sold',
    'comparison',
    'deal_state',
    'line_data',
    'line_state',
    'lines_summary',
    'load',
    'payloads',
    'plan_payload',
    'replaced_ids',
]
