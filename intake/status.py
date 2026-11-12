"""What the form says about each answer, worked out on read (plan.md §3.7, §5.2; B6, B9). Pure.

- `open_warning(entry)` is `documents.review_rules.open_warning`, the one rule (slice 17, OQ28): a value someone
  marked ⚑ Needs checking, or one Claude read and doubted (or the locator could not find) that nobody has approved or
  ignored.
- `statuses`: per question, `missing` (needed and blank, with no client answer waiting) or `to_check` (an open
  warning); blank and ok questions are left out. The badge words are the screen's (B6).
- `flags`: the open warnings on the shown questions, the stored count `Intake.flags` (O.3.7, OQ9 c), rewritten by
  every service that changes the answers or their sources.
- `review_counts`: the review bar's numbers (open warnings, how many flagged) over the shown answers (B11).
- `notes`: the form's two notes (B9): a multi-state group, and the census's salary and job title when a life or
  disability line is requested (old `multi_state`, `census_cond_note`).
"""

from decimal import Decimal, InvalidOperation

from documents.review_rules import open_warning, warning_counts

from . import form
from .values import blank

MISSING, TO_CHECK = 'missing', 'to_check'
# The lines that make salary and job title carrier-relevant on the census (old LIFE_DISABILITY_LINES).
SALARY_LINES = {'basic_life_add', 'voluntary_life', 'std', 'ltd'}
SALARY_NOTE = 'Life or disability lines are requested — carriers may also require salary and job title on the census.'


def pending_keys(client):
    """The questions a client answer waits on (the row's `client` JSON, §3.7; written from slice 53)."""
    return {
        key for key, entry in (client or {}).items() if isinstance(entry, dict) and entry.get('status') == 'pending'
    }


def statuses(answers, sources, needed, hidden, pending=()):
    """{key: 'missing' | 'to_check'} over the shown questions."""
    needed, hidden, pending = set(needed), set(hidden), set(pending)
    found = {}
    for key in form.KEYS:
        if key in hidden:
            continue
        if blank(answers.get(key)):
            if key in needed and key not in pending:
                found[key] = MISSING
        elif open_warning(sources.get(key)):
            found[key] = TO_CHECK
    return found


def flags(answers, sources, hidden):
    """The open warnings on the shown, answered questions (the stored `Intake.flags`)."""
    hidden = set(hidden)
    return sum(
        1 for key in form.KEYS if key not in hidden and not blank(answers.get(key)) and open_warning(sources.get(key))
    )


def review_counts(answers, sources, hidden):
    """{open, check, unflagged} over the shown, answered questions: the review bar's numbers (B11; E48)."""
    hidden = set(hidden)
    shown = [key for key in form.ANSWER_KEYS if key not in hidden and not blank(answers.get(key))]
    return warning_counts(sources.get(key) for key in shown)


def _count(value):
    try:
        return Decimal(str(value or '').replace(',', '').strip())
    except InvalidOperation:
        return None


def multi_state(answers):
    """More than one state of operation, or more than one location: confirm the carrier footprint (B9)."""
    states = answers.get('states_operating') or []
    if isinstance(states, str):
        states = states.replace(',', ' ').split()
    if len({str(state).strip().upper() for state in states if str(state).strip()}) > 1:
        return True
    locations = _count(answers.get('location_count'))
    return bool(locations is not None and locations.is_finite() and locations > 1)


def notes(answers, requested_lines):
    return {
        'multi_state': multi_state(answers),
        'census': SALARY_NOTE if SALARY_LINES & set(requested_lines or []) else '',
    }
