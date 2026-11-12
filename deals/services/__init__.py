"""Every write to clients and deals (plan.md §3.2, §5.1, §7.3), one module per responsibility (OQ9 d):
`clients` (create, edit, delete), `deals` (edits and stage moves, `advance`), `status` (the client status door,
`sale_changed` and the `client` reverter). Other apps import from here.
"""

from .clients import create_client, delete_client, update_client
from .deals import advance, mark_lost, reopen, update_deal
from .status import sale_changed, set_status

__all__ = [
    'advance',
    'create_client',
    'delete_client',
    'mark_lost',
    'reopen',
    'sale_changed',
    'set_status',
    'update_client',
    'update_deal',
]
