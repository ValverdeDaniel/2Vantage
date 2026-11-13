"""The Agenda's constants and small pure rules (plan.md §5.9; I15, I17, I20, I25, I30; I.6 `rules.py`).

- `FOLLOW_UP_DAYS`: how long a wait runs before a follow-up opens: a client ask 3 days, the client's decision on an
  issued proposal 7, carriers at market 10 (I25; old `serializers.overview.FOLLOW_UP_DAYS`). Code constants (I.7 #6).
- `SOON_DAYS`: a task due within 30 days wears amber, an overdue one red (I30; the old rulebook's `soon_days`).
- `LATER_PICKS`: Later's quick picks, in days from the agency's today (I15).
- `NO_DONE_ANYWAY`: a follow-up is done by following up, and drafts by sending them: their words carry a day count
  that moves every day, so Done anyway would lapse by tomorrow (I20; old `tasks/marks.py`).
- `severity(due, today)`, `due_in(due, today)`, and the day and plural words every row and Activity summary use.
"""

from datetime import date

LATER, DONE = 'later', 'done'
MARK_KINDS = (LATER, DONE)
CALL, EMAIL = 'call', 'email'
FOLLOW_UP_KINDS = (CALL, EMAIL)

FOLLOW_UP_DAYS = {'client_ask': 3, 'decision': 7, 'carriers': 10}
# The wait each follow-up step waits again when someone logs it (old agendaRows FOLLOW_UP_WAIT).
FOLLOW_UP_WAIT = {'follow_up_client': 'client_ask', 'follow_up_selection': 'decision', 'follow_up_carriers': 'carriers'}
SOON_DAYS = 30
LATER_PICKS = [{'days': 1, 'label': 'Tomorrow'}, {'days': 3, 'label': 'In 3 days'}, {'days': 7, 'label': 'Next week'}]
NO_DONE_ANYWAY = ('follow_up_', 'send_drafts')

TITLE_MAX = 300
TASK_NOTE_MAX = 2000
MARK_NOTE_MAX = 1000
FOLLOW_UP_MAX = 8000  # a logged call or email is a deal Note (deals.models.Note.MAX_BODY)


def plural(count, noun):
    return f'{count} {noun}{"" if count == 1 else "s"}'


def days(count):
    return plural(count, 'day')


def parse_day(value):
    """An ISO day ('2026-11-20') as a date, or None."""
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or '')[:10])
    except ValueError:
        return None


def due_in(due, today):
    """Days from the agency's today to `due` (negative when overdue), or None."""
    found = parse_day(due)
    return (found - today).days if found else None


def severity(due, today, soon_days=SOON_DAYS):
    """error when overdue, warn within `soon_days`, else info (I30; old radar `_severity`)."""
    found = due_in(due, today)
    if found is None:
        return 'info'
    if found < 0:
        return 'error'
    return 'warn' if found <= soon_days else 'info'


def short_day(day):
    """'Fri 11/20' (Activity summaries; I.6's "Later: Import the census (back Fri 11/20)")."""
    day = parse_day(day)
    return f'{day.strftime("%a")} {day.month}/{day.day}' if day else ''


def can_done_anyway(key):
    return not key.startswith(NO_DONE_ANYWAY)


def is_follow_up(key):
    return key in FOLLOW_UP_WAIT


def wait_days(key):
    return FOLLOW_UP_DAYS[FOLLOW_UP_WAIT[key]] if key in FOLLOW_UP_WAIT else None
