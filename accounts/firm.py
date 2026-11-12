"""Firm accounts: who a Microsoft 365 sign-in is in 2Vantage (plan.md §3.8, §7.2, §11.4; slice 47; rule 9).

The verified email of a firm account signs in the one active user with that email, case ignored. Nobody is made here:
users and their flags live in Django admin, so an email no user has is refused, and so are a user turned off and an
email that two active users share (an admin fixes the duplicate). `FirmAccounts` is the session's backend for these
sign-ins. It never checks a password; like Django's ModelBackend, it finds the user again on each request only while
they are active, so turning someone off in Django admin ends their access at their next request. Offboarding in
Microsoft 365 stops their next sign-in there.
"""

from django.contrib.auth import get_user_model, login
from django.contrib.auth.backends import ModelBackend

BACKEND = 'accounts.firm.FirmAccounts'

# What the sign-in page says when Microsoft 365 sign-in ends without a session: /login?signin=<code> (§8.2).
REFUSALS = {
    'unknown': 'Your Microsoft 365 account has no 2Vantage access. Ask an admin to add you with your work email.',
    'disabled': 'Your 2Vantage access is turned off. Ask an admin.',
    'shared': 'More than one 2Vantage user has your email address. Ask an admin to fix it.',
    'no_email': 'Your Microsoft 365 account sent no email address, so 2Vantage cannot tell who you are. Ask an admin.',
    'cancelled': 'Microsoft 365 sign-in was cancelled.',
    'expired': 'That sign-in took too long or was started in another window. Try again.',
    'failed': 'Microsoft 365 sign-in did not work. Try again; if it keeps failing, ask an admin.',
}
PASSWORD_OFF = 'Sign in with your Microsoft 365 account.'


class FirmAccounts(ModelBackend):
    """The backend of a firm-account session: `get_user` (active users only) and admin permissions, as ModelBackend.
    It authenticates no credentials; `sign_in` is the only way a firm account starts a session."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        return None


def match(email):
    """(user, None) for the one active user with this email, else (None, refusal code)."""
    users = list(get_user_model().objects.filter(email__iexact=email.strip()))
    active = [user for user in users if user.is_active]
    if len(active) == 1:
        return active[0], None
    if active:
        return None, 'shared'
    return None, 'disabled' if users else 'unknown'


def sign_in(request, email):
    """Start the session of the firm account with this verified email. Returns None, or the refusal's code."""
    if '@' not in email:
        return 'no_email'
    user, refusal = match(email)
    if refusal:
        return refusal
    login(request, user, backend=BACKEND)
    return None
