"""The list one deal's steps are built into, so each step is one readable call (old Vantage 891f1b3 `tasks/steps.py`
`_Steps`), and the facts every track reads first (`Situation`). Pure."""

from datetime import date, datetime

from deals import clock

from .. import catalogue

STATES = ('open', 'waiting', 'blocked', 'done')


def iso(value):
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def as_datetime(value):
    """A datetime from a datetime or an ISO string, else None."""
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def local_day(value):
    """The agency's calendar day of a moment (§3.5): a 21:00 Eastern send is still that day, not UTC's tomorrow."""
    moment = as_datetime(value)
    if moment is None:
        return None
    return clock.local(moment).date() if moment.tzinfo else moment.date()


def days_since(value, today):
    day = local_day(value)
    return (today - day).days if day else None


class Steps:
    """The rows being built. `lead=False` keeps a step that may lead from leading now (the quote-first rule)."""

    def __init__(self):
        self.rows = []

    def add(self, key, label, *, state='open', owner='us', lead=None, severity=None, tab=None, params=None,
            blocked_by=None, reason=None, since=None, due=None, wait_days=None, basis=None, also=None):  # fmt: skip
        assert state in STATES, state
        title, default_tab, track, can_lead = catalogue.entry(key)
        if severity is None:
            severity = 'done' if state == 'done' else 'info'
        row = {
            'id': f'step:{key}',
            'kind': 'step',
            'key': key,
            'title': title,
            'label': label,
            'tab': tab or default_tab,
            'params': dict(params or {}),
            'track': track,
            'lead': can_lead if lead is None else (lead and can_lead),
            'state': state,
            'severity': severity,
            'owner': owner,
            'since': iso(since),
            'due': iso(due),
            'wait_days': wait_days,
            'blocked_by': blocked_by,
            'blocked_reason': (reason or 'After the step before it') if state == 'blocked' else '',
            'basis': sorted(basis) if basis else [],
            'also': also,  # a second link beside Open ▸ (I50: Census beside the Advisor's counts), or None
        }
        self.rows.append(row)
        return row

    def ordered(self):
        """The rows in catalogue order (§5.9), steps of one key in the order they were added."""
        place = {key: index for index, key in enumerate(catalogue.ORDER)}

        def rank(row):
            key = row['key']
            return place.get(key, place['checklist:*'] if key.startswith('checklist:') else len(place))

        return sorted(self.rows, key=rank)
