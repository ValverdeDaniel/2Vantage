"""The Agenda tile's read on the client page (plan.md §8.5; CL18; slice 67): what is open on the agenda of each of the
client's live deals, by the day it falls due. Reads only, from agenda's own pieces: the facts already read for the
page (`agenda.facts.facts_for`), the steps they give (`agenda.steps.steps`) with the marks laid over them, the open
hand tasks and the open nudges — the rows the deal's Agenda shows, in the sections still to do (Up next and Waiting
on; Later, Blocked and Done are not open). The marks and tasks are one query each for every deal.

`open_days(facts, deal_ids, now, today)` → [due day or None], one per open item; `client_rules.agenda_rollup` counts
them. Slice 68's client agenda (`agenda.client_agenda`) lists the same rows on the client's Agenda tab.
"""

from agenda import marks as agenda_marks
from agenda import rows as agenda_rows
from agenda.models import Task
from agenda.selectors import marks_for
from agenda.steps import steps

OPEN = ('up_next', 'waiting')


def open_days(facts, deal_ids, now, today):
    """`facts`: {deal_id: facts_for's facts}; `deal_ids`: the live deals (a lost deal has no steps, I66)."""
    deal_ids = [deal_id for deal_id in deal_ids if deal_id in facts]
    if not deal_ids:
        return []
    stored = marks_for(deal_ids)
    days = []
    for deal_id in deal_ids:
        unmarked = steps(facts[deal_id], today, now)
        for step in agenda_marks.apply_marks(unmarked, stored.get(deal_id, {}), today):
            if agenda_rows.section(step) in OPEN:
                days.append(step.get('due'))
        days += [nudge['on'] for nudge in facts[deal_id].get('nudges') or [] if not nudge.get('done_at')]
    days += list(Task.objects.filter(deal_id__in=deal_ids, done_at__isnull=True).values_list('due', flat=True))
    return days
