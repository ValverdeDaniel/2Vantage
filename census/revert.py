"""Revert for census rows (plan.md §3.7, O.3.2; rule 4).

A census write records keys only, never a value (§3.8), so there is nothing to put back: `deals.activity.revert`
refuses a key-only row with its sentence before it calls an owner, and this reverter answers the same, so a census row
is never reverted by accident; the grid's own undo, which holds the old value in the browser, is the way back
(slice 41). Review marks are the exception: a `marked` row holds marks, never values, and its Revert puts them back on
the cells still as it left them (E88; `services.marks.revert`).
"""

from deals.activity import KEYS_ONLY, Refused

from .services import marks


def revert(row, user):
    if row.action == marks.MARKED:
        return marks.revert(row, user)
    raise Refused(KEYS_ONLY)
