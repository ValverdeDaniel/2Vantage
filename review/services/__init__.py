"""Every write to requests and links (plan.md §5.8, §7.13; L.6 services), one module per responsibility (OQ9 d):
`requests` (create with its dry run, close), `people` (who a request goes to), `links` (the link actions and their
dispatch table), `pins` (issue and check a PIN), `common` (the lock order, the shared refusals, the Activity row), the
portal's writes (`answers`, `client_adds`, `stamps`; slice 54) and `decisions` (approve, reject and undo what the
client sent, through the owners; slice 55), notes and the tray (slice 56), and slice 57's Ask card and settings card:
`form` (Update link, one locked write) with `form_preview` (its dry run), `link_settings` (a link's expiry, what they
see, its address, the reminder to nudge: `set_nudge` and `finish_nudge`, the only writers Agenda calls), `access`
(give someone else access) and `enter` (edit mode, through the owners' typed writes)."""

from .access import add_people
from .decisions import approve, reject, undo
from .enter import enter
from .form import update as update_form
from .link_settings import correct_address, finish_nudge, set_blank, set_expiry, set_nudge
from .links import ACTIONS, extend, mark_sent, new_pin, restore, revoke, unsend
from .requests import close, create

__all__ = [
    'ACTIONS',
    'add_people',
    'approve',
    'close',
    'correct_address',
    'create',
    'enter',
    'finish_nudge',
    'extend',
    'mark_sent',
    'new_pin',
    'reject',
    'restore',
    'revoke',
    'set_blank',
    'set_expiry',
    'set_nudge',
    'undo',
    'unsend',
    'update_form',
]
