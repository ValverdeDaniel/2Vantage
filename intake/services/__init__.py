"""Every write to intake (plan.md §5.2, §7.6; B.6, OQ9 d), one module per responsibility:

- `coverage`: current coverage rows — add, edit, remove (B14, B19), the one service behind both editors (OQ15);
- `intent`: the coverage intent — `set_intent`, the only writer of the lines to quote (B16–B18, B32), and
  `confirm_intent` / `reopen_intent` (B20).
`rows` holds the locks (the Deal, the Intake row, then coverage rows by id) and the Activity entries they share.
Every write records Activity (area `intake`) with before and after, writes nothing when nothing changes, and returns
only what changed. The answers (`update_answers`, slice 39), the checklist, the BOR and Mark as marketed (slice 40)
join this package in their slices.
"""

from .coverage import create_coverage, delete_coverage, update_coverage
from .intent import confirm_intent, reopen_intent, set_intent

__all__ = [
    'confirm_intent',
    'create_coverage',
    'delete_coverage',
    'reopen_intent',
    'set_intent',
    'update_coverage',
]
