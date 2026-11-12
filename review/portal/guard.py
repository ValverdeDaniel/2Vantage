"""Who may open a client link, and what they may do on it (plan.md §7.14, §3.8; L77, L78, L105, L107; OQ80; rule 11).

`open_link(request, token, write=…)` answers every portal door the same way:
- an unknown token is 404 `{"detail": "This link isn't valid."}` (a malformed one never reaches the database);
- a link turned off, run out, or on a closed request is 410, carrying the agency's name, phone and email and never an
  owner's (L107);
- a write on a lost or archived deal, or a past year, is also 410 (`deals.rules.client_asks_open`); the page stays
  readable (L105);
- a PIN link answers 428 until the browser proves the PIN (`verify/`), then sends the verification token in
  `X-Link-Verification`: Django's TimestampSigner over {link, pin_version, first}, good for an hour idle under an
  eight-hour ceiling and issued again with each answer; a New PIN (`pin_version`) ends it (L77);
- a staff session (Django's own session, read from the request itself: the portal has no DRF authentication) sees the
  page without the PIN, records no open, and every write answers 403 (L78, Ch. 10).
"""

import re
import time
from collections import namedtuple

from django.contrib import auth
from django.core import signing
from rest_framework import status
from rest_framework.exceptions import APIException

from deals import clock, rules
from deals.models import AgencySettings

from .. import tokens
from ..models import ClientLink
from ..rules import policy

TOKEN = re.compile(r'^[A-Za-z0-9_-]{43}$')
HEADER = 'X-Link-Verification'
SALT = 'review.portal.verify'
IDLE = 60 * 60  # seconds a verification lasts without a request (L.6)
CEILING = 8 * 60 * 60  # and at most, from the PIN

UNKNOWN = "This link isn't valid."
EXPIRED = 'This link has expired. Please ask your benefits contact for a new one.'
CLOSED = 'This link no longer takes answers. Please ask your benefits contact if you need to send anything.'
PIN_NEEDED = 'Enter the PIN you were given to open this link.'
LOCKED = 'This link is locked after too many wrong PINs. Ask whoever sent it to you for a new PIN.'
STAFF = "You're signed in to 2Vantage, so nothing here is saved as the client's answer. Use View as client to look."

Opened = namedtuple('Opened', 'link request deal staff verification')


def agency():
    """The agency's contact, the only "who to ask" a client link ever names (L107)."""
    row = AgencySettings.get()
    return {'name': row.name, 'phone': row.phone, 'email': row.email}


class Answer(APIException):
    """A refusal whose body keeps its types (DRF would turn a flag or a list into text)."""

    def __init__(self, body):
        super().__init__(body)
        self.detail = body


class Unknown(Answer):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'not_found'

    def __init__(self):
        super().__init__({'detail': UNKNOWN})


class Gone(Answer):
    status_code = status.HTTP_410_GONE
    default_code = 'gone'

    def __init__(self, sentence=EXPIRED):
        super().__init__({'detail': sentence, 'agency': agency()})


class NeedsPin(Answer):
    status_code = status.HTTP_428_PRECONDITION_REQUIRED
    default_code = 'pin_required'

    def __init__(self, locked=False):
        body = {'detail': LOCKED if locked else PIN_NEEDED, 'verification': 'required', 'kind': 'pin', 'locked': locked}
        super().__init__({**body, 'agency': agency()})


class StaffWrite(Answer):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'staff'

    def __init__(self):
        super().__init__({'detail': STAFF})


def find(token):
    """The link a token opens, with its request and deal, or Unknown."""
    if not TOKEN.match(str(token or '')):
        raise Unknown()
    link = ClientLink.objects.select_related('request__deal__client').filter(token_hash=tokens.digest(token)).first()
    if link is None:
        raise Unknown()
    return link


def staff_user(request):
    """The signed-in staff user of this browser, read from Django's session itself (never a DRF authenticator: with
    none, DRF sets the request's user to anonymous), or None."""
    user = auth.get_user(getattr(request, '_request', request))
    return user if user.is_authenticated and user.is_active else None


def issue(link, first=None):
    """A verification token for `link`; `first` keeps the eight-hour ceiling from the PIN."""
    return signing.TimestampSigner(salt=SALT).sign_object(
        {'l': link.id, 'v': link.pin_version, 'f': first or int(time.time())}
    )


def verified(link, presented):
    """The `first` of a good verification token for this link, else None."""
    if not presented:
        return None
    try:
        data = signing.TimestampSigner(salt=SALT).unsign_object(presented, max_age=IDLE)
    except (signing.BadSignature, ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get('l') != link.id or data.get('v') != link.pin_version:
        return None
    first = data.get('f')
    if not isinstance(first, int) or time.time() - first > CEILING:
        return None
    return first


def open_link(request, token, *, write=False):
    """Opened(link, request, deal, staff user or None, a fresh verification token or '') or one of the refusals."""
    link = find(token)
    asked, deal = link.request, link.request.deal
    if not policy.opens(link, clock.now(), closed=asked.closed_at is not None):
        raise Gone()
    staff = staff_user(request)
    if write and staff is not None:
        raise StaffWrite()
    if write and rules.client_asks_open(deal):
        raise Gone(CLOSED)
    renewed = ''
    if link.security == policy.PIN and staff is None:
        first = verified(link, request.headers.get(HEADER))
        if first is None:
            raise NeedsPin(locked=link.pin_tries >= policy.PIN_TRIES)
        renewed = issue(link, first)
    return Opened(link, asked, deal, staff, renewed)
