"""Deploy checks, active only when ENVIRONMENT == 'production' (plan.md §3.5; E006–E008: the PHI gate, §11.4)."""

import os

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def production_settings(app_configs, **kwargs):
    if settings.ENVIRONMENT != 'production':
        return []
    errors = []
    if settings.DEBUG:
        errors.append(Error('DEBUG is on in production.', id='vantage.E001'))
    if settings.SECRET_KEY == 'dev-only-not-secret':
        errors.append(Error('The default secret key is in use in production.', id='vantage.E002'))
    if settings.EMAIL_BACKEND.endswith('console.EmailBackend'):
        errors.append(Error('Email prints to the console in production.', id='vantage.E003'))
    if os.environ.get('ANTHROPIC_LOG', '').lower() in ('debug', 'info'):
        errors.append(Error('ANTHROPIC_LOG would log document contents.', id='vantage.E004'))
    if settings.ON_CLOUD_RUN and not settings.GS_BUCKET_NAME:
        # Each instance has its own disk, lost when it stops, and the worker never sees the web service's (slice 69).
        errors.append(Error('Files would be kept on a Cloud Run instance: set GS_BUCKET_NAME.', id='vantage.E005'))
    return errors + phi_gate()


def phi_gate():
    """The PHI gate's order in settings (slice 47; §11.4): sign-in moves to Microsoft 365 before the PHI-gate switch."""
    errors = []
    if settings.AI_PHI_READERS and (not settings.AUTH_OIDC or settings.AUTH_PASSWORD_SIGNIN):
        errors.append(
            Error(
                'AI_PHI_READERS is on before sign-in moved to Microsoft 365: set AUTH_OIDC_* and '
                'AUTH_PASSWORD_SIGNIN=false first (the PHI gate, plan.md §11.4).',
                id='vantage.E006',
            )
        )
    if not settings.AUTH_PASSWORD_SIGNIN and not settings.AUTH_OIDC:
        errors.append(
            Error('Nobody can sign in: password sign-in is off and Microsoft 365 is not set up.', id='vantage.E007')
        )
    if settings.AUTH_OIDC and not settings.AUTH_OIDC_ISSUER.startswith('https://'):
        errors.append(Error('Microsoft 365 sign-in must reach its provider over HTTPS.', id='vantage.E008'))
    return errors
