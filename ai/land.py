"""Who lands what (plan.md §10.1; D71, O.3.3; slice 20). Pure: it takes what it reads and decides nothing else.

A finished quote read lands at once, with ↶ Undo this run, when an admin or a direct person started it. It waits for a
person's review, as a staged change set, when:
- the reader always waits (SBC, intake, census, questionnaire: `must_review`, OQ33), or reads a target that never
  lands by itself;
- the person asked for a review: a re-read from the Documents' ↻ Re-read… panel always waits (E75);
- someone else started it (a producer, the portal);
- the plan table is locked from Claude (D104), or the deal is lost (O.3.7, `deals.rules`' sentence);
- the read is partial (Stop, a failed part, a cost cap) or would remove a plan.
A read with nothing to land (no items) neither lands nor waits.
"""

from dataclasses import dataclass

AUTO, STAGED = 'auto', 'staged'  # Job.land: landed by itself; waits for review
AUTO_TARGETS = ('quotes',)

WAITS = 'Waiting for review.'
ALWAYS = 'Reads of this kind always wait for review.'
ASKED = 'A re-read waits for review: nothing on the deal changes until you use it.'
LOCKED = 'The table is locked from Claude, so this read waits for review.'
PARTIAL = 'Part of this read could not be finished, so it waits for review.'
REMOVES = 'This read would remove a plan, so it waits for review.'


@dataclass(frozen=True)
class Landing:
    mode: str  # AUTO, STAGED, or '' when there is nothing to land
    sentence: str = ''


def is_partial(change_set):
    return bool(change_set.get('partial') or change_set.get('failed_parts') or change_set.get('halted'))


def decide(change_set, *, target, must_review=False, direct=False, asked_review=False, locked=False, lost=''):
    """How a read's change set lands. `direct`: its person is an admin or a direct person (D91's test); `lost`: the
    lost deal's sentence ('' when it is not lost)."""
    items = change_set.get('items') or []
    if not items:
        return Landing('')
    if must_review or target not in AUTO_TARGETS:
        return Landing(STAGED, ALWAYS)
    if asked_review:
        return Landing(STAGED, ASKED)
    if not direct:
        return Landing(STAGED, WAITS)
    if locked:
        return Landing(STAGED, LOCKED)
    if lost:
        return Landing(STAGED, lost)
    if is_partial(change_set):
        return Landing(STAGED, change_set.get('halted') or PARTIAL)
    if any(item.get('op') == 'remove_plan' for item in items):
        return Landing(STAGED, REMOVES)
    return Landing(AUTO)


TURN_WAITS = 'These changes wait for your review: nothing on the deal changes until you apply them.'
TURN_LOCKED = 'The table is locked from Claude, so these changes wait for your review.'


def decide_turn(change_set, *, direct=False, locked=False, lost=''):
    """How a chat turn's changes land (plan.md §2's `claude_direct`: "chat changes land at once, with Undo"; D71,
    D104): at once for an admin or a direct person, unless the table is locked or the deal lost; otherwise they wait.
    A turn's removals are the person's own request, so they land like its other changes (sold and recommended plans
    are refused when proposed, D86)."""
    if not (change_set.get('items') or []):
        return Landing('')
    if not direct:
        return Landing(STAGED, TURN_WAITS)
    if locked:
        return Landing(STAGED, TURN_LOCKED)
    if lost:
        return Landing(STAGED, lost)
    return Landing(AUTO)
