"""Who may open a link (plan.md §7.14; L77, L107, L110; rule 11; Q.9 row 54): 404 for a bad token, 410 (with the
agency's contact, never an owner) for a link off, run out or closed, 428 until the PIN, the five-try lock, a New PIN
ending the proof, the headers on every answer, and the per-link rates that keep polling off a save's budget."""

from datetime import timedelta
from unittest import mock

import pytest
from django.core.cache import cache
from django.test import override_settings

from deals import clock
from deals.models import AgencySettings
from review import services
from review.portal import guard

from .portal_world import client, fresh, make_request, page, save, url, verified

pytestmark = pytest.mark.django_db

INTAKE = {'intake': {'scope': 'missing'}}
CENSUS = {'census': {'scope': 'all'}}
HEADERS = {'Cache-Control': 'private, no-store', 'Referrer-Policy': 'no-referrer', 'X-Robots-Tag': 'noindex'}


def _headed(answer):
    return all(answer[name] == value for name, value in HEADERS.items())


@pytest.fixture
def agency(db):
    row = AgencySettings.get()
    row.phone, row.email = '555-0199', 'help@agency.example'
    row.save()
    return row


def test_L77_an_unknown_or_malformed_token_answers_404_with_the_headers(db):
    api = client()
    for token in ('A' * 43, 'short', 'x' * 43 + '!'):
        answer = api.get(url(token))
        assert answer.status_code == 404
        assert answer.json() == {'detail': "This link isn't valid."}
        assert _headed(answer)


def test_L107_a_link_off_run_out_or_closed_answers_410_with_the_agency_and_no_owner(user, deal, agency):
    api = client()
    off, token_off, _ = make_request(user, deal, INTAKE)
    services.revoke(user, off.id)
    expired, token_expired, _ = make_request(user, deal, INTAKE)
    closed, token_closed, _ = make_request(user, deal, INTAKE)
    services.close(user, closed.request_id, 'cancelled')
    later = clock.now() + timedelta(days=8)
    for token, moment in ((token_off, None), (token_expired, later), (token_closed, None)):
        with mock.patch.object(clock, 'now', return_value=moment or clock.now()):
            answer = api.get(url(token))
        assert answer.status_code == 410, token
        body = answer.json()
        assert body['agency'] == {'name': agency.name, 'phone': '555-0199', 'email': 'help@agency.example'}
        assert user.username not in str(body) and 'Dana' not in str(body)
        assert _headed(answer)
    assert fresh(expired).open_count == 0


def test_L77_a_pin_link_answers_428_until_the_pin_and_then_opens(user, deal):
    link, token, pin = make_request(user, deal, CENSUS)
    assert link.security == 'pin'
    api = client()
    asked = page(api, token)
    assert asked.status_code == 428
    body = asked.json()
    assert {key: body[key] for key in ('detail', 'verification', 'kind', 'locked')} == {
        'detail': guard.PIN_NEEDED,
        'verification': 'required',
        'kind': 'pin',
        'locked': False,
    }
    assert set(body['agency']) == {'name', 'phone', 'email'}
    assert fresh(link).open_count == 0
    header = verified(api, token, pin)
    opened = page(api, token, **header)
    assert opened.status_code == 200
    assert opened['X-Link-Verification']  # issued again with each answer (L.6)
    assert fresh(link).open_count == 1


def test_L77_five_wrong_pins_lock_the_link_until_a_new_pin(user, deal):
    link, token, pin = make_request(user, deal, CENSUS)
    api = client()
    wrong = '000000' if pin != '000000' else '111111'
    for left in (4, 3, 2, 1):
        answer = api.post(url(token, 'verify/'), {'pin': wrong}, format='json')
        assert answer.status_code == 400 and answer.json()['tries_left'] == left
    locked = api.post(url(token, 'verify/'), {'pin': wrong}, format='json')
    assert locked.json()['locked'] is True
    assert api.post(url(token, 'verify/'), {'pin': pin}, format='json').status_code == 400  # locked: even the PIN
    assert page(api, token).json()['locked'] is True
    renewed = services.new_pin(user, link.id).pin
    assert page(api, token, **verified(api, token, renewed)).status_code == 200


def test_L64_a_new_pin_ends_a_proved_browser(user, deal):
    link, token, pin = make_request(user, deal, CENSUS)
    api = client()
    header = verified(api, token, pin)
    assert page(api, token, **header).status_code == 200
    services.new_pin(user, link.id)
    assert page(api, token, **header).status_code == 428


def test_L77_a_proof_lasts_an_hour_idle(user, deal):
    _link, token, pin = make_request(user, deal, CENSUS)
    api = client()
    header = verified(api, token, pin)
    later = __import__('time').time() + 61 * 60
    with mock.patch('django.core.signing.time.time', return_value=later):
        assert page(api, token, **header).status_code == 428


def test_L77_a_staff_session_needs_no_pin_and_writes_answer_403(user, deal, api):
    link, token, _pin = make_request(user, deal, CENSUS)
    assert page(api, token).status_code == 200
    refused = api.post(url(token, 'people/'), {'people': [{'first_name': 'A', 'last_name': 'B'}]}, format='json')
    assert refused.status_code == 403 and _headed(refused)
    assert fresh(link).open_count == 0


@override_settings(
    REST_FRAMEWORK={
        'DEFAULT_AUTHENTICATION_CLASSES': ['accounts.auth.SessionAuth'],
        'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
        'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {
            'portal_read': '300/hour',
            'portal_write': '3600/hour',
            'portal_poll': '3/hour',
            'portal_pin': '10/hour',
        },
    }
)
def test_L110_polling_never_uses_up_a_save(user, deal):
    cache.clear()
    _link, token, _pin = make_request(user, deal, INTAKE)
    api = client()
    polls = [api.get(url(token, 'stamp/')).status_code for _ in range(5)]
    assert polls[:3] == [200, 200, 200] and polls[3:] == [429, 429]
    body = page(api, token).json()
    from .portal_world import field

    base = field(body, 'fein')['base']
    assert save(api, token, {'intake:fein': {'value': '12-3456789', 'base': base}}).status_code == 200
    cache.clear()
