"""Shared fixtures and factories (plan.md §12.1). Factories create only the rows a test needs; all data is synthetic."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user('dana', 'dana@example.com', 'pw-Example-1', first_name='Dana')


@pytest.fixture
def admin_user(db):
    return get_user_model().objects.create_user('ada', 'ada@example.com', 'pw-Example-1', is_staff=True)


def _signed_in(user):
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def api(user):
    return _signed_in(user)


@pytest.fixture
def admin_api(admin_user):
    return _signed_in(admin_user)


@pytest.fixture
def anon_api():
    return APIClient()


def make_client(user, name='Example Co.', **deal_kwargs):
    from deals.services import create_client

    deal_kwargs.setdefault('requested_lines', ['medical', 'dental', 'vision'])
    return create_client(user, name=name, **deal_kwargs)


def make_deal(user, **kwargs):
    return make_client(user, **kwargs)[1]


@pytest.fixture
def deal(user):
    return make_deal(user)
