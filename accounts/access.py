"""Who may do what (plan.md §6.1, §7.2; A2–A4). Two kinds of person: admin (`is_staff`) and producer.

`can_direct(user)` and `commission_tier(user)` are what other apps call (O.2). Neither creates a Profile: a user with no
row reads the defaults (not direct; a producer's tier is own), so a GET never writes.
"""

from rest_framework.permissions import BasePermission

from .models import Profile

DEFAULT_TIER = 'own'


def _profile(user):
    if not getattr(user, 'is_authenticated', False):
        return None
    cached = getattr(user, '_profile_row', False)
    if cached is False:
        cached = Profile.objects.filter(user_id=user.id).first()
        user._profile_row = cached  # one read per request user
    return cached


def can_direct(user):
    """True for a "direct" person (A3): reads land at once with Undo, Opus may be picked, budgets overridden."""
    profile = _profile(user)
    return bool(profile and profile.claude_direct)


def commission_tier(user):
    """'none', 'own' or 'all'. An admin is always all; a producer with no row reads own; signed out is none."""
    if not getattr(user, 'is_authenticated', False):
        return 'none'
    if user.is_staff:
        return 'all'
    profile = _profile(user)
    return profile.commissions_access if profile else DEFAULT_TIER


class IsAdmin(BasePermission):
    """RequireAdmin on the server (A4): staff users only."""

    message = 'Only an admin can do that.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class HasCommissions(BasePermission):
    """RequireCommissions on the server (A4): a commission tier other than none."""

    message = 'Your account has no access to commissions. Ask an admin.'

    def has_permission(self, request, view):
        return commission_tier(request.user) != 'none'
