"""Every write to clients and deals (plan.md §3.2, §5.1, §7.3), one module per responsibility (OQ9 d):
`clients` (create, edit; delete for the seeders only), `deals` (edits and stage moves, `advance`, lost and reopen;
`set_effective_date`, the door of intake's target effective date), `facts` (`set_owner`, the header facts), `lines`
(the lines to quote, written only through intake's `set_intent`), `status` (the client status door, `sale_changed` and
the `client` reverter), `archive` (Archive and Restore), `notes`, `contacts` and `agency` (the agency's default
commission rate, H100; slice 48). Other apps import from here.
"""

from .agency import set_default_commission
from .archive import set_archived
from .clients import create_client, delete_client, update_client
from .contacts import create_contact, delete_contact, update_contact
from .deals import advance, mark_lost, reopen, set_effective_date, update_deal
from .facts import set_facts, set_owner
from .lines import clean_lines, set_lines
from .notes import add_note, delete_note, update_note
from .status import sale_changed, set_status

__all__ = [
    'add_note',
    'advance',
    'clean_lines',
    'create_client',
    'create_contact',
    'delete_client',
    'delete_contact',
    'delete_note',
    'mark_lost',
    'reopen',
    'sale_changed',
    'set_archived',
    'set_default_commission',
    'set_effective_date',
    'set_facts',
    'set_lines',
    'set_owner',
    'set_status',
    'update_client',
    'update_contact',
    'update_deal',
    'update_note',
]
