"""Reminders to nudge someone about their link (I35–I39; L69): worked out on read from the review link's `nudge`
({on, by, at, done_at, done_by}), never a task of Agenda's own. Review & requests owns the day (its link settings
card, slice 57: `review.services.set_nudge` and `finish_nudge` are the only writers).

`of(deal_ids, now)` → {deal_id: [{link_id, request_id, who, on, by, done_at, done_by, open, later_max}]}, one query.
A reminder is `open` while the link can still be nudged — on, its request open, not run out, not answered — and it goes
quiet otherwise, coming back when the link is turned on again (I38); a ticked one stays in Done (I39). `later_max` is
the day before the link runs out: Later may not pick past it (I15, ch. 25).
"""

from datetime import timedelta

from deals import clock
from review.models import ClientLink
from review.rules import policy

from . import catalogue


def who(link):
    contact = link.contact
    return link.name or (contact.name if contact else '') or catalogue.NUDGE_NO_NAME


def of(deal_ids, now=None):
    now = now or clock.now()
    links = (
        ClientLink.objects.filter(request__deal_id__in=list(deal_ids))
        .exclude(nudge={})
        .select_related('request', 'contact')
        .order_by('id')
    )
    found = {}
    for link in links:
        nudge = link.nudge or {}
        if not nudge.get('on'):
            continue
        closed = link.request.closed_at is not None
        open_now = policy.opens(link, now, closed=closed) and link.submitted_at is None
        if not nudge.get('done_at') and not open_now:
            continue  # gone quiet (I38)
        found.setdefault(link.request.deal_id, []).append(
            {
                'link_id': link.id,
                'request_id': link.request_id,
                'who': who(link),
                'on': nudge['on'],
                'by': nudge.get('by'),
                'done_at': nudge.get('done_at'),
                'done_by': nudge.get('done_by'),
                'open': open_now,
                'later_max': (clock.local(link.expires_at).date() - timedelta(days=1)).isoformat(),
            }
        )
    return found
