"""`GET work-queue/` (plan.md §7.15, §8.3; I70–I82, I86, I122, I124; A9–A12; slice 61): the home page's one feed.

{today, rows, owners, client_names, cards: {prospects: {count, deal_size, unsized}}}

Every live deal's row (archived clients leave every list, A18), each open hand task and each open nudge (`queue.rows`),
soonest due first, undated last (the old feed's order). Finished and lost deals' rows come only with `include=closed`
(I80): Prospects and the Work queue hide them unless the Sold or Lost stage or a client search asks, and Clients reads
them for its Next action; a task stays on the queue on a sold or lost deal (I71). The steps come from the facts every
app's `summary.facts` gives, read once for every deal inside one batch scope, so the feed runs the same queries for 1
deal or 300 (Q.3 #4, Q.7). The Prospects cards are worked out here because they sum money (rule 5): the open Prospect
clients, their deals' Potential deal size and how many have none yet (I124; OQ95 as reworded by OQ101 c).
"""

from decimal import Decimal

from deals import clock, lifecycle
from deals import rules as deal_rules
from deals.models import Deal
from deals.selectors import money

from .. import marks, selectors
from ..facts import facts_for
from ..models import Task
from ..steps import steps
from . import rows


def _name(user):
    return (user.get_full_name() or user.username) if user else ''


def base(deal):
    """What every row of a deal carries (`queue.rows`)."""
    owner = deal.owner or deal.client.owner
    return {
        'deal_id': deal.id,
        'client_id': deal.client_id,
        'client_name': deal.client.name,
        'client_status': deal.client.relationship,
        'type': deal_rules.deal_type(deal),
        'stage': deal.stage,
        'effective_date': deal.effective_date.isoformat() if deal.effective_date else None,
        'owner_id': owner.id if owner else None,
        'owner_name': _name(owner),
        'deal_size': money(deal.deal_size),
        'home': f'/deals/{deal.id}',
    }


def _deal_rows(deals, now, today):
    ids = [deal.id for deal in deals]
    facts = facts_for(ids, now)
    stored = selectors.marks_for(ids)
    out, nudges = [], []
    for deal in deals:
        found = facts[deal.id]
        unmarked = steps(found, today, now)
        marked = marks.apply_marks(unmarked, stored.get(deal.id, {}), today)
        head = base(deal)
        out.append(rows.deal_row(head, found, unmarked, marked, selectors.next_of(deal.id, found, marked), today))
        nudges += [rows.nudge_row(head, nudge, today) for nudge in found.get('nudges') or [] if nudge.get('open')]
    return out, nudges


def _task_rows(deals, today):
    by_id = {deal.id: base(deal) for deal in deals}
    tasks = Task.objects.filter(deal_id__in=list(by_id), done_at__isnull=True).select_related('assigned_to')
    out = []
    for task in tasks.order_by('due', 'id'):
        person = task.assigned_to
        assignee = {'id': person.id, 'name': _name(person)} if person else None
        out.append(rows.task_row(by_id[task.deal_id], task, today, assignee))
    return out


def prospects_card(deal_rows):
    """The Prospects cards' figures (I86, I124): open Prospect clients, the sum of their deals' sizes, and how many of
    those deals have no size yet. Open: neither finished nor lost, as the old cards counted whatever the filters say."""
    shown = [
        row for row in deal_rows
        if row['client_status'] == lifecycle.PROSPECT and not row['finished'] and not row['lost']
    ]  # fmt: skip
    sized = [Decimal(row['deal_size']) for row in shown if row['deal_size'] is not None]
    return {
        'count': len({row['client_id'] for row in shown}),
        'deal_size': money(sum(sized, Decimal(0))) if sized else None,
        'unsized': len(shown) - len(sized),
    }


def _owners(found):
    seen = {}
    for row in found:
        if row['owner_id'] and row['owner_id'] not in seen:
            seen[row['owner_id']] = row['owner_name']
    return [{'id': owner_id, 'name': name} for owner_id, name in seen.items()]


def _order(row):
    return (row['due'] is None, row['due'] or '', row['client_name'].lower(), row['id'])


def work_queue(include_closed=False, now=None):
    now, today = now or clock.now(), clock.today()
    deals = list(Deal.objects.live().select_related('client', 'owner', 'client__owner').order_by('id'))
    deal_rows, nudge_rows = _deal_rows(deals, now, today)
    shown = deal_rows if include_closed else [row for row in deal_rows if not row['finished'] and not row['lost']]
    found = sorted([*shown, *_task_rows(deals, today), *nudge_rows], key=_order)
    return {
        'today': today.isoformat(),
        'rows': found,
        'owners': _owners(found),
        'client_names': sorted({row['client_name'] for row in found}, key=str.lower),
        'cards': {'prospects': prospects_card(deal_rows)},
    }
