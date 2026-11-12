"""Every write to the census (plan.md §5.3, §7.7; C.5, OQ9 d), one module per responsibility:

- `imports`: a census file's proposed mapping — create, change (sheet, header row, first data row, reformat, columns),
  discard (C12–C15);
- `apply`: the dry run and the apply of an import (C16, C17); `roster` writes the matched file onto the people;
- `rows`: the locks (the Deal, the import, the people by id, then CensusFacts), the stored file and the roster entries;
- `facts`: `refresh_facts`, the door for a change made elsewhere that moves what is required (rfp, slice 45);
- `members`: the roster grid's writes — `edit_values` (a person's cells, with `expect`), `add_member`, `remove_member`
  and `clear_roster` (C4–C7, slice 41);
- `marks`: review marks on census cells — `mark_values` (approve, ignore, needs checking, clear; C8, slice 41).
Every write locks what it changes, records Activity in area `census` with keys only (never a value), writes nothing
when nothing changes, and rewrites `CensusFacts` in its transaction (`census.facts.refresh`). Hand edits, people added
by hand and removal arrived with the grid (slice 41); `set_rules` joins in slice 57.
"""

from .apply import apply_import, dry_run
from .facts import refresh_facts
from .imports import create_import, discard_import, update_import
from .marks import mark_values
from .members import add_member, clear_roster, edit_values, remove_member

__all__ = [
    'add_member',
    'apply_import',
    'clear_roster',
    'create_import',
    'discard_import',
    'dry_run',
    'edit_values',
    'mark_values',
    'refresh_facts',
    'remove_member',
    'update_import',
]
