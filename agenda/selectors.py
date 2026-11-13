"""Agenda's reads (plan.md §5.9, §7.15; I.6 selectors). Nothing here writes.

- `deal_agenda(deal, viewer)`: `GET deals/{id}/agenda/` — {today, deal_id, lost, finished, next_step, waiting,
  journey, progress, rows}: the facts read once, the steps worked out, the marks laid over them, the tasks and nudges.
- `marked_steps(deal_id)`: (facts, unmarked steps, marked steps, today) — what the services decide against.
- `next_step(deal)`, `waiting(deal)`: the Overview's light reads (slice 62), from the same steps.
`today` is the agency's date (`deals.clock.today()`), so a Later picked at 21:00 Eastern means the agency's tomorrow.
"""

from deals import clock
from deals.models import Deal

from . import journey, links, marks, payload, rows
from .facts import facts_for
from .models import StepMark, Task
from .steps import steps


def stored_marks(deal_id):
    """{step_key: {kind, until, sig, note, by, at}} for the deal, in one query."""
    found = {}
    for mark in StepMark.objects.filter(deal_id=deal_id).select_related('by'):
        found[mark.step_key] = {
            'kind': mark.kind,
            'until': mark.until,
            'sig': mark.sig,
            'note': mark.note,
            'by': (mark.by.get_full_name() or mark.by.username) if mark.by else '',
            'at': mark.at.isoformat() if mark.at else None,
        }
    return found


def marked_steps(deal_id, now=None):
    now = now or clock.now()
    today = clock.today()
    facts = facts_for([deal_id], now).get(deal_id)
    if facts is None:
        raise Deal.DoesNotExist
    unmarked = steps(facts, today, now)
    return facts, unmarked, marks.apply_marks(unmarked, stored_marks(deal_id), today), today


def _next(deal_id, facts, marked):
    deal = facts['deal']
    if deal['lost']:
        return rows.lost_step(deal.get('lost_reason'))
    found = rows.next_step(marked) or (rows.sold_step(marked) if deal['sold'] else None)
    if found:
        found['link'] = links.link_for(deal_id, found['tab'], found.get('params'))
    return found


def step_payload(deal_id, step, marked, facts):
    """A mark's answer: {step, next_step} — the step's row now, and the deal's next step."""
    row = next((s for s in marked if s['key'] == step), None)
    return {
        'step': payload.step_row(row, deal_id) if row else None,
        'next_step': _next(deal_id, facts, marked),
    }


def deal_agenda(deal, viewer):
    facts, unmarked, marked, today = marked_steps(deal.id)
    tasks = Task.objects.filter(deal=deal).select_related('assigned_to', 'done_by', 'created_by')
    step_rows = [payload.step_row(step, deal.id) for step in marked]
    task_rows = [payload.task_row(task, today, viewer) for task in tasks]
    nudge_rows = [payload.nudge_row(nudge, deal.id, today) for nudge in facts.get('nudges') or []]
    milestones = journey.journey(facts, unmarked)
    return {
        'today': today.isoformat(),
        'deal_id': deal.id,
        'lost': facts['deal']['lost'],
        'finished': facts['deal']['lost'] or rows.finished(unmarked),
        'next_step': _next(deal.id, facts, marked),
        'waiting': rows.waiting(marked, today),
        'journey': milestones,
        'progress': journey.progress(milestones),
        'rows': payload.arrange(step_rows, task_rows, nudge_rows),
    }


def next_step(deal):
    facts, _unmarked, marked, _today = marked_steps(deal.id)
    return _next(deal.id, facts, marked)


def waiting(deal):
    _facts, _unmarked, marked, today = marked_steps(deal.id)
    return rows.waiting(marked, today)
