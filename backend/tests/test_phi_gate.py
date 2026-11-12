"""The PHI gate's settings (plan.md §11.4 items 3 and 7, §3.5; slice 47): the readers that see member data register
only while the PHI-gate switch is on, and production's deploy checks keep the gate's order — sign-in moves to
Microsoft 365 (over HTTPS, with passwords off) before the switch, and some way to sign in is always left."""

import pytest
from django.core.checks import run_checks

from ai import kinds, registry
from backend import checks

HTTPS = 'https://login.microsoftonline.com/f1a2b3c4-0000-4000-8000-000000000047/v2.0'


def _reader(target):
    return registry.Reader(
        target=target, kinds=(), prompt='', schema={}, version=1, note=None, merge=None, build_changes=None
    )


@pytest.fixture
def readers():
    """The registry as it stands, put back after the test."""
    kept = dict(registry.readers)
    yield registry.readers
    registry.readers.clear()
    registry.readers.update(kept)


@pytest.mark.parametrize('target', kinds.PHI_TARGETS)
def test_PHI7_a_reader_that_sees_member_data_waits_for_the_switch(settings, readers, target):
    readers.pop(target, None)
    settings.AI_PHI_READERS = False
    assert registry.register_reader(_reader(target)) is False and target not in readers
    settings.AI_PHI_READERS = True
    assert registry.register_reader(_reader(target)) is True and target in readers


def test_PHI7_the_plan_readers_never_wait(settings, readers):
    settings.AI_PHI_READERS = False
    for target in set(kinds.TARGETS) - set(kinds.PHI_TARGETS):
        assert registry.register_reader(_reader(target)) is True and target in readers


def _ids(settings, **values):
    settings.ENVIRONMENT = 'production'
    for name, value in values.items():
        setattr(settings, name, value)
    return {error.id for error in checks.production_settings(None)}


GATE = {'AUTH_OIDC': True, 'AUTH_OIDC_ISSUER': HTTPS, 'AUTH_PASSWORD_SIGNIN': False}


def test_PHI7_the_switch_goes_on_last(settings):
    assert 'vantage.E006' in _ids(settings, AI_PHI_READERS=True, AUTH_OIDC=False, AUTH_PASSWORD_SIGNIN=True)
    assert 'vantage.E006' in _ids(settings, AI_PHI_READERS=True, **{**GATE, 'AUTH_PASSWORD_SIGNIN': True})
    assert 'vantage.E006' not in _ids(settings, AI_PHI_READERS=True, **GATE)
    assert 'vantage.E006' not in _ids(settings, AI_PHI_READERS=False, AUTH_OIDC=False, AUTH_PASSWORD_SIGNIN=True)


def test_PHI3_some_way_in_is_always_left_and_microsoft_365_is_reached_over_https(settings):
    assert 'vantage.E007' in _ids(settings, AUTH_OIDC=False, AUTH_PASSWORD_SIGNIN=False)
    assert 'vantage.E007' not in _ids(settings, **GATE)
    assert 'vantage.E008' in _ids(settings, **{**GATE, 'AUTH_OIDC_ISSUER': 'http://localhost:8016/stand-in/v2.0'})
    assert not {'vantage.E006', 'vantage.E007', 'vantage.E008'} & _ids(settings, AI_PHI_READERS=True, **GATE)


def test_PHI3_the_gate_checks_stay_quiet_locally(settings):
    settings.ENVIRONMENT = 'local'
    settings.AI_PHI_READERS, settings.AUTH_PASSWORD_SIGNIN, settings.AUTH_OIDC = True, False, False
    assert not [error for error in run_checks(include_deployment_checks=True) if error.id.startswith('vantage.')]
