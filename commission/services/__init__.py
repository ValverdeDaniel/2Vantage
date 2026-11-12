"""Every write to commission (plan.md §5.6, §7.10; H.6 "Services"), one module per responsibility (OQ9 d): `rates`
(the agreed rates and the typed year, `update`), `splits` (`save_split`, the owners) and `people` (`create_party`,
`save_party`, `save_settings`). Each is atomic, locks what it changes, records Activity in area `commission` and
returns only what changed. Booking (`booking.py`, `records.py`) joins with slice 49.
"""

from .people import create_party, save_party, save_settings
from .rates import AREA, update
from .splits import save_split

__all__ = ['AREA', 'create_party', 'save_party', 'save_settings', 'save_split', 'update']
