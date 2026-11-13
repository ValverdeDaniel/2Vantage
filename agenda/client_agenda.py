"""The client's Agenda (plan.md §7.15, §8.5; CL24, I103 as Simplified; slice 68): `GET clients/{id}/agenda/`.

One panel per deal still being worked (old 891f1b3 `TasksView ?client=`: the client's deals not past working with it,
neither lost nor a year past their effective date, `deals.rules.is_past`), the soonest effective date first, then by
id. Each panel carries the rows the deal's own Agenda shows (`selectors.rows_of`, so the two read alike), its next
step and its Waiting line, from one `facts_for` over every deal, with the marks and the tasks one query each: the same
queries for one deal or many, small or big (Q.3 #4). Reminders and the client's own tasks wait (I104–I108): every task
here lives on a deal, and the writes are the deal's own (marks, tasks, nudges).

`counts` {overdue, soon, total} is the rollup the client page wears: the sidebar's chip, the Agenda nav badge and the
Overview's Agenda tile (CL13, CL18). It counts the open rows (Up next and Waiting on: steps, open tasks and open
nudges; Later, Blocked and Done are not open), each by the day it falls due with Agenda's own `rules.severity`
(overdue before today, soon within SOON_DAYS), as the old `agendaRollup` counted (error overdue, warn soon, every
open item in the total).

{today, counts: {overdue, soon, total},
 deals: [{deal: {id, stage, effective_date, link}, next_step, waiting, rows}]}
"""

from deals import clock
from deals import rules as deal_rules

from . import marks, rows, rules, selectors
from .facts import facts_for
from .steps import steps

OPEN = ('up_next', 'waiting')
OVERDUE, SOON = 'error', 'warn'


def working(deals, today):
    """The deals still being worked, the soonest effective date first (an undated deal last), then by id."""
    kept = [deal for deal in deals if not deal_rules.is_past(deal, today)]
    return sorted(kept, key=lambda deal: (deal.effective_date is None, deal.effective_date or today, deal.id))


def _deal(deal):
    return {
        'id': deal.id,
        'stage': deal.stage,
        'effective_date': deal.effective_date.isoformat() if deal.effective_date else None,
        'link': f'/deals/{deal.id}/agenda',
    }


def panels(deals, facts, viewer, now, today):
    """One panel per deal of `deals` (`working`'s answer), from `facts` (`facts_for`'s answer for them)."""
    ids = [deal.id for deal in deals]
    stored = selectors.marks_for(ids)
    tasks = selectors.tasks_for(ids)
    found = []
    for deal in deals:
        facts_of = facts[deal.id]
        marked = marks.apply_marks(steps(facts_of, today, now), stored.get(deal.id, {}), today)
        found.append(
            {
                'deal': _deal(deal),
                'next_step': selectors.next_of(deal.id, facts_of, marked),
                'waiting': rows.waiting(marked, today),
                'rows': selectors.rows_of(deal.id, facts_of, marked, tasks.get(deal.id, []), today, viewer),
            }
        )
    return found


def counts(found, today):
    """{overdue, soon, total} over the panels' open rows (above)."""
    open_rows = [row for panel in found for row in panel['rows'] if row['section'] in OPEN]
    severities = [rules.severity(row['date'], today) for row in open_rows]
    return {'overdue': severities.count(OVERDUE), 'soon': severities.count(SOON), 'total': len(severities)}


def counts_for(deals, facts, viewer, now, today):
    """The rollup for a reader that already read `facts` for the client's deals (the client Overview's tile, slice 67):
    `deals` every deal of the client, `facts` at least theirs."""
    return counts(panels(working(deals, today), facts, viewer, now, today), today)


def client_agenda(client, viewer, now=None):
    now, today = now or clock.now(), clock.today()
    deals = working(client.deals.all(), today)
    found = panels(deals, facts_for([deal.id for deal in deals], now), viewer, now, today)
    return {'today': today.isoformat(), 'counts': counts(found, today), 'deals': found}
