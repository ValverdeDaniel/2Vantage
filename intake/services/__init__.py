"""Every write to intake (plan.md §5.2, §7.6; B.6, OQ9 d), one module per responsibility:

- `coverage`: current coverage rows — add, edit, remove (B14, B19), the one service behind both editors (OQ15);
- `answers`: the form's answers — `update_answers`, the one writer of `Intake.answers` and their sources, and the
  door onto the deal's effective date (B1, B4);
- `marks`: review marks on the answers — `mark_answers` (approve, ignore, needs checking, clear; B10, B11);
- `checklist`: the marketing checklist's controls — `set_checklist_item`: the "On file" / "Confirmed" tick and the
  requirement (Not needed, Still needed ▸, Undo) of every attested item, COBRA included (the Census tab ticks it,
  C25, O.6 #2; B26, B27);
- `bor`: the broker-of-record e-signature — `sign_bor`, `clear_bor` (B29);
- `marketed`: Mark as marketed — `mark_marketed` (409 with the gaps until ready, or Market anyway, which records the
  skipped items), `unmark_marketed` (B33, B34);
- `intent`: the coverage intent — `set_intent`, the only writer of the lines to quote (B16–B18, B32), and
  `confirm_intent` / `reopen_intent` (B20).
`rows` holds the locks (the Deal, the Intake row, then coverage rows by id) and the Activity entries they share.
Every write records Activity (area `intake`) with before and after, writes nothing when nothing changes, and returns
only what changed.
"""

from .answers import update_answers
from .bor import clear_bor, sign_bor
from .checklist import set_checklist_item
from .coverage import create_coverage, delete_coverage, update_coverage
from .intent import confirm_intent, reopen_intent, set_intent
from .marketed import NotReady, mark_marketed, unmark_marketed
from .marks import mark_answers

__all__ = [
    'NotReady',
    'clear_bor',
    'confirm_intent',
    'create_coverage',
    'delete_coverage',
    'mark_answers',
    'mark_marketed',
    'reopen_intent',
    'set_checklist_item',
    'set_intent',
    'sign_bor',
    'unmark_marketed',
    'update_answers',
    'update_coverage',
]
