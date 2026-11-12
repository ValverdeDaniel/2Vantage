"""A link's PIN (plan.md §3.8; L64, L77; OQ80): six digits, shown once to the person who made it, stored only as a
hash, locked after five wrong tries until a person makes a new one.

`issue(link)` sets a new PIN on a row the caller holds locked and returns it: the old one stops working, the wrong
tries start over and `pin_version` moves on, so whoever had proved the old PIN proves the new one (the portal's
verification token carries the version; slice 54). `check(link_id, pin)` is the portal's door: it counts a wrong try
under the link's lock, so two tabs cannot both spend the last one.
"""

import secrets
from collections import namedtuple

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction

from ..models import ClientLink
from ..rules import policy

OK, WRONG, LOCKED, NONE = 'ok', 'wrong', 'locked', 'none'
Checked = namedtuple('Checked', 'outcome tries_left')


def make():
    return f'{secrets.randbelow(10**policy.PIN_DIGITS):0{policy.PIN_DIGITS}d}'


def issue(link):
    """A new PIN on `link` (in memory; the caller saves `pin_hash`, `pin_tries` and `pin_version`). Returns it."""
    pin = make()
    link.pin_hash = make_password(pin)
    link.pin_tries = 0
    link.pin_version += 1
    return pin


@transaction.atomic
def check(link_id, pin):
    """Checked(ok | wrong | locked | none, tries left). A wrong PIN is counted and kept; `none`: the link asks for no
    PIN, or has none yet."""
    link = ClientLink.objects.select_for_update().get(pk=link_id)
    if link.security != policy.PIN or not link.pin_hash:
        return Checked(NONE, 0)
    if link.pin_tries >= policy.PIN_TRIES:
        return Checked(LOCKED, 0)
    pin = str(pin or '').strip()
    if not pin or not check_password(pin, link.pin_hash):
        link.pin_tries += 1
        link.save(update_fields=['pin_tries'])
        left = max(policy.PIN_TRIES - link.pin_tries, 0)
        return Checked(LOCKED if left == 0 else WRONG, left)
    if link.pin_tries:
        link.pin_tries = 0
        link.save(update_fields=['pin_tries'])
    return Checked(OK, policy.PIN_TRIES)
