"""Every write to plans (plan.md §5.4, §7.8; F.6, OQ9 d), one module per responsibility:

- `plans`: create, PATCH (details and values, with `expect`); `copies`: Create renewal, Duplicate (`copy_plan`);
- `removal`: soft delete and Clear line (Restore is Revert); `moves`: move to another line; `merge`: two into one;
- `marks`: stars (cap, reason, auto-link), Clear shortlist, recommend, sold;
- `roles`: roles and links, each through its own door;
- `ordering`: move, swap, reset and `put_in_slot`;
- `enrollment`: typed counts; `packages`: member-built packages; `imports`: applying the plan template;
- `saved_views`: the Advisor's saved board setups (firm rows, not plans; F28).
`locks` (the Deal, then plans by id) and `batch` (one bulk_update, before and after) serve them. Every write records
Activity with before and after, writes nothing when nothing changes, and returns only what changed.
"""

from . import saved_views  # a module: services.saved_views.create, update, delete
from .copies import copy_plan, create_renewal
from .enrollment import set_enrollment
from .imports import apply_template
from .marks import HAND_PICKED, clear_shortlist, set_recommended, set_sold, star
from .merge import merge_plans
from .moves import move_line
from .ordering import arrange, put_in_slot
from .packages import create_package, delete_package, update_package
from .plans import clean_values, create_plan, update_plan
from .removal import clear_line, delete_plans
from .roles import ROLES, set_links, set_role

__all__ = [
    'HAND_PICKED',
    'ROLES',
    'apply_template',
    'arrange',
    'clean_values',
    'clear_line',
    'clear_shortlist',
    'copy_plan',
    'create_package',
    'create_plan',
    'create_renewal',
    'delete_package',
    'delete_plans',
    'merge_plans',
    'move_line',
    'put_in_slot',
    'saved_views',
    'set_enrollment',
    'set_links',
    'set_recommended',
    'set_role',
    'set_sold',
    'star',
    'update_package',
    'update_plan',
]
