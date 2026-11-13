"""Putting notes on a request the client already has (plan.md §5.8; L53, L58; old 891f1b3 `notes.send_group`,
`client_request.extend_ask`). The one write a tray send, a note to the client and the request page share.

`deliver(user, request_id, notes, items, now)` inside the caller's transaction: locks the Deal, the request, then its
links by id; refuses when the deal may no longer ask its client or the request closed (409). What the notes are about
and the request does not ask yet joins its asks (`rules.join`), bumping `form_version` so an open page re-reads; a
join that would need a PIN the links do not ask for (a census value on a private link), or that runs past the census
limit, is refused with `NeedsNew` and nothing is written (a link is never tightened under its holder, L64). Then every
link that can still live gets its life again from now, within its ceiling (a link that ran out comes back: "lives
again when sent"), and the notes are routed to the request and stamped sent, so they show on its links. One Activity
row, key-only (what was asked about, never a note's words): "Sent 3 follow-ups to the client".
"""

from collections import namedtuple

from deals import activity

from ..models import ReviewNote
from ..portal import asked as asked_rules
from ..rules import join as join_rules
from ..rules import policy
from ..rules import tray as tray_rules
from . import common

Delivered = namedtuple('Delivered', 'request added links activity')

TOO_MANY = 'That is more census values than one link can ask one by one: ask for their census file instead.'


class NeedsNew(Exception):
    """The request cannot take these: a new link must (its words say why)."""

    def __init__(self, why):
        super().__init__(why)
        self.why = why


def carried(deal, request, link, siblings):
    """Every ref a link on `request` asks now, its files included."""
    return asked_rules.carried(asked_rules.asked(link, request, deal, link_ids=[row.id for row in siblings]))


def _join(deal, request, live, links, items, now):
    refs = [item.ref for item in items]
    missing = [ref for ref in refs if ref not in carried(deal, request, live[0], links)]
    if not missing:
        return []
    try:
        asks, added = join_rules.join(request.asks, missing)
    except join_rules.TooMany:
        raise NeedsNew(TOO_MANY) from None
    if not added:
        return []
    level = policy.floor(asks)['level']
    if policy.RANK[level] > policy.RANK[tray_rules.weakest(links, now)]:
        raise NeedsNew(tray_rules.NEEDS_PIN)
    request.asks = asks
    request.form_version += 1
    request.save(update_fields=['asks', 'form_version'])
    return added


def _revive(live, now):
    for link in live:
        moved = policy.renewed(link.expires_at, link.ceiling_at, now)
        if moved != link.expires_at:
            link.expires_at = moved
            link.save(update_fields=['expires_at'])


def _plural(count, noun):
    return f'{count} {noun}{"" if count == 1 else "s"}'


def deliver(user, request_id, notes, items, now, *, summary=None, revive=True):
    """Delivered(request, [refs joined], [live link], Activity row). Raises NeedsNew, or Refused (409)."""
    deal, request = common.locked_request(request_id)
    common.refuse_unless_asking(deal, request)
    links = list(request.links.select_for_update().order_by('id'))
    live = tray_rules.live_links(links, now)
    if not live:
        raise NeedsNew(tray_rules.NEEDS_LINK)
    added = _join(deal, request, live, links, items, now)
    if revive:
        _revive(live, now)
    for note in notes:
        note.request_id, note.sent_at = request.id, now
    ReviewNote.objects.bulk_update(notes, ['request', 'sent_at'])
    keys = sorted({item.ref for item in items})
    words = summary or f'Sent {_plural(len(notes), "follow-up")} to the client'
    change = activity.change(common.request_target(request), keys)
    row = activity.record(
        deal, user, common.AREA, 'followed_up', words, changes=[change], keys_only=True, revertible=False
    )
    return Delivered(request, added, live, row)
