"""Profile flags and who may do what (plan.md §6.1, §7.2; A3, A4)."""

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser

from accounts import access
from accounts.models import Profile


def test_A3_a_user_with_no_row_reads_the_defaults_and_me_creates_none(api, user):
    body = api.get('/api/auth/me/').json()
    assert (body['claude_direct'], body['commissions_access']) == (False, 'own')
    assert not Profile.objects.exists()


def test_A3_me_serves_the_flags_as_they_apply(api, admin_api, user, admin_user):
    Profile.objects.create(user=user, claude_direct=True, commissions_access='none')
    Profile.objects.create(user=admin_user, commissions_access='none')
    mine = api.get('/api/auth/me/').json()
    assert (mine['claude_direct'], mine['commissions_access']) == (True, 'none')
    admin = admin_api.get('/api/auth/me/').json()
    assert (admin['claude_direct'], admin['commissions_access']) == (False, 'all')  # an admin is always all


def test_A3_login_answers_the_same_user_payload(anon_api, user):
    Profile.objects.create(user=user, commissions_access='all')
    body = anon_api.post('/api/auth/login/', {'username': 'dana', 'password': 'pw-Example-1'}, format='json').json()
    assert body['commissions_access'] == 'all' and body['claude_direct'] is False


@pytest.mark.parametrize(
    'staff, stored, tier',
    [(False, None, 'own'), (False, 'none', 'none'), (False, 'all', 'all'), (True, None, 'all'), (True, 'none', 'all')],
)
def test_A3_commission_tier(user, staff, stored, tier):
    user.is_staff = staff
    user.save()
    if stored:
        Profile.objects.create(user=user, commissions_access=stored)
    assert access.commission_tier(user) == tier


def test_A3_signed_out_is_neither_direct_nor_on_a_tier():
    assert access.can_direct(AnonymousUser()) is False
    assert access.commission_tier(AnonymousUser()) == 'none'


@pytest.mark.parametrize(
    'staff, stored, admin_ok, commissions_ok',
    [(False, None, False, True), (False, 'none', False, False), (True, 'none', True, True)],
)
def test_A4_the_permission_classes_match_the_flags(user, staff, stored, admin_ok, commissions_ok):
    user.is_staff = staff
    user.save()
    if stored:
        Profile.objects.create(user=user, commissions_access=stored)
    request = SimpleNamespace(user=user)
    assert access.IsAdmin().has_permission(request, None) is admin_ok
    assert access.HasCommissions().has_permission(request, None) is commissions_ok
