"""The client page's own rules (plan.md §8.5; CL14–CL22, G116; slice 67). Pure: no database; `client_payload.py`
reads what they take, once.

- `newest_first(deals)`: the client's deals newest first, by effective date (undated last), then by id (old
  `_sorted_cases`, 891f1b3; ids, never timestamps, break ties).
- `current_deal(deals, today)`: the deal in flight, the newest one not past working with its client (`deals.rules.
  is_past`: lost, or a year past its effective date; old `_current_case`). None when every deal is past.
- `year_of(deal)`: the deal's year, its effective date's, else the year it was made.
- `effective(day, today)`: the Effective tile and the sidebar's date: {date, days} (negative days: since), or None.
- `agenda_rollup(days, today)`: the Agenda tile (CL18): open agenda items by the day they fall due, with Agenda's own
  severity (`agenda.rules.severity`: overdue before today, due soon within its window), as the old client page's
  `agendaRollup` counted its reminders (error = overdue, warn = soon, every item in the total).
- `sold_of(plans)`: a deal's sale, {carriers, at}, from its live plans, or None.
- `chips(...)`: G116's artifact chips on a History row: Intake (answers on file), Census (employees on the roster),
  each carrier form (armed or started; "✓" once signed) and the files (old `ArtifactChips.jsx`).
"""

from datetime import date

from agenda.rules import severity
from deals import rules as deal_rules

# The chip each kind of carrier form wears (old ArtifactChips' KIND_LABELS).
FORM_CHIPS = {'medical': 'Questionnaire', 'stop_loss': 'Stop-loss'}
OVERDUE, SOON = 'error', 'warn'


def newest_first(deals):
    return sorted(
        deals,
        key=lambda deal: (deal.effective_date is not None, deal.effective_date or date.min, deal.id),
        reverse=True,
    )


def current_deal(deals, today):
    """`deals` newest first (`newest_first`)."""
    return next((deal for deal in deals if not deal_rules.is_past(deal, today)), None)


def year_of(deal):
    if deal.effective_date:
        return deal.effective_date.year
    return deal.created_at.year if deal.created_at else None


def effective(day, today):
    if day is None:
        return None
    return {'date': day, 'days': (day - today).days}


def agenda_rollup(days, today):
    """{overdue, soon, total}: `days` holds one entry per open agenda item, its due day or None (no day, never
    overdue)."""
    found = [severity(day, today) for day in days]
    return {'overdue': found.count(OVERDUE), 'soon': found.count(SOON), 'total': len(found)}


def sold_of(plans):
    """{carriers, at} for the deal's sold plans (carriers in plan order, once each; the newest sale's moment)."""
    sold = [plan for plan in plans if plan.sold]
    if not sold:
        return None
    moments = [plan.sold_at for plan in sold if plan.sold_at]
    carriers = list(dict.fromkeys(plan.carrier for plan in sold if plan.carrier))
    return {'carriers': carriers, 'at': max(moments, default=None)}


def form_chips(armed, started, labels, kinds):
    """[{key, label, chip, signed, started}] per carrier form: `armed` {form key: signed} from intake's checklist rows
    (the form each questionnaire item uses), `started` the form keys stored on the deal; `labels` and `kinds` by key.
    A started form the checklist no longer uses still shows, as the old chips listed every stored form."""
    keys = list(dict.fromkeys([*armed, *sorted(started)]))
    return [
        {
            'key': key,
            'label': labels.get(key, ''),
            'chip': FORM_CHIPS.get(kinds.get(key), FORM_CHIPS['medical']),
            'signed': bool(armed.get(key)),
            'started': key in started,
        }
        for key in keys
        if key in labels
    ]


def chips(intake, census, forms, documents):
    """The History row's chips: `intake` and `census` are the deal's `summary.facts`; `forms` `form_chips`' answer;
    `documents` its live files. A chip with nothing behind it is None (or empty)."""
    answered = (intake or {}).get('answered') or 0
    employees = (census or {}).get('employees') or 0
    return {
        'intake': {'answered': answered, 'needed': (intake or {}).get('needed') or 0} if answered else None,
        'census': {'employees': employees, 'dependents': (census or {}).get('dependents') or 0} if employees else None,
        'forms': forms,
        'documents': documents,
    }
