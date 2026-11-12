"""Every write to the census (plan.md §5.3, §7.7; C.5, OQ9 d), one module per responsibility:

- `imports`: a census file's proposed mapping — create, change (sheet, header row, first data row, reformat, columns),
  discard (C12–C15);
- `apply`: the dry run and the apply of an import (C16, C17); `roster` writes the matched file onto the people;
- `rows`: the locks (the Deal, the import, the people by id, then CensusFacts), the stored file and the roster entries;
- `facts`: `refresh_facts`, the door for a change made elsewhere that moves what is required (rfp, slice 45).
Every write locks what it changes, records Activity in area `census` with keys only (never a value), writes nothing
when nothing changes, and rewrites `CensusFacts` in its transaction (`census.facts.refresh`). Hand edits, people added
by hand, removal and `set_rules` join this package in slices 41 and 57.
"""

from .apply import apply_import, dry_run
from .facts import refresh_facts
from .imports import create_import, discard_import, update_import

__all__ = ['apply_import', 'create_import', 'discard_import', 'dry_run', 'refresh_facts', 'update_import']
