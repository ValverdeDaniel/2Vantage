"""A client answer as review sees it (plan.md §5.8; L.6 `rules/items.py`; L9, L14, L16, L43; old 891f1b3
`review/items.py`). Pure: the link's fields (a model instance or anything with the same attributes) and `now`.

- When an answer is **ready to review** (Daniel, 2026-10-26): its link was submitted after its last save, or that save
  is 24 hours old (`requests.ready`). Until then it reads **in progress** ("still typing"): per link, never per value,
  so the answers typed first do not jump into the queue while the client types the rest. An answer whose link is gone
  is ready.
- `ready_why`: why it is ready: `submitted`, `idle` ("Not submitted · idle N days") or '' (still typing). "Approve N
  ready" takes the submitted ones, and the idle ones only with its tick (D-153 C4).
- `change`: what the answer does to the value we hold: `added` (a person the client added), `same` (confirms it),
  `filled` (we held nothing), `cleared` (they blanked it) or `changed`. A cleared answer is never taken by "Approve N
  ready": a person looks at it (old `_add`).
- `GOING_BACK` (slice 56): an answer sent back to the client and not answered since (`rules.tray.going_back`) leaves
  To review for the queue's third phase until they answer again (L16).
"""

from .requests import IDLE, ready

TO_REVIEW, IN_PROGRESS, GOING_BACK = 'to_review', 'in_progress', 'going_back'
PHASES = (TO_REVIEW, IN_PROGRESS, GOING_BACK)
SUBMITTED, IDLE_WHY = 'submitted', 'idle'
ADDED, SAME, FILLED, CLEARED, CHANGED = 'added', 'same', 'filled', 'cleared', 'changed'
CHANGES = (CHANGED, ADDED, FILLED, CLEARED, SAME)  # the order the queue lists its groups (old CHANGE_ORDER)


def blank(value):
    return value is None or value == '' or value == []


def ready_why(link, now):
    if link is None:
        return SUBMITTED
    saved, submitted = link.last_saved_at, link.submitted_at
    if submitted and (saved is None or submitted >= saved):
        return SUBMITTED
    return IDLE_WHY if ready(link, now) else ''


def phase(link, now):
    return TO_REVIEW if ready_why(link, now) else IN_PROGRESS


def idle_days(link, now):
    """Whole days since an idle link's last save, else None."""
    if link is None or ready_why(link, now) != IDLE_WHY:
        return None
    return (now - link.last_saved_at).days


def ready_at(link, now):
    """When a link still being typed turns ready if nobody submits it, else None."""
    if link is None or link.last_saved_at is None or ready_why(link, now):
        return None
    return link.last_saved_at + IDLE


def same(a, b):
    if blank(a) and blank(b):
        return True
    return a == b


def change(stored, value, *, person=False):
    if person:
        return ADDED
    if same(stored, value):
        return SAME
    if blank(stored):
        return FILLED
    if blank(value):
        return CLEARED
    return CHANGED


def takes(why, *, cleared=False, include_idle=False):
    """Whether "Approve N ready" takes an answer: ready for its link's reason, and not one that blanks a value."""
    if cleared:
        return False
    return why == SUBMITTED or (include_idle and why == IDLE_WHY)
