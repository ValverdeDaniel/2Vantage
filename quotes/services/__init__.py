"""Every write to plans (plan.md §5.4, §7.8; F.6, OQ9 d), one module per responsibility:

- `plans`: create, PATCH (details and values, with `expect`), delete; `copies`: Create renewal, Copy as alternate;
- `marks`: stars (cap, reason, auto-link), Clear shortlist, recommend, sold;
- `roles`: roles and links, each through its own door;
- `ordering`: move, swap, reset and `put_in_slot`;
- `enrollment`: typed counts; `packages`: member-built packages; `imports`: applying the plan template.
`locks` (the Deal, then plans by id) and `batch` (one bulk_update, before and after) serve them. Every write records
Activity with before and after, writes nothing when nothing changes, and returns only what changed.
"""

from .copies import copy_as_alternate, create_renewal
from .enrollment import set_enrollment
from .imports import apply_template
from .marks import HAND_PICKED, clear_shortlist, set_recommended, set_sold, star
from .ordering import arrange, put_in_slot
from .packages import create_package, delete_package, update_package
from .plans import clean_values, create_plan, delete_plan, update_plan
from .roles import ROLES, set_links, set_role

__all__ = [
    'HAND_PICKED',
    'ROLES',
    'apply_template',
    'arrange',
    'clean_values',
    'clear_shortlist',
    'copy_as_alternate',
    'create_package',
    'create_plan',
    'create_renewal',
    'delete_package',
    'delete_plan',
    'put_in_slot',
    'set_enrollment',
    'set_links',
    'set_recommended',
    'set_role',
    'set_sold',
    'star',
    'update_package',
    'update_plan',
]
