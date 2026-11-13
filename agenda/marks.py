"""People's marks on derived steps (I16–I26; I.6 `marks.py`). Pure: no database.

- `sig(step)`: what Done anyway signs: the step's state, its words (which carry its counts) and `basis`, the ids
  behind a count. A step whose state, words or items change no longer matches, so the mark lapses by itself with no
  hook on any write path (I21, I.5 bug 11). The same items coming back, or an uncounted step left as it was, keep it.
- `check_mark(step, kind, until, today, lost)`: the refusals, each with its old sentence and HTTP status (I17).
- `apply_marks(steps, marks, today)`: lays the marks over open or waiting steps. Done anyway, while the signature
  matches: the step is done. Later, while `until` is after the agency's today: the step keeps its state and gains
  `later_until`; Later sections and the next step hold it back. Lapsed marks are simply ignored (I26).
Ported from old Vantage 891f1b3 `tasks/marks.py` and `steps._apply_marks`.
"""

import hashlib

from . import rules

LIVE = ('open', 'waiting')

KIND = 'kind must be "later" or "done".'
NO_STEP = 'Name the step to mark.'
LOST = 'This deal is lost: reopen it before planning its steps.'
PICK_A_DAY = 'Pick a day after today to bring it back.'
FOLLOW_UP = 'A follow-up is done by following up: log it, or bring it back later.'
GONE = 'That step is no longer on this deal.'


def sig(step):
    text = f'{step["state"]}|{step["label"]}|{",".join(str(i) for i in step.get("basis") or [])}'
    return hashlib.sha1(text.encode()).hexdigest()


def check_mark(step_key, step, kind, until, today, *, lost=False):
    """None when the mark may be set, else (status, sentence): 400 for a request that could never work, 409 for one
    the deal's state refuses. `until` is a date or None; `step` is the step as the system sees it now, or None."""
    if kind not in rules.MARK_KINDS:
        return 400, KIND
    if not step_key:
        return 400, NO_STEP
    if lost:
        return 409, LOST
    if kind == rules.LATER and (until is None or until <= today):
        return 400, PICK_A_DAY
    if kind == rules.DONE and not rules.can_done_anyway(step_key):
        return 400, FOLLOW_UP
    if step is None:
        return 409, GONE
    if step['state'] not in LIVE:
        return 409, f'That step is {step["state"]}: there is nothing to mark.'
    return None


def apply_marks(steps, marks, today):
    """`marks`: {step_key: {kind, until, sig, note, by, at}} (by: a name). Returns the steps, marked."""
    out = []
    for step in steps:
        step = dict(step)
        mark = marks.get(step['key'])
        if mark and step['state'] in LIVE:
            if mark['kind'] == rules.DONE and mark.get('sig') == sig(step):
                step['state'], step['severity'] = 'done', 'done'
                step['done_anyway'] = {'by': mark.get('by') or '', 'at': mark.get('at'), 'note': mark.get('note') or ''}
            elif mark['kind'] == rules.LATER and mark.get('until') and mark['until'] > today:
                step['later_until'] = mark['until'].isoformat()
                step['later'] = {'by': mark.get('by') or '', 'note': mark.get('note') or ''}
        out.append(step)
    return out
