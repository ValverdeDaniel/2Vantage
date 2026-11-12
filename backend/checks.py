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
    if settings.ON_CLOUD_RUN and not settings.GS_BUCKET_NAME:
        # Each instance has its own disk, lost when it stops, and the worker never sees the web service's (slice 69).
        errors.append(Error('Files would be kept on a Cloud Run instance: set GS_BUCKET_NAME.', id='vantage.E005'))
    return errors
