"""Later and ✓ on a nudge row (I35–I39; I37 fixes old bug 7, where both wrote the task directly and skipped every
rule). Agenda holds no reminder of its own: it is the review link's `nudge`, and review's `set_nudge` and
`finish_nudge` are its only writers (plan.md §5.8, §7.13), so their rules hold here unchanged — a day today or later
and before the link runs out, the link on, its request open, the deal still asking its client (I36) — with their
sentences (400, 409). Agenda adds only what its row means: the link is this deal's (else 404), and Later moves a
reminder that is set and not yet done, never makes one (that is the link's settings card). As on a task (I32; old
891f1b3 `taskActions.laterTask`), Later's optional note is kept as a deal Note "Task moved to <day>: <note>", in the
same transaction as the move.

- `later_nudge(user, deal_id, link_id, until, note='')` → {nudge: row | None}
- `tick_nudge(user, deal_id, link_id)` → {nudge: row | None}
Each answers the row as the Agenda now reads it (None once it has gone quiet, I38). Review records the Activity (area
`review`, `nudge` / `nudge_done`, revertible); the same call again changes nothing.
"""

from django.db import transaction
from django.http import Http404

from deals import clock
from deals.services import add_note
from review import services as review_services
from review.models import ClientLink

from .. import nudges, payload, rules
from .common import lock_deal, refuse
from .tasks import clean_note

NO_DAY = 'Pick the day to nudge them.'
NO_NUDGE = 'There is no reminder to nudge on this link.'
DONE = 'This reminder is done: set a new one in the link’s settings.'


def _reminder(deal_id, link_id):
    """The link's `nudge`, or 404 when the link is not this deal's."""
    found = ClientLink.objects.filter(pk=link_id, request__deal_id=deal_id).values_list('nudge', flat=True).first()
    if found is None:
        raise Http404
    return found or {}


def row_of(deal_id, link_id):
    """The link's nudge row as the deal's Agenda reads it, or None (no reminder, or it went quiet)."""
    found = next((one for one in nudges.of([deal_id]).get(deal_id, []) if one['link_id'] == link_id), None)
    return payload.nudge_row(found, deal_id, clock.today()) if found else None


def later_nudge(user, deal_id, link_id, until, note=''):
    day = rules.parse_day(until)
    if day is None:
        refuse(400, NO_DAY)
    note = clean_note(note)
    with transaction.atomic():
        lock_deal(deal_id)  # every nudge writer locks the Deal first, so the reminder read here holds
        reminder = _reminder(deal_id, link_id)
        if not reminder.get('on'):
            refuse(409, NO_NUDGE)
        if reminder.get('done_at'):
            refuse(409, DONE)
        moved = review_services.set_nudge(user, link_id, day)
        if moved.changed and note:
            add_note(user, deal_id, body=f'Task moved to {rules.short_day(day)}: {note}')
    return {'nudge': row_of(deal_id, link_id)}


def tick_nudge(user, deal_id, link_id):
    _reminder(deal_id, link_id)
    review_services.finish_nudge(user, link_id)
    return {'nudge': row_of(deal_id, link_id)}
