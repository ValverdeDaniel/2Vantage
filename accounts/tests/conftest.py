import pytest

from accounts import oidc
from accounts.testing import FakeProvider, settings_on


@pytest.fixture
def entra(settings):
    """Microsoft 365 sign-in turned on against the in-memory fake provider (accounts/testing.py); nothing leaves the
    machine. Yields the provider: `entra.sign_in_as(email)`, then `entra.approve(authorize_url)`."""
    for name, value in settings_on().items():
        setattr(settings, name, value)
    provider = FakeProvider()
    previous = oidc.install(provider)
    yield provider
    oidc.install(previous)
