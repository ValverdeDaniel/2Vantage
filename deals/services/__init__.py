"""Every write to clients and deals (plan.md §3.2, §5.1, §7.3), one module per responsibility (OQ9 d):
`clients` (create, edit, delete), `deals` (edits and stage moves, `advance`; `set_effective_date`, the door of
intake's target effective date), `lines` (the lines to quote, written only through intake's `set_intent`), `status`
(the client status door, `sale_changed` and the `client` reverter). Other apps import from here.
"""

from .clients import create_client, delete_client, update_client
from .deals import advance, mark_lost, reopen, set_effective_date, update_deal
from .lines import clean_lines, set_lines
from .status import sale_changed, set_status

__all__ = [
    'advance',
    'clean_lines',
    'create_client',
    'delete_client',
    'mark_lost',
    'reopen',
    'sale_changed',
    'set_effective_date',
    'set_lines',
    'set_status',
    'update_client',
    'update_deal',
]
