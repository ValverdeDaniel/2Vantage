"""The root conftest's socket guard (plan.md §3.5, §12.1, Q.2): a test may open only the database socket."""

import socket

import pytest
from django.contrib.auth import get_user_model


@pytest.mark.parametrize('address', [('203.0.113.7', 443), ('127.0.0.1', 8000)])
def test_PAR1_a_test_cannot_connect_anywhere_but_the_database(address):
    with pytest.raises(RuntimeError, match='may open only the database'):
        socket.create_connection(address, timeout=1)


def test_PAR1_connect_ex_is_guarded_too():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(RuntimeError, match='may open only the database'):
            sock.connect_ex(('203.0.113.7', 80))
    finally:
        sock.close()


@pytest.mark.django_db
def test_PAR1_the_database_still_answers():
    get_user_model().objects.create_user('probe', 'probe@example.com', 'pw-Example-1')
    assert get_user_model().objects.filter(username='probe').exists()
