import os
import tempfile

from .settings import *  # noqa: F403
from .settings import DATABASES, LOGGING, REST_FRAMEWORK

# Lets two test runs share the database server without sharing a test database (TEST_DB_NAME=test_lane_a).
if os.environ.get('TEST_DB_NAME'):
    DATABASES['default']['TEST'] = {'NAME': os.environ['TEST_DB_NAME']}

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
REST_FRAMEWORK = {**REST_FRAMEWORK, 'DEFAULT_THROTTLE_CLASSES': []}
ANTHROPIC_API_KEY = ''
MEDIA_ROOT = tempfile.mkdtemp(prefix='vantage2-test-media-')
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
LOGGING = {**LOGGING, 'loggers': {**LOGGING['loggers'], 'django.request': {'level': 'ERROR'}}}
