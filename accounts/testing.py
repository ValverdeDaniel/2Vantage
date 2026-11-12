"""A fake OpenID provider: Entra ID's side of Microsoft 365 sign-in, in memory (plan.md §12.1, Q.2; slice 47).

Installed with `accounts.oidc.install(provider)`, it answers the discovery document, the key set and the token endpoint
as Entra does, and signs ID tokens with its own RSA key, so the real verification runs on every test sign-in and
nothing leaves the machine. `sign_in_as(email)` is the person at Microsoft's page; `approve(authorize_url)` is the
browser going there and coming back: it checks what the app asked for and returns the callback's path with a code.
The token endpoint checks the client secret, the redirect URI, the single-use code and the PKCE verifier. `claims`
changes the next ID token (a value of None leaves the claim out); `forge` signs it another way.
"""

import base64
import hashlib
import json
import time
from functools import cache
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt
import requests
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

TENANT = 'f1a2b3c4-0000-4000-8000-000000000047'
ISSUER = f'https://login.example.test/{TENANT}/v2.0'
CLIENT_ID = 'client-2vantage-test'
CLIENT_SECRET = 'not-a-real-secret-only-the-fake-provider-knows'
REDIRECT_URI = 'http://testserver/api/auth/microsoft/callback/'
KID = 'fake-signing-key'


def settings_on(**extra):
    """The settings that turn Microsoft 365 sign-in on against this provider."""
    return {
        'AUTH_OIDC': True,
        'AUTH_OIDC_ISSUER': ISSUER,
        'AUTH_OIDC_TENANT_ID': TENANT,
        'AUTH_OIDC_CLIENT_ID': CLIENT_ID,
        'AUTH_OIDC_CLIENT_SECRET': CLIENT_SECRET,
        'AUTH_OIDC_REDIRECT_URI': REDIRECT_URI,
        **extra,
    }


@cache
def private_key(name=KID):
    """One RSA key per name for the whole test run (making one takes a moment)."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _s256(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()


class FakeProvider:
    def __init__(self, issuer=ISSUER, tenant=TENANT):
        self.issuer, self.tenant = issuer, tenant
        self.base = issuer.removesuffix('/v2.0')
        self.email, self.claims, self.forge = None, {}, None
        self.down = False
        self.codes = {}
        self.calls = []

    # ---- what the provider publishes ----------------------------------------------------------------------------
    def discovery(self):
        return {
            'issuer': self.issuer,
            'authorization_endpoint': f'{self.base}/oauth2/v2.0/authorize',
            'token_endpoint': f'{self.base}/oauth2/v2.0/token',
            'jwks_uri': f'{self.base}/discovery/v2.0/keys',
            'response_types_supported': ['code'],
            'id_token_signing_alg_values_supported': ['RS256'],
        }

    def jwks(self):
        public = json.loads(RSAAlgorithm.to_jwk(private_key().public_key()))
        return {'keys': [{**public, 'kid': KID, 'use': 'sig'}]}

    # ---- the transport the app calls (accounts.oidc.Transport's two methods) --------------------------------------
    def get_json(self, url):
        self.calls.append(('GET', url))
        if self.down:
            raise requests.ConnectionError('the provider is down')
        meta = self.discovery()
        if url == f'{self.issuer}/.well-known/openid-configuration':
            return meta
        if url == meta['jwks_uri']:
            return self.jwks()
        raise requests.HTTPError(f'404 {url}')

    def post_form(self, url, data):
        self.calls.append(('POST', url))
        if self.down:
            raise requests.ConnectionError('the provider is down')
        grant = self.codes.pop(data.get('code'), None)
        checks = (
            url == self.discovery()['token_endpoint'],
            data.get('grant_type') == 'authorization_code',
            data.get('client_id') == CLIENT_ID and data.get('client_secret') == CLIENT_SECRET,
            grant is not None and data.get('redirect_uri') == grant['redirect_uri'],
            grant is not None and _s256(str(data.get('code_verifier', ''))) == grant['challenge'],
        )
        if not all(checks):
            return 400, {'error': 'invalid_grant'}
        return 200, {'token_type': 'Bearer', 'access_token': 'opaque', 'id_token': self.id_token(grant['nonce'])}

    # ---- the person and the browser -----------------------------------------------------------------------------
    def sign_in_as(self, email, **claims):
        self.email, self.claims = email, claims
        return self

    def approve(self, authorize_url, error=None):
        """The browser at Microsoft's page and back: the callback's path and query, with a code (or the `error`)."""
        parts = urlsplit(authorize_url)
        assert f'{parts.scheme}://{parts.netloc}{parts.path}' == self.discovery()['authorization_endpoint']
        asked = {key: values[0] for key, values in parse_qs(parts.query).items()}
        assert asked['client_id'] == CLIENT_ID and asked['response_type'] == 'code'
        assert asked['code_challenge_method'] == 'S256' and 'openid' in asked['scope'].split()
        back = urlsplit(asked['redirect_uri'])
        if error:
            return f'{back.path}?{urlencode({"error": error, "state": asked["state"]})}'
        code = f'code-{len(self.codes) + 1}-{asked["state"][:8]}'
        self.codes[code] = {
            'challenge': asked['code_challenge'],
            'redirect_uri': asked['redirect_uri'],
            'nonce': asked['nonce'],
        }
        return f'{back.path}?{urlencode({"code": code, "state": asked["state"]})}'

    def id_token(self, nonce):
        now = int(time.time())
        claims = {
            'iss': self.issuer,
            'aud': CLIENT_ID,
            'sub': f'sub-{self.email}',
            'tid': self.tenant,
            'oid': f'oid-{self.email}',
            'email': self.email,
            'preferred_username': self.email,
            'name': 'Synthetic Firm Person',
            'nonce': nonce,
            'iat': now,
            'nbf': now,
            'exp': now + 3600,
        }
        claims.update(self.claims)
        claims = {key: value for key, value in claims.items() if value is not None}
        if self.forge == 'other_key':
            return jwt.encode(claims, private_key('other'), algorithm='RS256', headers={'kid': KID})
        if self.forge == 'hs256':  # the classic: the client secret as an HMAC key
            return jwt.encode(claims, CLIENT_SECRET, algorithm='HS256', headers={'kid': KID})
        if self.forge == 'none':
            head = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b'=').decode()
            body = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b'=').decode()
            return f'{head}.{body}.'
        if self.forge == 'unknown_kid':
            return jwt.encode(claims, private_key(), algorithm='RS256', headers={'kid': 'rotated-away'})
        return jwt.encode(claims, private_key(), algorithm='RS256', headers={'kid': KID})
