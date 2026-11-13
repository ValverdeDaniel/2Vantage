"""Sending the request tray (plan.md §5.8, §7.13 `POST review/tray/send/`; L52, L53, L37; old 891f1b3
`notes.send_tray`): what was gathered in the tray goes out, on the link the client already has where one can take
it, else on one new link.

`send(user, deal_id, ids=None, request_id=None, new=None)` → Sent(sent, targets, waiting, whys, dropped, created):
- `ids`: the drafts to send (default: the whole tray);
- `request_id`: every one of them onto that request (the "Goes on" picker);
- `new`: a new request for them, `{people, security?, expires_on?, message?, blank?}` as `POST review/requests/` takes
  it, whose asks are what the drafts ask (`rules.join`): "Choose who ▸" for the drafts no open link can take (with no
  `ids`, those). Its links and PINs come back once, in `created`, as a new request's do;
- otherwise each draft goes where `rules.tray.target` points, and one with nowhere to go stays (`waiting`, with why).
One transaction per destination (L53: a failure part way keeps what went), each through `deliver` in the lock order
(the Deal, the request, its links); a destination that cannot take its drafts (it closed meanwhile, a census value on a
private link) leaves them in the tray and says why (`whys`). Drafts about something no longer on the deal are dropped.
Refused (409) when the deal may no longer ask its client, or nothing waits.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals.models import Deal

from ..models import ReviewNote
from ..rules import asks as ask_rules
from ..rules import join as join_rules
from ..rules import tray as tray_rules
from ..selectors import items as item_rows
from ..selectors import notes as note_rows
from ..selectors import open_requests
from . import deliver as delivering
from . import requests
from .tray import refuse_unless_asking

Sent = namedtuple('Sent', 'sent targets waiting whys dropped created')

EMPTY = 'Nothing is waiting to go to the client.'
NOT_A_REQUEST = 'That request is not on this deal.'


def _ids(ids):
    if ids is None:
        return None
    if not isinstance(ids, list) or not all(isinstance(pk, int) and not isinstance(pk, bool) for pk in ids):
        raise ValidationError({'ids': ['Send the ids as a list of numbers.']})
    return ids


def _request_id(deal, request_id, found):
    try:
        request_id = int(request_id)
    except (TypeError, ValueError):
        raise ValidationError({'request_id': [NOT_A_REQUEST]}) from None
    if request_id not in found:
        raise ValidationError({'request_id': [NOT_A_REQUEST]})
    return request_id


def _plan(drafts, items, candidates, own):
    """({request_id: [note]}, [note waiting], {note id: why}). `own`: {link id: its request id}."""
    plan, waiting, whys = {}, [], {}
    for note in drafts:
        item = items[note_rows.ref_of(note)]
        ask = tray_rules.Item(item.ref, item.section, item.gone, own.get(item.own_link), note.request_id, item.pin)
        found, why = tray_rules.target(ask, candidates)
        if found is None:
            waiting.append(note)
            whys[note.id] = why
        else:
            plan.setdefault(found.request_id, []).append(note)
    return plan, waiting, whys


def _target_row(delivered, notes, items, now):
    return {
        'key': f'request:{delivered.request.id}',
        'request_id': delivered.request.id,
        'names': open_requests.names(delivered.links, now),
        'items': [items[note_rows.ref_of(note)].label for note in notes],
        'links': [{'link_id': link.id, 'name': link.name, 'expires_at': link.expires_at.isoformat()}
                  for link in delivered.links],
    }  # fmt: skip


def _new_request(user, deal, new, notes, items, now):
    if not isinstance(new, dict):
        raise ValidationError({'new': ['Send who the new link is for as an object.']})
    asks, _added = join_rules.join(ask_rules.empty(), [note_rows.ref_of(note) for note in notes])
    created = requests.create(user, deal.id, {**new, 'asks': asks})
    picked = [items[note_rows.ref_of(note)] for note in notes]
    delivered = delivering.deliver(user, created.request.id, notes, picked, now, revive=False)
    return created, delivered


def send(user, deal_id, *, ids=None, request_id=None, new=None):
    deal = Deal.objects.select_related('client').get(pk=deal_id)
    refuse_unless_asking(deal)
    drafts = note_rows.drafts(deal.id, _ids(ids))
    if not drafts:
        raise activity.Refused(EMPTY)
    now = clock.now()
    items = item_rows.resolve(deal, [note_rows.ref_of(note) for note in drafts])
    gone = [note for note in drafts if items[note_rows.ref_of(note)].gone]
    live = [note for note in drafts if note not in gone]
    found = open_requests.load(deal.id)
    plan, waiting, whys = _plan(live, items, open_requests.candidates(found, now), open_requests.own_requests(found))
    created = None
    if new is not None:
        chosen = live if ids is not None else waiting
        with transaction.atomic():
            created, delivered = _new_request(user, deal, new, chosen, items, now)
        targets = [_target_row(delivered, chosen, items, now)]
        plan, waiting = {}, [note for note in waiting if note not in chosen]
    else:
        if request_id is not None:
            plan, waiting = {_request_id(deal, request_id, found): live}, []
        targets = []
    for rid, notes in plan.items():
        try:
            with transaction.atomic():
                delivered = delivering.deliver(user, rid, notes, [items[note_rows.ref_of(n)] for n in notes], now)
        except delivering.NeedsNew as refused:
            waiting += notes
            whys.update({note.id: refused.why for note in notes})
            continue
        targets.append(_target_row(delivered, notes, items, now))
    if gone:
        ReviewNote.objects.filter(pk__in=[note.id for note in gone], sent_at__isnull=True).delete()
    sent = sum(len(row['items']) for row in targets)
    whys = {note.id: whys.get(note.id, tray_rules.NEEDS_LINK) for note in waiting}
    return Sent(sent, targets, [note.id for note in waiting], whys, len(gone), created)
