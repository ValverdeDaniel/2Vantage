import tempfile

from .settings import *  # noqa: F403
from .settings import LOGGING, REST_FRAMEWORK

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
REST_FRAMEWORK = {**REST_FRAMEWORK, 'DEFAULT_THROTTLE_CLASSES': []}
ANTHROPIC_API_KEY = ''
MEDIA_ROOT = tempfile.mkdtemp(prefix='vantage2-test-media-')
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
LOGGING = {**LOGGING, 'loggers': {**LOGGING['loggers'], 'django.request': {'level': 'ERROR'}}}
