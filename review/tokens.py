"""A client link's token (plan.md §6.12, §7.14; L.6, L77): 43 URL-safe characters, the only thing in its URL.

The token is never stored. A link's row keeps a random `seed` and the token's SHA-256 (`token_hash`, unique): the
token is the seed signed with the server's key (Django's `salted_hmac` over SECRET_KEY), so staff can copy the same
link again for as long as it lives, while a copy of the database alone opens nothing. The portal (slice 54) finds a
link by `digest(token)`; nothing else ever reads a token, and no log, Activity row, error or staff URL carries one
(logs drop `/portal/` paths, backend/logs.py).

Rotating SECRET_KEY ends every open link (its token no longer matches, so it answers 404): a link lives at most 30
days, and a new one is a click away.
"""

import base64
import hashlib
import secrets

from django.utils.crypto import salted_hmac

SALT = 'review.ClientLink.token'
PATH = '/portal/'  # the client's page; the browser puts its own origin in front (plan.md §8.20)


def new_seed():
    return secrets.token_hex(16)


def token_of(seed):
    """The link's token: 32 bytes of HMAC-SHA256 over its seed, URL-safe base64 without padding (43 characters)."""
    raw = salted_hmac(SALT, seed, algorithm='sha256').digest()
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def digest(token):
    """What the row stores and the portal looks a token up by."""
    return hashlib.sha256(str(token).encode('utf-8')).hexdigest()


def path_of(seed):
    """`/portal/<token>`: what Copy link copies, after the browser's origin."""
    return f'{PATH}{token_of(seed)}'
