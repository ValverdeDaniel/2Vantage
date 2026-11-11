"""Deploy checks, active only when ENVIRONMENT == 'production' (plan.md §3.5)."""

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
    return errors
