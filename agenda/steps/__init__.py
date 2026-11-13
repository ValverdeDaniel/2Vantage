"""A deal's steps, worked out on read from its facts (plan.md §5.9; I41, I.6). Pure: `steps(facts, today, now)` takes
one deal's facts dict (`agenda.facts.facts_for`) and returns every step it shows, in catalogue order, each `open` (ours
to do now), `waiting` (on the client or a carrier), `blocked` (a step before it is still open) or `done`. Nothing is
stored and nothing here writes; a step finishes when its real work does. People's marks are laid over these by
`agenda.marks.apply_marks`.

Tracks, in order: intake, enrollment, quotes, close (with the step after the sale), asks. A lost deal has no steps
(I66). Ported from old Vantage 891f1b3 `tasks/steps.py`, deciding from facts rather than the stage (I.5 bug 3).
"""

from . import asks, close, enrollment, intake, quotes
from .base import Steps
from .situation import situation

TRACKS = (intake, enrollment, quotes, close, asks)


def steps(facts, today, now):
    sit = situation(facts, today, now)
    if sit.lost:
        return []
    found = Steps()
    for track in TRACKS:
        track.add(found, facts, sit)
    return found.ordered()
