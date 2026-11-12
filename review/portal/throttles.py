"""The portal's rates, kept per link (plan.md §3.5, §7.14; L110, B2): `portal_read` 300/hour for the page and its
files, `portal_write` 3,600/hour for saves, uploads and the rest, `portal_poll` 600/hour for the stamp, and `portal_pin`
10/hour for PIN tries on top of the five-try lock. Each scope keeps its own count, so polling never uses up a save;
the global anonymous rate never applies (the portal's views name only these). The count is keyed by the token's
hash, never the token. The moved page (no token) counts by address.
"""

from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle

from .. import tokens


class LinkThrottle(SimpleRateThrottle):
    scope = None

    def get_rate(self):
        # Read now, not when the class was made, so a setting changed in a test takes effect.
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope)

    def get_cache_key(self, request, view):
        token = (getattr(view, 'kwargs', None) or {}).get('token')
        ident = tokens.digest(token)[:32] if token else self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class Read(LinkThrottle):
    scope = 'portal_read'


class Write(LinkThrottle):
    scope = 'portal_write'


class Poll(LinkThrottle):
    scope = 'portal_poll'


class Pin(LinkThrottle):
    scope = 'portal_pin'
