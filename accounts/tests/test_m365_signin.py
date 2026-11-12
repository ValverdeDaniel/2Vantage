"""Microsoft 365 sign-in, the PHI gate's item 3 (plan.md §11.4, §3.8, §7.2; slice 47): a firm account signs in through
the provider and becomes the one active user with its email; nobody is made; refusals land on the sign-in page with a
sentence; turning password sign-in off leaves Microsoft 365 as the only way in. Against the fake provider only."""

from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts import firm, oidc
from accounts.testing import REDIRECT_URI

pytestmark = pytest.mark.django_db
User = get_user_model()


def start(client, next_path=None):
    """The sign-in page's button: GET auth/microsoft/ → the authorize URL the browser is sent to."""
    answer = client.get('/api/auth/microsoft/', {'next': next_path} if next_path else {})
    assert answer.status_code == 302, answer.status_code
    return answer['Location']


def sign_in(entra, email, next_path=None, client=None):
    """A whole Microsoft 365 sign-in in one browser. Returns (client, the callback's answer)."""
    client = client or APIClient()
    entra.sign_in_as(email)
    return client, client.get(entra.approve(start(client, next_path)))


def refused(answer):
    assert answer.status_code == 302
    location = urlsplit(answer['Location'])
    assert location.path == '/login'
    return parse_qs(location.query)['signin'][0]


def test_PHI3_a_firm_account_signs_in_as_the_user_with_its_email(entra, user):
    users = User.objects.count()
    client = APIClient()
    url = start(client, '/deals/12/census')
    authorize, asked = urlsplit(url), parse_qs(urlsplit(url).query)
    assert f'{authorize.scheme}://{authorize.netloc}{authorize.path}' == entra.discovery()['authorization_endpoint']
    assert asked['code_challenge_method'] == ['S256'] and asked['response_type'] == ['code']
    assert asked['redirect_uri'] == [REDIRECT_URI] and set(asked['scope'][0].split()) >= {'openid', 'email'}
    entra.sign_in_as('Dana@Example.com')  # Entra's spelling; the user was added as dana@example.com
    answer = client.get(entra.approve(url))
    assert answer.status_code == 302 and answer['Location'] == '/deals/12/census'
    me = client.get('/api/auth/me/')
    assert me.status_code == 200 and me.json()['username'] == user.username
    assert User.objects.count() == users  # nobody made (rule 9)


def test_PHI3_no_self_sign_up_an_unknown_account_is_refused(entra, user):
    users = User.objects.count()
    client, answer = sign_in(entra, 'stranger@example.com')
    assert refused(answer) == 'unknown'
    assert User.objects.count() == users
    assert client.get('/api/auth/me/').status_code == 401


def test_PHI3_a_user_turned_off_is_refused_and_their_session_ends_at_the_next_request(entra, user):
    client, answer = sign_in(entra, 'dana@example.com')
    assert client.get('/api/auth/me/').status_code == 200
    user.is_active = False
    user.save()
    assert client.get('/api/auth/me/').status_code == 401  # the live session ends (§3.8)
    _, again = sign_in(entra, 'dana@example.com')
    assert refused(again) == 'disabled'


def test_PHI3_an_email_two_active_users_share_is_refused_one_turned_off_is_not_counted(entra, user):
    twin = User.objects.create_user('dana2', 'DANA@example.com', 'pw-Example-1')
    _, answer = sign_in(entra, 'dana@example.com')
    assert refused(answer) == 'shared'
    twin.is_active = False
    twin.save()
    client, answer = sign_in(entra, 'dana@example.com')
    assert answer.status_code == 302 and client.get('/api/auth/me/').json()['username'] == 'dana'


def test_PHI3_the_refusals_are_sentences_the_sign_in_page_reads(entra, anon_api):
    options = anon_api.get('/api/auth/options/').json()
    assert options['password'] is True
    assert options['microsoft']['start'] == '/api/auth/microsoft/'
    assert set(options['microsoft']['messages']) == set(firm.REFUSALS)
    assert all(sentence.endswith('.') for sentence in options['microsoft']['messages'].values())


def test_PHI3_off_until_the_firm_registration_is_named(anon_api, db):
    options = anon_api.get('/api/auth/options/').json()
    assert options == {'password': True, 'microsoft': None}
    assert anon_api.get('/api/auth/microsoft/').status_code == 404
    assert anon_api.get('/api/auth/microsoft/callback/', {'code': 'x', 'state': 'y'}).status_code == 404


def test_PHI3_password_sign_in_off_leaves_microsoft_365_the_only_way_in(entra, settings, admin_user):
    settings.AUTH_PASSWORD_SIGNIN = False
    settings.AUTHENTICATION_BACKENDS = [firm.BACKEND]
    client = APIClient()
    answer = client.post('/api/auth/login/', {'username': 'ada', 'password': 'pw-Example-1'}, format='json')
    assert answer.status_code == 400 and answer.json() == {'non_field_errors': [firm.PASSWORD_OFF]}
    page = client.post('/admin/login/', {'username': 'ada', 'password': 'pw-Example-1'})
    assert page.status_code == 200 and '_auth_user_id' not in client.session  # Django admin refuses the password
    assert client.get('/api/auth/options/').json()['password'] is False
    client, answer = sign_in(entra, 'ada@example.com', '/admin/')
    assert answer['Location'] == '/admin/'
    assert client.get('/admin/').status_code == 200  # an admin reaches Django admin through the same session


@pytest.mark.parametrize('next_path', ['//evil.example/x', 'https://evil.example/', '/api/auth/me/', 'deals/1', ''])
def test_PHI3_after_signing_in_the_browser_stays_on_this_site(entra, user, next_path):
    _, answer = sign_in(entra, 'dana@example.com', next_path)
    assert answer.status_code == 302 and answer['Location'] == '/'


def test_PHI3_OQ107_a_firm_sign_in_lasts_twelve_hours(entra, user, settings):
    client, _ = sign_in(entra, 'dana@example.com')
    assert settings.SESSION_COOKIE_AGE == 43200
    assert client.cookies[settings.SESSION_COOKIE_NAME]['max-age'] == 43200


def test_PHI3_the_two_steps_are_never_cached_and_send_no_referrer(entra, user):
    client = APIClient()
    entra.sign_in_as('dana@example.com')
    first = client.get('/api/auth/microsoft/')
    second = client.get(entra.approve(first['Location']))
    for answer in (first, second):
        assert answer['Cache-Control'] == 'no-store' and answer['Referrer-Policy'] == 'no-referrer'
    assert oidc.SESSION_KEY not in client.session  # the pending sign-in is used once
