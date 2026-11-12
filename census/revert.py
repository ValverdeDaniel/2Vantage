"""Revert for census rows (plan.md §3.7, O.3.2; rule 4).

A census write records keys only, never a value (§3.8), so there is nothing to put back: `deals.activity.revert`
refuses a key-only row with its sentence before it calls an owner. This reverter answers the same, so a census row is
never reverted by accident; the grid's own undo, which holds the old value in the browser, is the way back (slice 41).
"""

from deals.activity import KEYS_ONLY, Refused


def revert(row, user):
    raise Refused(KEYS_ONLY)
