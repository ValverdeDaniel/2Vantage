"""2Vantage settings. The only module that reads environment variables (plan.md §3.5)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name, default=''):
    return os.environ.get(name, default)


def _flag(name, default='False'):
    return _env(name, default).strip().lower() in ('true', '1', 'yes')


def _list(name, default=''):
    return [item.strip() for item in _env(name, default).split(',') if item.strip()]


SECRET_KEY = _env('DJANGO_SECRET_KEY', 'dev-only-not-secret')
DEBUG = _flag('DJANGO_DEBUG')
ENVIRONMENT = _env('ENVIRONMENT', 'local')
ALLOWED_HOSTS = ['*'] if DEBUG else _list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
FRONTEND_URL = _env('FRONTEND_URL', 'http://localhost:4001').rstrip('/')
GIT_SHA = _env('GIT_SHA', 'unknown')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'backend',
    'accounts',
    'deals',
    'documents',
    'quotes',
    'proposals',
    'golden',  # seed only, last in the chain (§3.3)
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'backend.middleware.JsonGZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'
WSGI_APPLICATION = 'backend.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _env('DB_NAME', 'vantage2'),
        'USER': _env('DB_USER', 'vantage'),
        'PASSWORD': _env('DB_PASSWORD', 'vantage-dev'),
        'HOST': _env('DB_HOST', 'localhost'),
        'PORT': _env('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Storage and API timestamps are UTC; dates people see use the agency's zone (deals/clock.py).
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_TZ = True
AGENCY_TIME_ZONE = _env('AGENCY_TIME_ZONE', 'America/New_York')

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Uploaded and issued files: a Docker volume, never a folder inside the repository (§3.4).
MEDIA_ROOT = _env('MEDIA_ROOT', '/data/media')
MEDIA_URL = '/media-not-served/'
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
# One file per request, under Cloud Run's 32 MiB request limit (§3.5, E7, OQ24).
FILE_UPLOAD_MAX_BYTES = 30 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sign-in: Django sessions (§3.8). The CSRF cookie stays readable so the SPA can echo it.
SESSION_COOKIE_AGE = int(_env('SESSION_COOKIE_AGE', '43200'))
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False
CSRF_TRUSTED_ORIGINS = [FRONTEND_URL] + [f'https://{host}' for host in _list('ALLOWED_HOSTS') if host != '*']
LOGIN_URL = '/login'
if ENVIRONMENT == 'production':
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

EMAIL_HOST = _env('EMAIL_HOST')
EMAIL_PORT = int(_env('EMAIL_PORT') or 587)
EMAIL_HOST_USER = _env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = _env('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = _env('DEFAULT_FROM_EMAIL', 'no-reply@localhost')
EMAIL_BACKEND = (
    'django.core.mail.backends.smtp.EmailBackend'
    if EMAIL_HOST_USER
    else 'django.core.mail.backends.console.EmailBackend'
)

ANTHROPIC_API_KEY = _env('ANTHROPIC_API_KEY')
AI_MODEL = _env('AI_MODEL')
AI_READ_LIMIT_USD = _env('AI_READ_LIMIT_USD')
# On: Claude's reads leave out the pages the member-data screen flagged at upload; off, files are read whole (OQ22).
AI_MEMBER_DATA_SCREEN = _flag('AI_MEMBER_DATA_SCREEN')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['accounts.auth.SessionAuth'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {'anon': '200/hour', 'user': '5000/hour', 'login': '10/minute', 'portal': '1000/hour'},
    'UNAUTHENTICATED_USER': 'django.contrib.auth.models.AnonymousUser',
}

# Logging (§3.5): one console handler at WARNING; SDK loggers pinned (their DEBUG output carries document text).
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler', 'level': 'WARNING'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        **{name: {'level': 'WARNING'} for name in ('anthropic', 'httpx', 'httpcore')},
        **{name: {'level': 'INFO'} for name in ('accounts', 'deals', 'documents', 'quotes', 'proposals')},
    },
}
