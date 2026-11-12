"""Every write to commission (plan.md §5.6, §7.10; H.6 "Services"), one module per responsibility (OQ9 d): `rates`
(the agreed rates and the typed year, `update`), `splits` (`save_split`, the owners), `people` (`create_party`,
`save_party`, `save_settings`), `booking` (`book_deal`, `rebook`, the `sold_changed` receiver; slice 49) and `records`
(`edit_record`, `set_shares`, `add_to_book`; slice 49). Each is atomic, locks what it changes, records Activity in area
`commission` and returns only what changed.
"""

from .booking import book_deal, forget_client, on_sold_changed, rebook, rebook_record
from .people import create_party, save_party, save_settings
from .rates import AREA, update
from .records import add_to_book, edit_record, set_shares
from .splits import save_split

__all__ = [
    'AREA',
    'add_to_book',
    'book_deal',
    'create_party',
    'edit_record',
    'forget_client',
    'on_sold_changed',
    'rebook',
    'rebook_record',
    'save_party',
    'save_settings',
    'save_split',
    'set_shares',
    'update',
]
