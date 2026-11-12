import os
import tempfile

from .settings import *  # noqa: F403
from .settings import DATABASES, LOGGING, REST_FRAMEWORK

# Lets two test runs share the database server without sharing a test database (TEST_DB_NAME=test_lane_a).
if os.environ.get('TEST_DB_NAME'):
    DATABASES['default']['TEST'] = {'NAME': os.environ['TEST_DB_NAME']}

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
REST_FRAMEWORK = {**REST_FRAMEWORK, 'DEFAULT_THROTTLE_CLASSES': []}
ANTHROPIC_API_KEY = ''  # tests never reach Claude, even with the key in the container: the fake client (ai/testing.py)
AI_TOTAL_BUDGET_USD = ''
AI_READ_PARALLEL = 1  # ranges one after another, in the test's own thread and transaction
AI_JOBS_INLINE = True  # a started job runs at once, in the test (plan.md §3.5)
MEDIA_ROOT = tempfile.mkdtemp(prefix='vantage2-test-media-')
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
LOGGING = {**LOGGING, 'loggers': {**LOGGING['loggers'], 'django.request': {'level': 'ERROR'}}}
AUTH_OIDC = False  # Microsoft 365 sign-in is off unless a test turns it on with the fake provider (accounts/testing.py)
AI_PHI_READERS = True  # test data is synthetic: the readers that see member data register in tests (slice 47)
