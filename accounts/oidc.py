"""Microsoft 365 sign-in: OpenID Connect's authorization code flow with PKCE (plan.md §3.8, §7.2, §11.4; slice 47).

The provider is the firm's Entra ID directory, spoken to only in standard OpenID Connect, so any OpenID provider
answers the same way (the tests' fake in accounts/testing.py). Two steps, both in the browser:
- `begin(session, next_path)` keeps one pending sign-in in the session (state, nonce, the PKCE verifier, where to go
  afterwards; ten minutes) and returns the provider's authorize URL;
- `finish(session, query)` takes it back once, trades the code at the token endpoint for an ID token (with the
  client secret and the verifier) and verifies the token with PyJWT: RS256 only, signed by a key of the provider's
  published set, issued by the configured issuer to this client, unexpired, carrying our nonce and, for Entra, the
  firm's tenant. It returns the account's email and where to go, or raises `Refused` with a code (accounts.firm).
Server-side calls are the discovery document, the key set (both kept an hour) and the token exchange, through the
`install`able transport: tests install the fake provider and never touch the network (Q.2). Nothing is logged but
the kind of failure: no token, code, email or provider message.
"""

import base64
import hashlib
import hmac
import logging
import secrets
import time
from urllib.parse import urlencode

import jwt
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SESSION_KEY = 'm365_signin'
PENDING_SECONDS = 600
CACHE_SECONDS = 3600
REFETCH_SECONDS = 300  # an unknown key id refetches the key set at most this often (the provider rotated its keys)
LEEWAY_SECONDS = 120  # clock skew allowed on exp and iat
SCOPE = 'openid email profile'
ALGORITHM = 'RS256'
REQUIRED_CLAIMS = ['exp', 'iat', 'iss', 'aud', 'sub', 'nonce']
EMAIL_CLAIMS = ('email', 'preferred_username', 'upn')


class Refused(Exception):
    """A sign-in that ends without a session; `code` is a key of accounts.firm.REFUSALS."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class Transport:
    """HTTPS through requests: certificates verified, redirects not followed, ten seconds at most."""

    timeout = 10

    def get_json(self, url):
        response = requests.get(url, timeout=self.timeout, allow_redirects=False)
        response.raise_for_status()
        return response.json()

    def post_form(self, url, data):
        """(status, JSON body or {}) of a form POST: the token endpoint answers errors as JSON too."""
        response = requests.post(url, data=data, timeout=self.timeout, allow_redirects=False)
        try:
            return response.status_code, response.json()
        except ValueError:
            return response.status_code, {}


_transport = Transport()
_cache = {}


def install(transport):
    """Use `transport` for every provider call (tests: the fake provider). Returns the old one; clears the cache."""
    global _transport
    previous, _transport = _transport, transport
    _cache.clear()
    return previous


def _cached(key, fetch, max_age=CACHE_SECONDS):
    held = _cache.get(key)
    if held and time.monotonic() - held[0] < max_age:
        return held[1]
    value = fetch()
    _cache[key] = (time.monotonic(), value)
    return value


def _call(fetch):
    """A provider call; a failure to reach it, or an answer that is not JSON, is the sign-in's failure."""
    try:
        return fetch()
    except (requests.RequestException, ValueError) as error:
        logger.warning('Microsoft 365 sign-in could not reach the provider (%s).', type(error).__name__)
        raise Refused('failed') from None


def _metadata():
    issuer = settings.AUTH_OIDC_ISSUER

    def discover():
        meta = _call(lambda: _transport.get_json(f'{issuer}/.well-known/openid-configuration'))
        if str(meta.get('issuer', '')).rstrip('/') != issuer:
            logger.warning('Microsoft 365 sign-in: the discovery document names another issuer.')
            raise Refused('failed')
        return meta

    return _cached(('metadata', issuer), discover)


def _challenge(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()


def begin(session, next_path):
    """Keep a pending sign-in in the session and return the provider's authorize URL."""
    meta = _metadata()
    state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
    session[SESSION_KEY] = {'state': state, 'nonce': nonce, 'verifier': verifier, 'next': next_path, 'at': time.time()}
    query = {
        'client_id': settings.AUTH_OIDC_CLIENT_ID,
        'response_type': 'code',
        'response_mode': 'query',
        'redirect_uri': settings.AUTH_OIDC_REDIRECT_URI,
        'scope': SCOPE,
        'state': state,
        'nonce': nonce,
        'code_challenge': _challenge(verifier),
        'code_challenge_method': 'S256',
        'prompt': 'select_account',
    }
    return f'{meta["authorization_endpoint"]}?{urlencode(query)}'


def _pending(session, state):
    pending = session.pop(SESSION_KEY, None)
    if not isinstance(pending, dict) or time.time() - float(pending.get('at', 0)) > PENDING_SECONDS:
        raise Refused('expired')
    if not hmac.compare_digest(str(state or ''), str(pending.get('state', ''))):
        raise Refused('expired')
    return pending


def _signing_key(jwks_uri, kid):
    for max_age in (CACHE_SECONDS, REFETCH_SECONDS):
        keys = _cached(('jwks', jwks_uri), lambda: _call(lambda: _transport.get_json(jwks_uri)), max_age)
        for found in keys.get('keys', []):
            if found.get('kid') == kid and found.get('kty') == 'RSA' and found.get('use', 'sig') == 'sig':
                return jwt.PyJWK(found, algorithm=ALGORITHM).key
    raise jwt.InvalidTokenError('no published key has this key id')


def _verify(id_token, meta, nonce):
    try:
        header = jwt.get_unverified_header(id_token)
        if header.get('alg') != ALGORITHM:
            raise jwt.InvalidAlgorithmError('not RS256')
        claims = jwt.decode(
            id_token,
            _signing_key(meta['jwks_uri'], header.get('kid')),
            algorithms=[ALGORITHM],
            audience=settings.AUTH_OIDC_CLIENT_ID,
            issuer=meta['issuer'],
            leeway=LEEWAY_SECONDS,
            options={'require': REQUIRED_CLAIMS},
        )
    except jwt.PyJWTError as error:
        logger.warning('Microsoft 365 sign-in refused an ID token (%s).', type(error).__name__)
        raise Refused('failed') from None
    tenant = settings.AUTH_OIDC_TENANT_ID
    if not hmac.compare_digest(str(claims.get('nonce')), nonce) or (tenant and claims.get('tid') != tenant):
        logger.warning('Microsoft 365 sign-in refused an ID token (nonce or tenant).')
        raise Refused('failed')
    return claims


def email_of(claims):
    """The account's email: `email`, else the user principal name Entra sends as `preferred_username`."""
    for name in EMAIL_CLAIMS:
        value = str(claims.get(name) or '').strip().lower()
        if '@' in value:
            return value
    raise Refused('no_email')


def finish(session, query):
    """(email, next path) of the account the provider signed in; raises `Refused`."""
    pending = _pending(session, query.get('state'))
    if query.get('error'):
        raise Refused('cancelled' if query.get('error') == 'access_denied' else 'failed')
    if not query.get('code'):
        raise Refused('failed')
    meta = _metadata()
    form = {
        'grant_type': 'authorization_code',
        'code': query['code'],
        'redirect_uri': settings.AUTH_OIDC_REDIRECT_URI,
        'client_id': settings.AUTH_OIDC_CLIENT_ID,
        'client_secret': settings.AUTH_OIDC_CLIENT_SECRET,
        'code_verifier': pending['verifier'],
    }
    status, body = _call(lambda: _transport.post_form(meta['token_endpoint'], form))
    if status != 200 or not isinstance(body.get('id_token'), str):
        logger.warning('Microsoft 365 sign-in: the token endpoint answered %s.', status)
        raise Refused('failed')
    return email_of(_verify(body['id_token'], meta, pending['nonce'])), pending.get('next') or '/'
