"""Reads for the Advisor (plan.md §7.8, F.6), one module per read: `state` (`deal_state`, every line worked out in one
grouped read), `comparison` (one line's compact payload), `lines` (the per-line counts), `plans` (one plan as a write
answers it), `sales` (what other apps ask about sales), `find` (the finder's index) and `saved_views` (the saved board
setups a person may use). GETs write nothing (Q.3 #2).
"""

from .comparison import comparison
from .find import find_index
from .lines import lines_summary
from .plans import payloads, plan_payload
from .sales import client_has_sold
from .state import LineState, deal_state, line_data, line_state, load, replaced_ids

__all__ = [
    'LineState',
    'client_has_sold',
    'comparison',
    'deal_state',
    'find_index',
    'line_data',
    'line_state',
    'lines_summary',
    'load',
    'payloads',
    'plan_payload',
    'replaced_ids',
]
