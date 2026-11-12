"""What a person does to one link (plan.md §7.13 `PATCH links/{id}/`; L8, L60–L64, L71). Each action locks the Deal,
the request and the link in that order, writes one Activity row with each field's before and after, and returns only
what changed; asking again for what is already so changes nothing.

- `mark_sent` (Copy link copies first, then marks it; `copied=True` words the row "Copied") and `unsend` ("Not sent
  after all"), refused once the link was opened or sent back (L71): it demonstrably went out.
- `extend`: the link lives its own life again from now, within its 30-day ceiling, even after it ran out (L58).
- `revoke` ("Turn off"): it stops opening now; what the client said stays. Allowed on a lost or past deal and on a
  closed request, since it asks nobody for anything. `restore` ("Turn back on"): the same URL, its own life from now,
  refused past the ceiling (L60).
- `new_pin`: a new PIN for a PIN link, shown this once; the old one stops working and a locked link opens again.

Every action but `revoke` and `unsend` is refused (409) once the deal may no longer ask its client or the request is
closed. `ACTIONS` is the PATCH's dispatch table.
"""

from collections import namedtuple

from django.db import transaction

from deals import activity, clock

from .. import words
from ..rules import policy
from . import common, pins

Acted = namedtuple('Acted', 'link request changed activity pin', defaults=('',))


def _unchanged(link, request):
    return Acted(link, request, {}, None)


def _done(deal, user, link, request, action, summary, diff, fields, *, revertible=True, pin=''):
    link.save(update_fields=fields)
    row = common.record(deal, user, action, summary, common.link_target(link), diff, revertible=revertible)
    return Acted(link, request, diff, row, pin)


@transaction.atomic
def mark_sent(user, link_id, *, copied=False):
    deal, request, link = common.locked_link(link_id)
    if link.sent_at is not None:
        return _unchanged(link, request)
    common.refuse_unless_asking(deal, request)
    now = clock.now()
    diff = {'sent_at': [None, common.iso(now)]}
    link.sent_at = now
    summary = 'Copied a client link' if copied else 'Marked a client link as sent'
    return _done(deal, user, link, request, 'sent', summary, diff, ['sent_at'])


@transaction.atomic
def unsend(user, link_id):
    deal, request, link = common.locked_link(link_id)
    if link.sent_at is None:
        return _unchanged(link, request)
    if link.opened_at is not None or link.submitted_at is not None:
        raise activity.Refused(words.OPENED)
    diff = {'sent_at': [common.iso(link.sent_at), None]}
    link.sent_at = None
    return _done(deal, user, link, request, 'unsent', 'Put a client link back to not sent', diff, ['sent_at'])


@transaction.atomic
def extend(user, link_id):
    deal, request, link = common.locked_link(link_id)
    common.refuse_unless_asking(deal, request)
    if link.revoked_at is not None:
        raise activity.Refused(words.LINK_OFF)
    now = clock.now()
    if not policy.can_renew(link, now):
        raise activity.Refused(words.NO_LONGER)
    moved = policy.renewed(link.expires_at, link.ceiling_at, now)
    if moved == link.expires_at:
        if link.expires_at >= link.ceiling_at:
            raise activity.Refused(words.NO_LONGER)
        return _unchanged(link, request)
    diff = {'expires_at': [common.iso(link.expires_at), common.iso(moved)]}
    link.expires_at = moved
    return _done(deal, user, link, request, 'extended', 'Extended a client link', diff, ['expires_at'])


@transaction.atomic
def revoke(user, link_id):
    deal, request, link = common.locked_link(link_id)
    if link.revoked_at is not None:
        return _unchanged(link, request)
    now = clock.now()
    diff = {'revoked_at': [None, common.iso(now)], 'revoked_by': [None, common.user_id(user)]}
    link.revoked_at, link.revoked_by_id = now, common.user_id(user)
    return _done(deal, user, link, request, 'revoked', 'Turned a client link off', diff, ['revoked_at', 'revoked_by'])


@transaction.atomic
def restore(user, link_id):
    deal, request, link = common.locked_link(link_id)
    if link.revoked_at is None:
        return _unchanged(link, request)
    common.refuse_unless_asking(deal, request)
    now = clock.now()
    if not policy.can_renew(link, now):
        raise activity.Refused(words.PAST_LIMIT)
    moved = policy.renewed(link.expires_at, link.ceiling_at, now)
    diff = {'revoked_at': [common.iso(link.revoked_at), None], 'revoked_by': [link.revoked_by_id, None]}
    if moved != link.expires_at:
        diff['expires_at'] = [common.iso(link.expires_at), common.iso(moved)]
    link.revoked_at, link.revoked_by_id, link.expires_at = None, None, moved
    fields = ['revoked_at', 'revoked_by', 'expires_at']
    return _done(deal, user, link, request, 'restored', 'Turned a client link back on', diff, fields)


@transaction.atomic
def new_pin(user, link_id):
    deal, request, link = common.locked_link(link_id)
    common.refuse_unless_asking(deal, request)
    if link.revoked_at is not None:
        raise activity.Refused(words.LINK_OFF)
    if link.security != policy.PIN:
        raise activity.Refused(words.NOT_PIN)
    before = link.pin_version
    pin = pins.issue(link)
    diff = {'pin_version': [before, link.pin_version]}
    fields = ['pin_hash', 'pin_tries', 'pin_version']
    summary = 'Made a new PIN for a client link'
    return _done(deal, user, link, request, 'pin', summary, diff, fields, revertible=False, pin=pin)


ACTIONS = {
    'mark_sent': mark_sent,
    'unsend': unsend,
    'extend': extend,
    'revoke': revoke,
    'restore': restore,
    'new_pin': new_pin,
}
