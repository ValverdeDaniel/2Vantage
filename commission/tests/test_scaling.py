"""Query scaling for commission (plan.md §12.2, Q.3 #4): the Commission tab, the roster of parties and the book of
records run the same queries at two sizes. Two sizes compared, never a pinned number."""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from accounts.models import Profile
from commission import services
from commission.models import Party
from conftest import make_deal

pytestmark = pytest.mark.django_db


def test_Q3_4_the_tab_reads_in_a_fixed_number_of_queries(api, user):
    from quotes import services as quotes

    def queries(deal):
        with CaptureQueriesContext(connection) as captured:
            assert api.get(f'/api/deals/{deal.id}/commission/').status_code == 200
        return len(captured.captured_queries)

    small = make_deal(user, requested_lines=('medical',))
    big = make_deal(user, name='Bigger Co.', requested_lines=('medical', 'dental', 'vision', 'std', 'ltd', 'eap'))
    for line in ('medical', 'dental', 'vision'):
        for n in range(4):
            quotes.create_plan(user, big, line=line, role='alternate', carrier='Cigna', name=f'P{n}', values={})
    for n in range(5):
        Party.objects.create(kind='partner', name=f'Partner {n}')
        get_user_model().objects.create_user(f'producer{n}', f'p{n}@example.com', 'pw-Example-1')
    services.update(user, big.id, {'rates': {'medical': '5', 'dental': '10'}})
    assert queries(big) == queries(small)


def test_Q3_4_the_roster_reads_in_a_fixed_number_of_queries(admin_api):
    def queries():
        with CaptureQueriesContext(connection) as captured:
            assert admin_api.get('/api/commissions/parties/').status_code == 200
        return len(captured.captured_queries)

    one = get_user_model().objects.create_user('first', 'f@example.com', 'pw-Example-1')
    Party.objects.create(kind='producer', name='First', user=one)
    before = queries()
    for n in range(8):
        login = get_user_model().objects.create_user(f'more{n}', f'm{n}@example.com', 'pw-Example-1')
        Profile.objects.create(user=login, commissions_access='all')
        Party.objects.create(kind='producer' if n % 2 else 'partner', name=f'More {n}', user=login if n % 2 else None)
    assert queries() == before


def test_Q3_4_the_book_reads_in_a_fixed_number_of_queries(admin_api, admin_user):
    def queries():
        with CaptureQueriesContext(connection) as captured:
            assert admin_api.get('/api/commissions/records/').status_code == 200
        return len(captured.captured_queries)

    services.add_to_book(admin_user, {'client_name': 'First Co.', 'line': 'medical', 'rate': '5'})
    before = queries()
    for n in range(6):
        services.add_to_book(admin_user, {'client_name': f'More Co. {n}', 'line': 'dental', 'premium_annual': '100'})
    assert queries() == before
