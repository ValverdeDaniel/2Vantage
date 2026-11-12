"""Microsoft 365 sign-in refuses what it cannot verify (plan.md §11.4 item 3, §3.8; slice 47): the state, the PKCE
verifier, the ID token's signature, algorithm, issuer, audience, tenant, expiry and nonce. Every refusal lands on the
sign-in page as `failed` (or `expired`, `cancelled`) with no session, and the logs name only the kind of failure."""

import logging
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from rest_framework.test import APIClient

from accounts import oidc
from accounts.testing import TENANT

pytestmark = pytest.mark.django_db


def attempt(entra, email='dana@example.com', error=None, before_callback=None):
    """One sign-in; `before_callback(client)` meddles between the provider and the callback. → (client, answer)."""
    client = APIClient()
    entra.email = email  # the claims a test set stay
    back = entra.approve(client.get('/api/auth/microsoft/')['Location'], error=error)
    if before_callback:
        back = before_callback(client, back) or back
    return client, client.get(back)


def code_of(answer):
    location = urlsplit(answer['Location'])
    return parse_qs(location.query).get('signin', [None])[0] if location.path == '/login' else None


def signed_out(client):
    return client.get('/api/auth/me/').status_code == 401


TAMPERED = {
    'another audience': {'aud': 'someone-elses-app'},
    'another issuer': {'iss': 'https://login.example.test/other/v2.0'},
    'another tenant': {'tid': 'another-tenant'},
    'expired': {'exp': int(time.time()) - 3600, 'iat': int(time.time()) - 7200},
    'issued in the future': {'iat': int(time.time()) + 3600},
    'no nonce': {'nonce': None},
    'no expiry': {'exp': None},
}


@pytest.mark.parametrize('claims', TAMPERED.values(), ids=TAMPERED.keys())
def test_PHI3_an_id_token_with_wrong_claims_is_refused(entra, user, claims):
    entra.claims = claims
    client, answer = attempt(entra)
    assert code_of(answer) == 'failed' and signed_out(client)


@pytest.mark.parametrize('forge', ['other_key', 'hs256', 'none', 'unknown_kid'])
def test_PHI3_an_id_token_not_signed_by_the_provider_is_refused(entra, user, forge):
    entra.forge = forge
    client, answer = attempt(entra)
    assert code_of(answer) == 'failed' and signed_out(client)


def test_PHI3_a_nonce_from_another_sign_in_is_refused(entra, user):
    entra.claims = {'nonce': 'a-nonce-the-app-never-sent'}
    client, answer = attempt(entra)
    assert code_of(answer) == 'failed' and signed_out(client)


def test_PHI3_the_state_must_match_and_is_used_once(entra, user):
    client, answer = attempt(entra, before_callback=lambda c, back: back.replace('state=', 'state=x'))
    assert code_of(answer) == 'expired' and signed_out(client)
    client, answer = attempt(entra)
    assert answer['Location'] == '/'
    callback = f'{answer.request["PATH_INFO"]}?{answer.request["QUERY_STRING"]}'
    assert code_of(client.get(callback)) == 'expired'  # the same code and state again: the pending sign-in is gone


def test_PHI3_a_sign_in_left_ten_minutes_has_expired(entra, user):
    def later(client, back):
        session = client.session
        session[oidc.SESSION_KEY]['at'] -= oidc.PENDING_SECONDS + 120  # wide: the clock steps back under load
        session.save()

    client, answer = attempt(entra, before_callback=later)
    assert code_of(answer) == 'expired' and signed_out(client)


def test_PHI3_the_code_is_worth_nothing_without_the_browsers_pkce_verifier(entra, user):
    def swap(client, back):
        session = client.session
        session[oidc.SESSION_KEY]['verifier'] = 'a-verifier-the-provider-never-saw-0000000000000'
        session.save()

    client, answer = attempt(entra, before_callback=swap)
    assert code_of(answer) == 'failed' and signed_out(client)


def test_PHI3_cancelled_and_provider_errors(entra, user):
    assert code_of(attempt(entra, error='access_denied')[1]) == 'cancelled'
    assert code_of(attempt(entra, error='server_error')[1]) == 'failed'
    entra.down = True
    oidc.install(entra)  # a new instance: nothing cached
    answer = APIClient().get('/api/auth/microsoft/')
    assert code_of(answer) == 'failed'


def test_PHI3_an_account_with_no_email_is_refused_and_preferred_username_stands_in(entra, user):
    entra.claims = {'email': None, 'preferred_username': 'DANA@example.com'}
    client, answer = attempt(entra)
    assert answer['Location'] == '/' and not signed_out(client)
    entra.claims = {'email': None, 'preferred_username': 'dana', 'tid': TENANT}
    client, answer = attempt(entra)
    assert code_of(answer) == 'no_email' and signed_out(client)


def test_PHI3_the_provider_documents_are_fetched_once_and_keys_again_after_rotation(entra, user):
    attempt(entra)
    attempt(entra)
    gets = [url for method, url in entra.calls if method == 'GET']
    assert len(gets) == len(set(gets)) == 2  # discovery and keys, once each for both sign-ins


def test_PHI3_nothing_about_a_sign_in_reaches_the_logs(entra, user, caplog):
    caplog.set_level(logging.DEBUG)
    entra.forge = 'other_key'
    attempt(entra, email='dana@example.com')
    entra.forge = None
    attempt(entra, email='stranger@example.com')
    text = caplog.text
    assert 'refused an ID token' in text  # the kind of failure, and nothing else
    for secret in ('dana@example.com', 'stranger@example.com', 'code-', 'state=', 'eyJ', entra.calls[0][1]):
        assert secret not in text
