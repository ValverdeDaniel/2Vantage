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


# ---- the Q.3 contracts (plan.md §12.3): helpers in contract_helpers.py, each app's tables in its own tests ------
from contract_helpers import check_permissions, sweep_gets, write_path_contract  # noqa: E402, F401


@pytest.fixture
def actors(anon_api, api, admin_api):
    """The permission matrix's actors that exist today (Q.3 #3); later slices add theirs (owner, tiers, portal)."""
    return {'signed_out': anon_api, 'producer': api, 'admin': admin_api}


@pytest.fixture
def no_csrf_api(user):
    """A signed-in producer whose client enforces CSRF and sends no token: every write answers 403 (§3.6)."""
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    return client


def make_client(user, name='Example Co.', requested_lines=('medical', 'dental', 'vision'), **deal_kwargs):
    """A client and its deal; its lines to quote go through their one writer, intake's `set_intent` (B17)."""
    from deals.services import create_client
    from intake.services import set_intent

    client, deal = create_client(user, name=name, **deal_kwargs)
    if requested_lines:
        set_intent(user, deal.id, lines=list(requested_lines), shop=True)
        deal.refresh_from_db()
    return client, deal


def make_deal(user, **kwargs):
    return make_client(user, **kwargs)[1]


@pytest.fixture
def deal(user):
    return make_deal(user)


# ---- the golden deals (plan.md §12.6, Q.2): built once per test module; app tests never import `golden` -----------
@pytest.fixture(scope='module')
def golden(django_db_setup, django_db_blocker):
    """{'GD1': Golden(deal, refs, spec), …}: every golden deal, built once for this test module through the services
    and removed after it. `refs` maps the spec's plan refs to plan ids. Read-only: a test that writes uses a factory
    deal. A transactional test (`transaction=True`) in the same module would wipe them."""
    from golden import seed

    with django_db_blocker.unblock():
        builder, _ = get_user_model().objects.get_or_create(username='golden-builder')
        built = seed.build_all(builder)
    yield built
    with django_db_blocker.unblock():
        seed.remove_all(builder)
        builder.delete()


@pytest.fixture(scope='module')
def gd1(golden):
    return golden['GD1']


@pytest.fixture(scope='module')
def gd2(golden):
    return golden['GD2']


@pytest.fixture(scope='module')
def gd3(golden):
    """GD3 at checkpoint A as seeded: no current plan, ten quotes on typed whole-line counts (slice 13)."""
    return golden['GD3']


@pytest.fixture(scope='module')
def gd5(golden):
    """GD5 as seeded: a level-funded medical line and the Stop-Loss line's contract, renewal and options (slice 36)."""
    return golden['GD5']


@pytest.fixture(scope='module')
def gd6(golden):
    return golden['GD6']


class QuoteFirst:
    """A fresh GD3 for one test, moved through its checkpoints the way a person's clicks move it
    (golden/quote_first.py): `arrive('D')`, `split()`, `census()`. `built` is the Golden(deal, refs, spec) now."""

    def __init__(self, user):
        from golden import seed, specs

        self.user = user
        self.built = seed.build(specs.load('GD3'), user)

    def _step(self, name, *args):
        from golden import quote_first

        self.built = getattr(quote_first, name)(self.user, self.built, *args)
        return self

    def arrive(self, ref):
        return self._step('arrive', ref)

    def split(self):
        return self._step('split')

    def census(self):
        return self._step('census')


@pytest.fixture(scope='session')
def gd3_packet_answer():
    """The reply a perfect read of GD3's renewal packet gives, and the range it covers (golden/renewal_packet.py)."""
    from golden import renewal_packet, specs

    return renewal_packet.answer(specs.load('GD3')), renewal_packet.RANGE


@pytest.fixture
def gd3_packet(gd3, gd3_packet_answer, db):
    """GD3's renewal packet as seeded (unread), with the perfect read's reply and range (slice 18):
    (document, answer, range label)."""
    from documents.models import Document

    return Document.objects.get(deal=gd3.deal, kind='renewal'), *gd3_packet_answer


@pytest.fixture
def quote_first(user):
    """GD3 built for this test only (it writes), at checkpoint A; see QuoteFirst."""
    return QuoteFirst(user)


class GetToMarket:
    """A fresh GD6 for one test, as seeded (Blocked), moved toward Ready to market the way a person's clicks move it
    (golden/get_to_market.py; slice 40): `step('contacts')`, `'census_arrives'`, `'intent'`, `'bor'`, `'ticks'`, or
    `ready()` for all of them. `built` is the Golden(deal, refs, spec) now."""

    def __init__(self, user):
        from golden import seed, specs

        self.user = user
        self.built = seed.build(specs.load('GD6'), user)

    def step(self, *names):
        from golden import get_to_market

        for name in names:
            self.built = getattr(get_to_market, name)(self.user, self.built)
        return self

    def ready(self):
        return self.step('ready')


@pytest.fixture
def get_to_market(user):
    """GD6 built for this test only (it writes), as seeded; see GetToMarket."""
    return GetToMarket(user)


# ---- GD1-sold (plan.md §13.4; slice 49): GD1 after its sale, a variant under a client name of its own ---------------
@pytest.fixture(scope='module')
def gd1_sold(django_db_setup, django_db_blocker):
    """GD1-sold built once for this test module and removed after it: its sale books on commit (two medical records,
    Cigna and UnitedHealthcare) and makes its client a New client. Read-only; a test that writes uses `sell_gd1`."""
    from commission.models import Party
    from deals.models import Activity
    from golden import seed, specs

    with django_db_blocker.unblock():
        builder, _ = get_user_model().objects.get_or_create(username='golden-sold-builder')
        built = seed.build(specs.load('GD1-sold'), builder)
    yield built
    with django_db_blocker.unblock():
        seed.remove(built.spec, builder)
        for party in Party.objects.filter(user=builder):  # the owner's Party, made by the booking (H95)
            Activity.objects.filter(subject=f'party:{party.id}').delete()
            party.delete()
        builder.delete()


@pytest.fixture
def sell_gd1(user, django_capture_on_commit_callbacks):
    """GD1-sold built for this test only (it writes), owned by `user`, with its sale's on-commit booking run."""
    from golden import seed, specs

    with django_capture_on_commit_callbacks(execute=True):
        built = seed.build(specs.load('GD1-sold'), user)
    return built


@pytest.fixture(scope='session')
def golden_keys():
    """{'GD1': its answer key, …} (Q.4): the figures, with checked_by, checked_on and method (null until signed), the
    variants' (GD1-sold) among them."""
    from golden import specs

    return {key: specs.answer_key(key) for key in [*specs.keys(), *specs.variant_keys()]}


# ---- GD-Big (plan.md §13.4, Q.7): scale, in tests only; the builder is the root's gd_big.py -------------------------
def make_big_deal(user, plans, name='Big shape (synthetic)'):
    """GD-Big's shape at any size, inside a test: a scaling test compares two sizes (Q.3 #4)."""
    import gd_big as big

    return big.build(user, plans=plans, name=name)


@pytest.fixture(scope='module')
def gd_big(django_db_setup, django_db_blocker):
    """A deal with 600 medical plans (links, stars, read values), built once for this test module and removed after
    it. Read-only, like the golden deals; `make_big_deal(user, 10)` makes the same shape small inside a test."""
    import gd_big as big

    with django_db_blocker.unblock():
        builder, _ = get_user_model().objects.get_or_create(username='gd-big-builder')
        deal = big.build(builder)
    yield deal
    with django_db_blocker.unblock():
        big.remove(builder, deal)
        builder.delete()


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
