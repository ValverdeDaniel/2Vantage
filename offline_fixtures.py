"""Tests stay on the machine (plan.md §3.5, §12.1, §12.8; Q.2, Q.6): the socket guard and the fake Claude. A pytest
plugin, loaded by the root conftest.py's `pytest_plugins`."""

import pytest


# ---- the fake Claude (plan.md §12.8, Q.6; slice 18): replays recorded replies, never calls out -----------------------
@pytest.fixture
def fake_claude():
    """ai.testing.FakeTransport installed for this test: `fake_claude.record(key, data, **options)`, `.log`."""
    from ai import client
    from ai.testing import FakeTransport

    fake = FakeTransport()
    previous = client.install(fake)
    yield fake
    client.install(previous)


# ---- the socket guard (plan.md §3.5, Q.2): a test may open only the database socket ---------------------------------
class NetworkBlocked(RuntimeError):
    """A test tried to reach something other than the database: nothing leaves the machine (§12.1)."""


@pytest.fixture(autouse=True, scope='session')
def _socket_guard():
    import socket

    from django.conf import settings

    db = settings.DATABASES['default']
    host, port = db.get('HOST') or 'localhost', int(db.get('PORT') or 5432)
    allowed = {(host, port)}
    try:
        allowed |= {(info[4][0], port) for info in socket.getaddrinfo(host, port)}
    except OSError:
        pass
    unix_path = f'{host}/.s.PGSQL.{port}' if host.startswith('/') else None
    real = socket.socket.connect, socket.socket.connect_ex

    def guarded(method):
        def connect(sock, address):
            inet = sock.family in (socket.AF_INET, socket.AF_INET6) and tuple(address[:2]) in allowed
            if inet or (unix_path and address == unix_path):
                return method(sock, address)
            raise NetworkBlocked(f'A test tried to connect to {address!r}; tests may open only the database.')

        return connect

    socket.socket.connect, socket.socket.connect_ex = guarded(real[0]), guarded(real[1])
    yield
    socket.socket.connect, socket.socket.connect_ex = real
